"""recommend — 02-spec §3.6.

LLM(T=0, structured)로 사용자 조건 + 컨텍스트 → final_decks(≤3).
verify_grounding이 후처리로 화이트리스트/수치/금지어 필터링.
"""

from __future__ import annotations

import json
import time

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
import structlog

from app.agents.strategy.llm import call_structured
from app.agents.strategy.prompts import load_text
from app.agents.strategy.state import StrategyState
from app.observability import elapsed_ms
from app.schemas.shared import DeckDraft, DeckRecommendation, RagChunk, WebFact

logger = structlog.get_logger()


class RecommendOut(BaseModel):
    decks: list[DeckRecommendation] = Field(default_factory=list, max_length=3)


def _serialize_chunks(chunks: list[RagChunk]) -> str:
    items = [
        {"id": c.id, "index": c.index, "text": c.text, "metadata": c.metadata}
        for c in chunks[:30]
    ]
    return json.dumps(items, ensure_ascii=False, indent=2)


def _serialize_web_facts(facts: list[WebFact]) -> str:
    if not facts:
        return "[]"
    return json.dumps(
        [
            {
                "text": f.text,
                "quote": f.quote,
                "source_url": str(f.source_url),
                "extraction_confidence": f.extraction_confidence,
            }
            for f in facts
        ],
        ensure_ascii=False,
        indent=2,
    )


def _serialize_drafts(drafts: list[DeckDraft]) -> str:
    if not drafts:
        return "[]"
    return json.dumps(
        [d.model_dump() for d in drafts], ensure_ascii=False, indent=2,
    )


async def recommend(state: StrategyState) -> dict:
    started = time.perf_counter()
    if state.intent in (None, "other"):
        state.node_latencies_ms["recommend"] = elapsed_ms(started)
        logger.info(
            "recommend_skip",
            request_id=state.request_id,
            stage="recommend",
            reason="unsupported_intent",
            latency_ms=state.node_latencies_ms["recommend"],
        )
        return state.model_dump()

    logger.info(
        "recommend_start",
        request_id=state.request_id,
        stage="recommend",
        candidates=len(state.candidate_decks),
        rag_chunks=len(state.rag_chunks),
        web_facts=len(state.web_facts),
    )
    system = load_text("recommend").format(
        patch_version=state.patch_version,
        tier=state.tier,
        play_style=state.play_style,
        intent=state.intent,
    )
    human = (
        f"[meta_summary]\n{state.meta_summary or '(미생성)'}\n\n"
        f"[candidate_decks]\n{_serialize_drafts(state.candidate_decks)}\n\n"
        f"[rag_chunks]\n{_serialize_chunks(state.rag_chunks)}\n\n"
        f"[web_facts]\n{_serialize_web_facts(state.web_facts)}\n\n"
        f"[user_question]\n{state.question}\n"
    )

    # 01-spec §5.2: recommend가 schema fail 2회 연속(=시도 2회 모두 실패)이면
    # 502 agent_failed 로 매핑되어야 함. retries=1 → 최초 시도 + 1회 retry = 2회.
    # 최종 실패 시 StrategyLLMError 를 그대로 전파 → run_strategy_agent 에서 캐치.
    result = await call_structured(
        role="recommend",
        schema=RecommendOut,
        messages=[SystemMessage(content=system), HumanMessage(content=human)],
        retries=1,
    )
    state.final_decks = result.decks
    state.node_latencies_ms["recommend"] = elapsed_ms(started)
    logger.info(
        "recommend_done",
        request_id=state.request_id,
        stage="recommend",
        decks=len(state.final_decks),
        latency_ms=state.node_latencies_ms["recommend"],
    )
    return state.model_dump()
