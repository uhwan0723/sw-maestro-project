"""format_response — 02-spec §3.8.

결정적. RecommendationResponse Pydantic 모델로 매핑.
intent=other 단축 경로에서도 단일 진입점 보장.
불변식(07-spec §4.1) I4 ~ I8을 여기서 강제.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone

import structlog

from app.agents.strategy.state import StrategyState
from app.observability import elapsed_ms
from app.schemas.api import DebugInfo, RecommendationResponse

logger = structlog.get_logger()

OTHER_MESSAGE = (
    "이 질문은 DeckGuru의 지원 범위(덱 추천 / 운영법 / 아이템 피벗 / 패치 요약) 밖이에요. "
    "롤토체스 메타·덱 관련 질문을 입력해 주세요."
)


PATCH_SUMMARY_FALLBACK = (
    "현재 패치의 통계 자료가 충분하지 않아 메타 요약을 자세히 생성하지 못했어요. "
    "패치 직후에는 데이터가 누적되는 데 며칠 걸려요. "
    "잠시 후 다시 시도하거나, 직전 패치 기준 추천을 참고해 주세요."
)
GENERIC_FALLBACK = "현재 보유한 자료를 바탕으로 추천을 생성했어요."


def _coerce_meta_summary(state: StrategyState) -> str:
    if state.intent == "other":
        return OTHER_MESSAGE
    if state.intent == "patch_summary":
        # I7 (07-spec §4.1): patch_summary ⇒ meta_summary ≥ 100자.
        if state.meta_summary and len(state.meta_summary) >= 100:
            return state.meta_summary
        return PATCH_SUMMARY_FALLBACK
    if state.meta_summary:
        return state.meta_summary
    return GENERIC_FALLBACK


def format_response(state: StrategyState) -> RecommendationResponse:
    decks = state.final_decks if state.intent != "other" else []
    confidence = state.confidence
    if not decks:
        confidence = "low"  # I4: len(decks)==0 ⇔ confidence=="low"

    debug = None
    if os.getenv("DEMO_MODE", "false").lower() == "true":
        debug = DebugInfo(
            react_steps=state.research_steps,
            rag_avg_score=state.rag_avg_score,
            tier2_triggered=state.need_live,
            node_latencies_ms=state.node_latencies_ms,
        )

    return RecommendationResponse(
        request_id=state.request_id,
        patch_version=state.patch_version,
        intent=state.intent or "other",
        meta_summary=_coerce_meta_summary(state),
        decks=decks,
        sources=state.sources,
        confidence=confidence,
        warnings=state.warnings,
        generated_at=datetime.now(timezone.utc),
        debug=debug,
    )


async def format_response_node(state: StrategyState) -> dict:
    """LangGraph 노드 어댑터. 결과는 state 자체에 저장하지 않고
    api.py의 entrypoint가 최종 state로부터 RecommendationResponse를 빌드.

    여기서는 state를 그대로 반환 (graph 종단). 실제 변환은 format_response().
    """
    started = time.perf_counter()
    state.node_latencies_ms["format_response"] = elapsed_ms(started)
    logger.info(
        "response_ready",
        request_id=state.request_id,
        stage="response",
        intent=state.intent or "other",
        decks=len(state.final_decks) if state.intent != "other" else 0,
        confidence=state.confidence if state.final_decks else "low",
        warnings=len(state.warnings),
        latency_ms=state.node_latencies_ms["format_response"],
    )
    return state.model_dump()
