"""analyze_meta — 02-spec §3.5.

LLM(T=0, structured)로 메타 한 단락 요약 + 후보 덱(≤5) 추출.
컨텍스트 외 새 덱 생성 금지 — 시스템 프롬프트로 강제.
"""

from __future__ import annotations

import json
import time

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
import structlog

from app.agents.strategy.llm import StrategyLLMError, call_structured
from app.agents.strategy.prompts import load_text
from app.agents.strategy.state import StrategyState
from app.observability import elapsed_ms
from app.schemas.shared import DeckDraft, RagChunk, WebFact

logger = structlog.get_logger()


class MetaOut(BaseModel):
    meta_summary: str = Field(max_length=400)
    candidate_decks: list[DeckDraft] = Field(default_factory=list, max_length=5)


def _serialize_chunks(chunks: list[RagChunk]) -> str:
    items = [
        {"id": c.id, "index": c.index, "text": c.text, "metadata": c.metadata}
        for c in chunks[:30]  # token 절약
    ]
    return json.dumps(items, ensure_ascii=False, indent=2)


def _serialize_web_facts(facts: list[WebFact]) -> str:
    if not facts:
        return "[]"
    items = [
        {"text": f.text, "quote": f.quote, "source_url": str(f.source_url)}
        for f in facts
    ]
    return json.dumps(items, ensure_ascii=False, indent=2)


async def analyze_meta(state: StrategyState) -> dict:
    started = time.perf_counter()
    if state.intent in (None, "other"):
        state.node_latencies_ms["analyze_meta"] = elapsed_ms(started)
        logger.info(
            "meta_skip",
            request_id=state.request_id,
            stage="meta",
            reason="unsupported_intent",
            latency_ms=state.node_latencies_ms["analyze_meta"],
        )
        return state.model_dump()

    logger.info(
        "meta_start",
        request_id=state.request_id,
        stage="meta",
        rag_chunks=len(state.rag_chunks),
        web_facts=len(state.web_facts),
    )
    system = load_text("meta").format(patch_version=state.patch_version)
    human = (
        f"[rag_chunks]\n{_serialize_chunks(state.rag_chunks)}\n\n"
        f"[web_facts]\n{_serialize_web_facts(state.web_facts)}\n\n"
        f"[intent]\n{state.intent}\n\n"
        f"[user_question]\n{state.question}\n"
    )

    try:
        result = await call_structured(
            role="meta",
            schema=MetaOut,
            messages=[SystemMessage(content=system), HumanMessage(content=human)],
            retries=1,
        )
        state.meta_summary = result.meta_summary
        state.candidate_decks = result.candidate_decks
    except StrategyLLMError as exc:
        logger.warning(
            "meta_failed",
            request_id=state.request_id,
            stage="meta",
            error=str(exc),
        )
        state.errors.append(f"analyze_meta_failed: {exc}")
        # meta 없이도 recommend가 RAG/web만으로 fallback 가능 — 빈 값 유지

    state.node_latencies_ms["analyze_meta"] = elapsed_ms(started)
    logger.info(
        "meta_done",
        request_id=state.request_id,
        stage="meta",
        candidates=len(state.candidate_decks),
        has_summary=bool(state.meta_summary),
        latency_ms=state.node_latencies_ms["analyze_meta"],
    )
    return state.model_dump()
