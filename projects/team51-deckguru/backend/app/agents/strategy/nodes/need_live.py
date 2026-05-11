"""Live Research를 실행할지 결정하는 조건부 라우터.

Strategy graph에서 `rag_retrieve` 다음에 호출되는 순수 함수다. LLM을 쓰지 않고
현재 state만 보고 live_research 노드로 갈지, 바로 analyze_meta로 갈지 결정한다.

실행 조건:
- RAG 평균 점수가 낮아 정적 데이터만으로 답변 근거가 약한 경우
- 질문에 "최신/오늘/latest/current meta" 같은 freshness 키워드가 있는 경우
- patch_summary 질문이고 패치가 배포된 지 3일 이하인 경우
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import structlog

from app.agents.strategy.state import StrategyState

logger = structlog.get_logger()

# 사용자가 "현재 상황"을 묻는 신호. 한/영 키워드를 함께 둔다.
FRESHNESS_KEYWORDS = (
    "이번 패치",
    "오늘",
    "최근",
    "어제",
    "현재 메타",
    "최신",
    "latest",
    "today",
    "recent",
    "current meta",
)
LIVE_RESEARCH_REASONS = {"low_rag_score", "freshness_keyword", "recent_patch_summary"}


def _patch_age_days(patch_version: str) -> int:
    """패치 배포 일수. 정확한 매핑은 RAG/Backend 쪽 patch-info에서 보강.

    여기서는 환경변수 PATCH_RELEASED_AT (ISO date) 가 있으면 사용, 없으면 99로 fallback
    (오래된 패치로 간주 — 보수적).
    """
    iso = os.getenv("PATCH_RELEASED_AT")
    if not iso:
        return 99
    try:
        released = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - released
        return delta.days
    except ValueError:
        return 99


def _need_live_reason(state: StrategyState) -> str:
    if state.intent in (None, "other"):
        return "unsupported_intent"
    if os.getenv("LIVE_RESEARCH_ENABLED", "true").lower() != "true":
        return "disabled_by_env"

    if state.rag_avg_score < 0.4:
        # 정적 RAG 검색 점수가 낮으면 외부 검색으로 근거를 보강한다.
        return "low_rag_score"
    question = state.question.lower()
    if any(k in question for k in FRESHNESS_KEYWORDS):
        # 최신성 질문은 RAG가 높은 점수를 줘도 live source 확인을 시도한다.
        return "freshness_keyword"
    if state.intent == "patch_summary" and _patch_age_days(state.patch_version) <= 3:
        # 패치 직후에는 정적 RAG가 아직 덜 쌓였을 가능성이 높다.
        return "recent_patch_summary"
    return "static_rag_sufficient"


def need_live(state: StrategyState) -> bool:
    """StrategyState를 보고 Live Research 필요 여부를 반환한다."""
    return _need_live_reason(state) in LIVE_RESEARCH_REASONS


def need_live_branch(state: StrategyState) -> str:
    """LangGraph conditional edge용 라우팅 키."""
    reason = _need_live_reason(state)
    route = "live" if reason in LIVE_RESEARCH_REASONS else "skip"
    logger.info(
        "live_research_route",
        request_id=state.request_id,
        stage="research",
        route=route,
        reason=reason,
        rag_avg_score=round(state.rag_avg_score, 3),
    )
    return route
