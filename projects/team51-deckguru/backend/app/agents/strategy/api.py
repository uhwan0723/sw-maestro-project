"""Backend → Strategy Agent 단일 진입점 — 02-spec §5, 08-spec §2.1.

`run_strategy_agent`만 외부에 노출. 내부 그래프는 graph.COMPILED_GRAPH.
"""

from __future__ import annotations

import asyncio
import os
import time

import structlog

from app.agents.strategy.graph import COMPILED_GRAPH
from app.agents.strategy.llm import StrategyLLMError
from app.agents.strategy.nodes.format_response import format_response
from app.agents.strategy.state import StrategyState
from app.observability import elapsed_ms, preview
from app.schemas.api import RecommendationResponse
from app.schemas.shared import PlayStyle, Tier
from app.settings import settings

logger = structlog.get_logger()


class RecommendationTimeout(TimeoutError):
    """Strategy Agent timeout — Backend는 504 agent_timeout 으로 매핑."""


class RecommendationFailed(RuntimeError):
    """recommend LLM이 schema 검증 2회 연속 실패 — Backend는 502 agent_failed 로 매핑.

    01-spec §5.2 / 02-spec §3.6 의 "schema fail 2회 → 502" 정책.
    """


async def run_strategy_agent(
    request_id: str,
    tier: Tier,
    play_style: PlayStyle,
    question: str,
    *,
    patch_version: str | None = None,
    timeout_s: float = 25.0,
) -> RecommendationResponse:
    patch_version = patch_version or os.getenv("PATCH_VERSION", settings.patch_version)
    started = time.perf_counter()

    initial = StrategyState(
        request_id=request_id,
        patch_version=patch_version,
        tier=tier,
        play_style=play_style,
        question=question,
    )
    logger.info(
        "strategy_start",
        request_id=request_id,
        stage="strategy",
        patch_version=patch_version,
        tier=tier,
        play_style=play_style,
        question=preview(question),
    )

    try:
        # LangGraph는 dict로 state를 반환. Pydantic 모델로 다시 검증.
        raw = await asyncio.wait_for(
            COMPILED_GRAPH.ainvoke(initial),
            timeout=timeout_s,
        )
    except asyncio.TimeoutError as exc:
        logger.error(
            "strategy_timeout",
            request_id=request_id,
            stage="strategy",
            timeout_s=timeout_s,
            latency_ms=elapsed_ms(started),
        )
        raise RecommendationTimeout(
            f"strategy agent exceeded {timeout_s}s"
        ) from exc
    except StrategyLLMError as exc:
        # recommend / analyze_meta / analyze_intent 의 최종 실패가 여기로 전파됨.
        # analyze_intent 는 자체 fallback이 있으니 여기로 오는 건 사실상 recommend 의 schema fail.
        logger.error(
            "strategy_llm_failed",
            request_id=request_id,
            stage="strategy",
            latency_ms=elapsed_ms(started),
            error=str(exc),
        )
        raise RecommendationFailed(str(exc)) from exc

    final_state = StrategyState.model_validate(raw)
    response = format_response(final_state)
    logger.info(
        "strategy_done",
        request_id=request_id,
        stage="strategy",
        intent=response.intent,
        rag_chunks=len(final_state.rag_chunks),
        rag_avg_score=round(final_state.rag_avg_score, 3),
        web_facts=len(final_state.web_facts),
        decks=len(response.decks),
        confidence=response.confidence,
        warnings=len(response.warnings),
        latency_ms=elapsed_ms(started),
    )
    return response


__all__ = ["run_strategy_agent", "RecommendationTimeout", "RecommendationFailed"]
