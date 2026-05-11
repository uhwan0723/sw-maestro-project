import asyncio
import time

import structlog
from fastapi import APIRouter, HTTPException, Request, Response

from app.observability import elapsed_ms, preview
from app.rag.service import RagUnavailableError
from app.schemas.api import ErrorDetail, RecommendationResponse, RecommendRequest
from app.services.cache import cache_service
from app.services.limiter import limiter
from app.services.normalize import cache_key
from app.services.strategy_invoker import (
    RecommendationFailed,
    RecommendationTimeout,
    run_strategy_agent,
)
from app.settings import settings

logger = structlog.get_logger()
router = APIRouter()

agent_semaphore = asyncio.Semaphore(settings.semaphore_limit)

_ERROR_MESSAGES = {
    "agent_timeout": "응답이 너무 오래 걸려요. 다시 시도하시거나 더 짧은 질문을 입력해주세요.",
    "agent_failed": "AI 응답 생성에 실패했어요. 잠시 후 다시 시도해주세요.",
    "rag_unavailable": "추천 근거 데이터를 불러오지 못했어요. 잠시 후 다시 시도해주세요.",
    "agent_internal": "서버 내부 오류가 발생했어요. 잠시 후 다시 시도해주세요.",
}


@router.post(
    "/recommend",
    response_model=RecommendationResponse,
    summary="덱 추천",
    description="""
티어와 플레이 스타일, 자연어 질문을 입력받아 현재 패치 기준 덱 추천 결과를 반환합니다.

- 동일 요청은 캐시(L1 LRU + L2 SQLite)에서 즉시 반환됩니다 (`X-Cache: HIT`).
- 응답에는 덱 목록, 운영법(playbook), 출처(sources), 확신도(confidence)가 포함됩니다.
- IP당 분당 5회 호출 제한이 적용됩니다.
- 최대 응답 시간: 25초 (초과 시 504 반환).
""",
    responses={
        429: {"description": "Rate limit 초과"},
        502: {"description": "Agent 또는 RAG 처리 실패"},
        504: {"description": "Agent 응답 시간 초과 (25s)"},
        500: {"description": "서버 내부 오류"},
    },
)
@limiter.limit(settings.effective_rate_limit)
async def recommend(request: Request, response: Response, body: RecommendRequest):
    req_id = getattr(request.state, "request_id", "-")
    patch = settings.patch_version

    key = cache_key(body.tier, body.play_style, body.question, patch)
    logger.info(
        "cache_lookup",
        request_id=req_id,
        stage="api",
        tier=body.tier,
        play_style=body.play_style,
        patch_version=patch,
        question=preview(body.question),
    )

    cached = await cache_service.get(key)
    if cached:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Patch-Version"] = patch
        logger.info(
            "cache_hit",
            request_id=req_id,
            stage="api",
            tier=body.tier,
            intent=cached.get("intent"),
        )
        return RecommendationResponse(**cached)

    logger.info("cache_miss", request_id=req_id, stage="api")
    async with agent_semaphore:
        logger.info(
            "strategy_agent_start",
            request_id=req_id,
            stage="api",
            timeout_s=settings.agent_timeout_s,
        )
        started = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                run_strategy_agent(
                    req_id,
                    body.tier,
                    body.play_style,
                    body.question,
                    patch_version=patch,
                    timeout_s=settings.agent_timeout_s,
                ),
                timeout=settings.agent_timeout_s,
            )
            logger.info(
                "strategy_agent_done",
                request_id=req_id,
                stage="api",
                intent=result.intent,
                decks=len(result.decks),
                confidence=result.confidence,
                latency_ms=elapsed_ms(started),
            )
        except (asyncio.TimeoutError, RecommendationTimeout):
            logger.warning(
                "strategy_agent_timeout",
                request_id=req_id,
                stage="api",
                latency_ms=elapsed_ms(started),
            )
            raise HTTPException(
                status_code=504,
                detail=ErrorDetail(
                    code="agent_timeout",
                    message=_ERROR_MESSAGES["agent_timeout"],
                    request_id=req_id,
                ).model_dump(),
            )
        except RecommendationFailed as exc:
            logger.warning(
                "agent_failed",
                request_id=req_id,
                stage="api",
                latency_ms=elapsed_ms(started),
                error=str(exc),
            )
            raise HTTPException(
                status_code=502,
                detail=ErrorDetail(
                    code="agent_failed",
                    message=_ERROR_MESSAGES["agent_failed"],
                    request_id=req_id,
                ).model_dump(),
            )
        except RagUnavailableError as exc:
            logger.warning(
                "rag_unavailable",
                request_id=req_id,
                stage="api",
                latency_ms=elapsed_ms(started),
                error=str(exc),
            )
            raise HTTPException(
                status_code=502,
                detail=ErrorDetail(
                    code="rag_unavailable",
                    message=_ERROR_MESSAGES["rag_unavailable"],
                    request_id=req_id,
                ).model_dump(),
            )
        except Exception as exc:
            logger.error(
                "agent_error",
                request_id=req_id,
                stage="api",
                latency_ms=elapsed_ms(started),
                error=str(exc),
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail=ErrorDetail(
                    code="agent_internal",
                    message=_ERROR_MESSAGES["agent_internal"],
                    request_id=req_id,
                ).model_dump(),
            )

    await cache_service.put(key, result.model_dump(mode="json"), patch_version=patch)
    logger.info("cache_store", request_id=req_id, stage="api", patch_version=patch)
    response.headers["X-Cache"] = "MISS"
    response.headers["X-Patch-Version"] = patch
    return result
