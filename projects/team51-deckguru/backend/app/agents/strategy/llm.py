"""LLM client wrapper — Upstage Solar.

- T=0 결정성
- structured output (Pydantic) 강제
- 1회 retry, 실패 시 호출자가 fallback 결정
- 모델 분리 (D1/D2): recommend/meta는 강력, intent는 cheap

ChatUpstage(`langchain-upstage`)는 .with_structured_output()을 통해
tool-calling 기반 schema 강제를 지원한다.
"""

from __future__ import annotations

import os
import time
from typing import TypeVar

from langchain_core.exceptions import OutputParserException
from langchain_core.messages import BaseMessage
from langchain_upstage import ChatUpstage
from pydantic import BaseModel, ValidationError
import structlog

from app.observability import elapsed_ms
from app.settings import settings

logger = structlog.get_logger()

T = TypeVar("T", bound=BaseModel)


class StrategyLLMError(RuntimeError):
    """LLM 호출이 retry 후에도 실패."""


def _model_for(role: str) -> str:
    env_key = f"UPSTAGE_MODEL_{role.upper()}"
    if model := os.getenv(env_key):
        return model
    if role == "recommend":
        return settings.upstage_model_recommend
    if role == "meta":
        return settings.upstage_model_meta
    if role == "intent":
        return settings.upstage_model_intent
    return "solar-mini"


def _build_chat(role: str) -> ChatUpstage:
    api_key = os.getenv("UPSTAGE_API_KEY") or settings.upstage_api_key
    if not api_key:
        raise StrategyLLMError("UPSTAGE_API_KEY not set")
    return ChatUpstage(
        model=_model_for(role),
        api_key=api_key,
        temperature=0.0,
    )


async def call_structured(
    role: str,
    schema: type[T],
    messages: list[BaseMessage],
    *,
    retries: int = 1,
) -> T:
    """structured output 강제 + 재시도.

    schema 검증 실패 시 retries회까지 재호출. 그래도 실패하면 StrategyLLMError.
    """
    model = _model_for(role)
    started = time.perf_counter()
    logger.info(
        "llm_call_start",
        stage="llm",
        role=role,
        model=model,
        schema=schema.__name__,
        max_attempts=retries + 1,
    )
    chat = _build_chat(role)
    structured = chat.with_structured_output(schema)

    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            result = await structured.ainvoke(messages)
            if not isinstance(result, schema):
                # with_structured_output가 dict를 줄 때 대비
                result = schema.model_validate(result)
            logger.info(
                "llm_call_done",
                stage="llm",
                role=role,
                model=model,
                attempt=attempt + 1,
                latency_ms=elapsed_ms(started),
            )
            return result
        except (ValidationError, OutputParserException, ValueError) as exc:
            last_err = exc
            logger.warning(
                "llm_structured_fail",
                stage="llm",
                role=role,
                model=model,
                attempt=attempt + 1,
                error=str(exc),
            )

    logger.error(
        "llm_call_failed",
        stage="llm",
        role=role,
        model=model,
        latency_ms=elapsed_ms(started),
        error=str(last_err),
    )
    raise StrategyLLMError(
        f"structured output failed after {retries + 1} attempts: {last_err}"
    )
