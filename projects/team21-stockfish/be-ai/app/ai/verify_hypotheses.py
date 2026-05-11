from collections.abc import Mapping, Sequence
import json
from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.ai.prompts.loader import load_prompt_messages
from app.ai.state import (
    AgentState,
    AnalysisHypothesis,
    HypothesisVerificationResult,
    IndicatorContext,
    NewsContext,
)
from app.core.llm import ChatMessage, UpstageLLMClient
from app.models.enums import RequestType
from app.schemas.common import WarningMessage


class HypothesisVerificationLLMResponse(BaseModel):
    verification_results: list[HypothesisVerificationResult] = Field(
        default_factory=list
    )
    confidence: float = Field(ge=0.0, le=1.0)
    warnings: list[WarningMessage] = Field(default_factory=list)


class StructuredLLMClient(Protocol):
    async def complete_structured(
        self,
        messages: Sequence[ChatMessage],
        *,
        response_model: type[HypothesisVerificationLLMResponse],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> HypothesisVerificationLLMResponse: ...


async def verify_hypotheses(
    state: AgentState | Mapping[str, Any],
    *,
    llm_client: StructuredLLMClient | None = None,
) -> dict[str, Any]:
    if _should_skip(state):
        return {}

    warnings = list(_read_existing_warnings(state))
    hypotheses = _read_hypotheses(state)
    if not hypotheses:
        warning = WarningMessage(
            code="hypotheses_missing",
            message="검증할 분석 가설이 없습니다.",
        )
        return {
            "verification_results": [],
            "confidence": 0.0,
            "warnings": [*warnings, warning],
        }

    verification = await _verify_hypotheses_with_llm(
        llm_client=llm_client,
        user_message=_read_user_message(state),
        hypotheses=hypotheses,
        indicator_context=_read_indicator_context(state),
        news_context=_read_news_context(state),
        warnings=warnings,
    )
    verification_results = _sanitize_verification_results(
        hypotheses=hypotheses,
        verification_results=verification.verification_results,
    )
    result_warnings = [
        warning for result in verification_results for warning in result.warnings
    ]
    confidence = _resolve_confidence(
        llm_confidence=verification.confidence,
        verification_results=verification_results,
    )

    return {
        "verification_results": verification_results,
        "confidence": confidence,
        "warnings": _deduplicate_warnings(
            [*warnings, *verification.warnings, *result_warnings]
        ),
    }


async def _verify_hypotheses_with_llm(
    *,
    llm_client: StructuredLLMClient | None,
    user_message: str,
    hypotheses: Sequence[AnalysisHypothesis],
    indicator_context: IndicatorContext | None,
    news_context: Sequence[NewsContext],
    warnings: Sequence[WarningMessage],
) -> HypothesisVerificationLLMResponse:
    if llm_client is not None:
        return await _request_verification(
            llm_client=llm_client,
            user_message=user_message,
            hypotheses=hypotheses,
            indicator_context=indicator_context,
            news_context=news_context,
            warnings=warnings,
        )

    client = UpstageLLMClient()
    try:
        return await _request_verification(
            llm_client=client,
            user_message=user_message,
            hypotheses=hypotheses,
            indicator_context=indicator_context,
            news_context=news_context,
            warnings=warnings,
        )
    finally:
        await client.aclose()


async def _request_verification(
    *,
    llm_client: StructuredLLMClient,
    user_message: str,
    hypotheses: Sequence[AnalysisHypothesis],
    indicator_context: IndicatorContext | None,
    news_context: Sequence[NewsContext],
    warnings: Sequence[WarningMessage],
) -> HypothesisVerificationLLMResponse:
    return await llm_client.complete_structured(
        _build_verification_messages(
            user_message=user_message,
            hypotheses=hypotheses,
            indicator_context=indicator_context,
            news_context=news_context,
            warnings=warnings,
        ),
        response_model=HypothesisVerificationLLMResponse,
        temperature=0.0,
        max_tokens=1400,
    )


def _build_verification_messages(
    *,
    user_message: str,
    hypotheses: Sequence[AnalysisHypothesis],
    indicator_context: IndicatorContext | None,
    news_context: Sequence[NewsContext],
    warnings: Sequence[WarningMessage],
) -> list[ChatMessage]:
    return load_prompt_messages(
        "hypothesis_verification",
        context=_json_dumps(
            _build_context_payload(
                user_message=user_message,
                hypotheses=hypotheses,
                indicator_context=indicator_context,
                news_context=news_context,
                warnings=warnings,
            )
        ),
    )


def _build_context_payload(
    *,
    user_message: str,
    hypotheses: Sequence[AnalysisHypothesis],
    indicator_context: IndicatorContext | None,
    news_context: Sequence[NewsContext],
    warnings: Sequence[WarningMessage],
) -> dict[str, Any]:
    return {
        "user_message": user_message,
        "hypotheses": [
            hypothesis.model_dump(mode="json") for hypothesis in hypotheses
        ],
        "indicator_context": (
            indicator_context.model_dump(mode="json")
            if indicator_context is not None
            else None
        ),
        "news_context": [
            article.model_dump(mode="json") for article in news_context
        ],
        "warnings": [warning.model_dump(mode="json") for warning in warnings],
    }


def _sanitize_verification_results(
    *,
    hypotheses: Sequence[AnalysisHypothesis],
    verification_results: Sequence[HypothesisVerificationResult],
) -> list[HypothesisVerificationResult]:
    result_by_title = {
        result.hypothesis_title: result
        for result in verification_results
        if result.hypothesis_title
    }

    sanitized: list[HypothesisVerificationResult] = []
    for hypothesis in hypotheses:
        result = result_by_title.get(hypothesis.title)
        if result is None:
            sanitized.append(_build_missing_result(hypothesis))
            continue
        sanitized.append(
            HypothesisVerificationResult(
                hypothesis_title=hypothesis.title,
                is_supported=result.is_supported,
                reason=result.reason.strip(),
                confidence=result.confidence,
                warnings=result.warnings,
            )
        )
    return sanitized


def _build_missing_result(
    hypothesis: AnalysisHypothesis,
) -> HypothesisVerificationResult:
    return HypothesisVerificationResult(
        hypothesis_title=hypothesis.title,
        is_supported=False,
        reason="LLM 검증 응답에 해당 가설의 검증 결과가 포함되지 않았습니다.",
        confidence=0.0,
        warnings=[
            WarningMessage(
                code="hypothesis_verification_missing",
                message=f"'{hypothesis.title}' 가설의 LLM 검증 결과가 없습니다.",
            )
        ],
    )


def _resolve_confidence(
    *,
    llm_confidence: float,
    verification_results: Sequence[HypothesisVerificationResult],
) -> float:
    if not verification_results:
        return 0.0
    if any(result.confidence == 0.0 for result in verification_results):
        return round(min(llm_confidence, _average_confidence(verification_results)), 2)
    return round(llm_confidence, 2)


def _average_confidence(
    verification_results: Sequence[HypothesisVerificationResult],
) -> float:
    return sum(result.confidence for result in verification_results) / len(
        verification_results
    )


def _should_skip(state: AgentState | Mapping[str, Any]) -> bool:
    if _has_final_answer(state):
        return True
    return _read_request_type(state) != RequestType.SECTOR_ANALYSIS


def _has_final_answer(state: AgentState | Mapping[str, Any]) -> bool:
    if isinstance(state, AgentState):
        return state.final_answer is not None

    final_answer = state.get("final_answer")
    return isinstance(final_answer, str) and bool(final_answer)


def _read_user_message(state: AgentState | Mapping[str, Any]) -> str:
    if isinstance(state, AgentState):
        return state.user_message

    value = state.get("user_message", "")
    return value if isinstance(value, str) else ""


def _read_request_type(state: AgentState | Mapping[str, Any]) -> RequestType | None:
    if isinstance(state, AgentState):
        return state.request_type

    value = state.get("request_type")
    if isinstance(value, RequestType):
        return value
    if isinstance(value, str):
        try:
            return RequestType(value)
        except ValueError:
            return None
    return None


def _read_indicator_context(
    state: AgentState | Mapping[str, Any],
) -> IndicatorContext | None:
    if isinstance(state, AgentState):
        return state.indicator_context

    value = state.get("indicator_context")
    if value is None:
        return None
    if isinstance(value, IndicatorContext):
        return value
    if isinstance(value, Mapping):
        return IndicatorContext.model_validate(value)
    return None


def _read_news_context(state: AgentState | Mapping[str, Any]) -> tuple[NewsContext, ...]:
    if isinstance(state, AgentState):
        return tuple(state.news_context)

    value = state.get("news_context")
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ()
    return tuple(_parse_news_context(article) for article in value)


def _parse_news_context(value: Any) -> NewsContext:
    if isinstance(value, NewsContext):
        return value
    if isinstance(value, Mapping):
        return NewsContext.model_validate(value)
    raise ValueError("news_context items must be NewsContext-compatible")


def _read_hypotheses(
    state: AgentState | Mapping[str, Any],
) -> tuple[AnalysisHypothesis, ...]:
    if isinstance(state, AgentState):
        return tuple(state.hypotheses)

    value = state.get("hypotheses", ())
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ()
    return tuple(_parse_hypothesis(hypothesis) for hypothesis in value)


def _parse_hypothesis(value: Any) -> AnalysisHypothesis:
    if isinstance(value, AnalysisHypothesis):
        return value
    if isinstance(value, Mapping):
        return AnalysisHypothesis.model_validate(value)
    raise ValueError("hypotheses items must be AnalysisHypothesis-compatible")


def _read_existing_warnings(
    state: AgentState | Mapping[str, Any],
) -> tuple[WarningMessage, ...]:
    if isinstance(state, AgentState):
        return tuple(state.warnings)

    value = state.get("warnings", ())
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ()
    return tuple(_parse_warning(warning) for warning in value)


def _parse_warning(value: Any) -> WarningMessage:
    if isinstance(value, WarningMessage):
        return value
    if isinstance(value, Mapping):
        return WarningMessage.model_validate(value)
    return WarningMessage(code="unknown_warning", message=str(value))


def _deduplicate_warnings(warnings: Sequence[WarningMessage]) -> list[WarningMessage]:
    deduplicated: list[WarningMessage] = []
    seen: set[tuple[str, str]] = set()
    for warning in warnings:
        key = (warning.code, warning.message)
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(warning)
    return deduplicated


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
