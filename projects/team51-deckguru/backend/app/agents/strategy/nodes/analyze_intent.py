"""analyze_intent — 02-spec §3.1.

LLM(small, T=0)으로 사용자 질문을 5개 enum + 키워드로 분류.
schema fail → 1회 retry → fallback intent=other.
"""

from __future__ import annotations

import json
import time

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
import structlog

from app.agents.strategy.llm import StrategyLLMError, call_structured
from app.agents.strategy.prompts import load_json
from app.agents.strategy.state import StrategyState
from app.observability import elapsed_ms
from app.schemas.shared import Intent

logger = structlog.get_logger()

_DECK_TERMS = ("덱", "추천", "티어", "메타", "deck", "recommend", "tier", "meta")
_PLAYSTYLE_TERMS = ("운영법", "빌드업", "초반", "중반", "후반", "play", "phase", "guide")
_ITEM_TERMS = ("아이템", "피벗", "곡궁", "bf", "대검", "장갑", "지팡이", "item", "pivot", "sword")
_PATCH_TERMS = ("패치", "요약", "변경점", "버프", "너프", "patch", "summary", "buff", "nerf")


class IntentOut(BaseModel):
    intent: Intent
    extracted_keywords: list[str] = Field(default_factory=list, max_length=5)


def _build_messages(question: str) -> list:
    cfg = load_json("intent")
    examples = cfg["examples"]
    fewshot = "\n".join(
        f'Question: {ex["q"]}\nResult: {{"intent":"{ex["intent"]}","extracted_keywords":{json.dumps(ex["extracted_keywords"], ensure_ascii=False)}}}'
        for ex in examples
    )
    sys_prompt = cfg["system"] + "\n\n[Examples]\n" + fewshot
    return [
        SystemMessage(content=sys_prompt),
        HumanMessage(content=f"Question: {question}\nResult:"),
    ]


def _rule_based_intent(question: str) -> IntentOut | None:
    normalized = question.lower()
    keywords: list[str] = []

    if any(term in normalized for term in _ITEM_TERMS):
        keywords = [term for term in ("곡궁", "BF대검", "아이템", "피벗") if term.lower() in normalized]
        return IntentOut(intent="item_pivot", extracted_keywords=keywords[:5])

    if any(term in normalized for term in _PLAYSTYLE_TERMS):
        keywords = [term for term in ("운영법", "초반", "중반", "후반", "빌드업") if term.lower() in normalized]
        return IntentOut(intent="deck_playstyle", extracted_keywords=keywords[:5])

    if any(term in normalized for term in _DECK_TERMS):
        keywords = [term for term in ("현재 패치", "17.2", "골드", "티어", "덱", "메타") if term.lower() in normalized]
        return IntentOut(intent="recommend_deck", extracted_keywords=keywords[:5])

    if any(term in normalized for term in _PATCH_TERMS):
        keywords = [term for term in ("17.2", "패치", "요약", "변경점", "버프", "너프") if term.lower() in normalized]
        return IntentOut(intent="patch_summary", extracted_keywords=keywords[:5])

    return None


async def analyze_intent(state: StrategyState) -> dict:
    started = time.perf_counter()
    logger.info("intent_start", request_id=state.request_id, stage="intent")
    try:
        result = await call_structured(
            role="intent",
            schema=IntentOut,
            messages=_build_messages(state.question),
            retries=1,
        )
        fallback = _rule_based_intent(state.question)
        if result.intent == "other" and fallback is not None:
            logger.info(
                "intent_other_overridden",
                request_id=state.request_id,
                stage="intent",
                fallback=fallback.intent,
            )
            result = fallback
        state.intent = result.intent
        state.extracted_keywords = result.extracted_keywords
    except StrategyLLMError as exc:
        fallback = _rule_based_intent(state.question)
        if fallback is not None:
            logger.warning(
                "intent_llm_failed_using_rule_fallback",
                request_id=state.request_id,
                stage="intent",
                error=str(exc),
            )
            state.intent = fallback.intent
            state.extracted_keywords = fallback.extracted_keywords
            state.warnings.append("intent_classification_fallback")
        else:
            logger.warning(
                "intent_failed_using_other",
                request_id=state.request_id,
                stage="intent",
                error=str(exc),
            )
            state.intent = "other"
            state.warnings.append("intent_classification_failed")

    state.node_latencies_ms["analyze_intent"] = elapsed_ms(started)
    logger.info(
        "intent_done",
        request_id=state.request_id,
        stage="intent",
        intent=state.intent,
        keywords=state.extracted_keywords,
        latency_ms=state.node_latencies_ms["analyze_intent"],
    )
    return state.model_dump()
