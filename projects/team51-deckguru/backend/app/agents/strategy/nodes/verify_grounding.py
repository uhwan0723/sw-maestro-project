"""verify_grounding — 02-spec §3.7.

100% 결정적. LLM 미사용. 5단계 필터:
1. core_units / key_items 화이트리스트 매칭 (RAG units/items 인덱스)
2. unit 3개 미만 → deck 제거
3. rationale 수치 → 컨텍스트에서 출처 추적 가능한 것만 유지, 아니면 정성 표현으로
4. 금지 표현 정규식 sanitize
5. confidence 산출 (rag_avg_score + sources count)
"""

from __future__ import annotations

import re
import time

import structlog

from app.agents.strategy.state import StrategyState
from app.observability import elapsed_ms
from app.rag.service import RagService, get_rag_service
from app.schemas.shared import DeckRecommendation, RagChunk, WebFact

logger = structlog.get_logger()

FORBIDDEN_RE = re.compile(
    r"(1\s*등\s*보장|승률\s*100\s*%?|무조건|확실히|반드시\s*1\s*등)"
)
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?%?")


def _all_quotes(
    rag_chunks: list[RagChunk],
    web_facts: list[WebFact],
    patch_version: str,
) -> str:
    """수치 출처 추적용. 모든 인용 가능한 텍스트 + metadata 값을 한 문자열로 모아 검색.

    metadata를 포함하지 않으면 stable_top4 / Top4 / 14.9 같은 도메인 리터럴이
    "근거 없는 수치"로 오인되어 정성 표현으로 강등됨. 사용자 응답 품질 저하.
    patch_version은 항상 sources에 있다고 봐야 함 (07-spec I10).
    """
    parts: list[str] = [patch_version]
    for c in rag_chunks:
        parts.append(c.text)
        # metadata 값 (스칼라/리스트) 도 출처로 인정
        for v in c.metadata.values():
            if isinstance(v, (str, int, float)):
                parts.append(str(v))
            elif isinstance(v, (list, tuple)):
                parts.extend(str(x) for x in v)
    for f in web_facts:
        parts.append(f.quote)
        parts.append(f.text)
    return "\n".join(parts)


def _filter_unsourced_numbers(text: str, sources_blob: str) -> str:
    def _replace(match: re.Match[str]) -> str:
        token = match.group(0)
        if token in sources_blob:
            return token
        # 출처 없음 → 정성 표현으로 강등 (단순 제거가 아닌 의미 보존)
        if "%" in token:
            return "(상당 비율)"
        return "(상당)"

    return NUMBER_RE.sub(_replace, text)


def _sanitize_forbidden(text: str) -> str:
    return FORBIDDEN_RE.sub("(현재 자료 기준 강세)", text)


def _filter_deck(
    deck: DeckRecommendation,
    *,
    units_wl: set[str],
    items_wl: set[str],
    sources_blob: str,
) -> DeckRecommendation | None:
    deck.core_units = [u for u in deck.core_units if u in units_wl]
    deck.key_items = [i for i in deck.key_items if i in items_wl]

    if len(deck.core_units) < 3:
        return None

    # rationale 후처리
    deck.rationale = _filter_unsourced_numbers(deck.rationale, sources_blob)
    deck.rationale = _sanitize_forbidden(deck.rationale)
    deck.fallback_plan = _sanitize_forbidden(deck.fallback_plan)

    return deck


def _fallback_whitelist_from_chunks(
    rag_chunks: list[RagChunk],
) -> tuple[set[str], set[str]]:
    units: set[str] = set()
    items: set[str] = set()
    for chunk in rag_chunks:
        if chunk.index != "deck_templates":
            continue
        core_units = chunk.metadata.get("core_units")
        key_items = chunk.metadata.get("key_items")
        if isinstance(core_units, list):
            units.update(str(unit) for unit in core_units if unit)
        if isinstance(key_items, list):
            items.update(str(item) for item in key_items if item)
    return units, items


def verify_grounding(
    state: StrategyState,
    *,
    rag: RagService | None = None,
) -> dict:
    started = time.perf_counter()
    before_count = len(state.final_decks)
    logger.info(
        "grounding_start",
        request_id=state.request_id,
        stage="grounding",
        decks=before_count,
        patch_version=state.patch_version,
    )
    active_rag = rag or get_rag_service()
    whitelist = active_rag.get_whitelist(state.patch_version)
    units_wl: set[str] = whitelist.get("units", set())
    items_wl: set[str] = whitelist.get("items", set())
    fallback_units, fallback_items = _fallback_whitelist_from_chunks(state.rag_chunks)
    if not units_wl:
        units_wl = fallback_units
    if not items_wl:
        items_wl = fallback_items

    sources_blob = _all_quotes(state.rag_chunks, state.web_facts, state.patch_version)

    filtered: list[DeckRecommendation] = []
    for deck in state.final_decks:
        result = _filter_deck(
            deck,
            units_wl=units_wl,
            items_wl=items_wl,
            sources_blob=sources_blob,
        )
        if result is None:
            state.warnings.append(
                f"deck_filtered_{deck.name}_insufficient_units"
            )
            continue
        filtered.append(result)

    state.final_decks = filtered

    # confidence 산출 — 07-spec §1.6 표
    if len(filtered) == 0:
        state.confidence = "low"
        if "all_decks_filtered" not in state.warnings:
            state.warnings.append("all_decks_filtered")
    elif state.rag_avg_score >= 0.6 and len(state.sources) >= 1:
        state.confidence = "high"
    else:
        state.confidence = "medium"

    if len(state.sources) == 1:
        state.warnings.append("single_source")

    state.node_latencies_ms["verify_grounding"] = elapsed_ms(started)
    logger.info(
        "grounding_done",
        request_id=state.request_id,
        stage="grounding",
        kept=len(filtered),
        filtered=before_count - len(filtered),
        confidence=state.confidence,
        units_whitelist=len(units_wl),
        items_whitelist=len(items_wl),
        warnings=len(state.warnings),
        latency_ms=state.node_latencies_ms["verify_grounding"],
    )
    return state.model_dump()
