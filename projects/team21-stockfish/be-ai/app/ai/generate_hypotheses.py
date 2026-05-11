from collections.abc import Mapping, Sequence
import json
from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.ai.history import EMPTY_HISTORY_PLACEHOLDER, format_history_text
from app.ai.prompts.loader import load_prompt_messages
from app.ai.state import (
    AgentState,
    AnalysisHypothesis,
    IndicatorContext,
    NewsContext,
)
from app.core.llm import ChatMessage, UpstageLLMClient
from app.models.enums import RequestType, SectorCode, SECTOR_LABELS
from app.schemas.chat import ChatTurn
from app.schemas.common import SourceInfo, WarningMessage


MAX_NEWS_CONTEXT_ITEMS = 12
MAX_BASIS_ITEMS = 5


class HypothesisGenerationLLMResponse(BaseModel):
    hypotheses: list[AnalysisHypothesis] = Field(default_factory=list)
    warnings: list[WarningMessage] = Field(default_factory=list)


class StructuredLLMClient(Protocol):
    async def complete_structured(
        self,
        messages: Sequence[ChatMessage],
        *,
        response_model: type[HypothesisGenerationLLMResponse],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> HypothesisGenerationLLMResponse: ...


async def generate_hypotheses(
    state: AgentState | Mapping[str, Any],
    *,
    llm_client: StructuredLLMClient | None = None,
) -> dict[str, Any]:
    if _should_skip(state):
        return {}

    warnings = list(_read_existing_warnings(state))
    existing_hypotheses = list(_read_existing_hypotheses(state))
    indicator_context = _read_indicator_context(state)
    news_context = _read_news_context(state)

    if indicator_context is None and not news_context:
        warnings.append(
            WarningMessage(
                code="hypothesis_context_missing",
                message="LLM 분석 가설을 생성할 지표와 뉴스 컨텍스트가 없습니다.",
            )
        )
        return {
            "hypotheses": existing_hypotheses,
            "warnings": warnings,
        }

    news_context_for_llm = news_context[:MAX_NEWS_CONTEXT_ITEMS]
    allowed_sources = _build_allowed_sources(
        indicator_context=indicator_context,
        news_context=news_context_for_llm,
    )
    generation = await _generate_hypotheses_with_llm(
        llm_client=llm_client,
        user_message=_read_user_message(state),
        sector=_read_sector(state),
        indicator_context=indicator_context,
        news_context=news_context_for_llm,
        warnings=warnings,
        chat_history=_read_chat_history(state),
    )
    generated_hypotheses = _sanitize_hypotheses(
        hypotheses=generation.hypotheses,
        allowed_sources=allowed_sources,
    )
    warnings.extend(generation.warnings)

    if not generated_hypotheses:
        warnings.append(
            WarningMessage(
                code="llm_hypothesis_generation_empty",
                message="LLM이 검토 가능한 분석 가설을 생성하지 못했습니다.",
            )
        )

    return {
        "hypotheses": _deduplicate_hypotheses(
            [*existing_hypotheses, *generated_hypotheses]
        ),
        "warnings": _deduplicate_warnings(warnings),
    }


async def _generate_hypotheses_with_llm(
    *,
    llm_client: StructuredLLMClient | None,
    user_message: str,
    sector: SectorCode | None,
    indicator_context: IndicatorContext | None,
    news_context: Sequence[NewsContext],
    warnings: Sequence[WarningMessage],
    chat_history: Sequence[ChatTurn],
) -> HypothesisGenerationLLMResponse:
    if llm_client is not None:
        return await _request_hypotheses(
            llm_client=llm_client,
            user_message=user_message,
            sector=sector,
            indicator_context=indicator_context,
            news_context=news_context,
            warnings=warnings,
            chat_history=chat_history,
        )

    client = UpstageLLMClient()
    try:
        return await _request_hypotheses(
            llm_client=client,
            user_message=user_message,
            sector=sector,
            indicator_context=indicator_context,
            news_context=news_context,
            warnings=warnings,
            chat_history=chat_history,
        )
    finally:
        await client.aclose()


async def _request_hypotheses(
    *,
    llm_client: StructuredLLMClient,
    user_message: str,
    sector: SectorCode | None,
    indicator_context: IndicatorContext | None,
    news_context: Sequence[NewsContext],
    warnings: Sequence[WarningMessage],
    chat_history: Sequence[ChatTurn],
) -> HypothesisGenerationLLMResponse:
    return await llm_client.complete_structured(
        _build_hypothesis_messages(
            user_message=user_message,
            sector=sector,
            indicator_context=indicator_context,
            news_context=news_context,
            warnings=warnings,
            chat_history=chat_history,
        ),
        response_model=HypothesisGenerationLLMResponse,
        temperature=0.2,
        max_tokens=1400,
    )


def _build_hypothesis_messages(
    *,
    user_message: str,
    sector: SectorCode | None,
    indicator_context: IndicatorContext | None,
    news_context: Sequence[NewsContext],
    warnings: Sequence[WarningMessage],
    chat_history: Sequence[ChatTurn],
) -> list[ChatMessage]:
    return load_prompt_messages(
        "hypothesis_generation",
        context=_json_dumps(
            _build_context_payload(
                user_message=user_message,
                sector=sector,
                indicator_context=indicator_context,
                news_context=news_context,
                warnings=warnings,
            )
        ),
        chat_history=format_history_text(
            list(chat_history),
            empty_placeholder=EMPTY_HISTORY_PLACEHOLDER,
        ),
    )


def _build_context_payload(
    *,
    user_message: str,
    sector: SectorCode | None,
    indicator_context: IndicatorContext | None,
    news_context: Sequence[NewsContext],
    warnings: Sequence[WarningMessage],
) -> dict[str, Any]:
    return {
        "user_message": user_message,
        "sector": sector.value if sector else None,
        "sector_label": _format_sector_label(sector),
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


def _build_allowed_sources(
    *,
    indicator_context: IndicatorContext | None,
    news_context: Sequence[NewsContext],
) -> dict[str, SourceInfo]:
    sources: list[SourceInfo] = []
    if indicator_context is not None:
        sources.extend(_build_indicator_sources(indicator_context))
    sources.extend(_build_news_sources(news_context))
    return {source.url: source for source in sources}


def _build_indicator_sources(
    indicator_context: IndicatorContext,
) -> list[SourceInfo]:
    providers = sorted(
        {
            source
            for ticker in indicator_context.tickers
            for source in ticker.sources
            if source
        }
    )
    provider = ", ".join(providers) if providers else "market_metrics"
    return [
        SourceInfo(
            title="KOSPI 섹터 시장 지표",
            url=f"market://{indicator_context.sector.value}/{indicator_context.reference_date.isoformat()}",
            provider=provider,
        )
    ]


def _build_news_sources(
    news_context: Sequence[NewsContext],
) -> list[SourceInfo]:
    return [
        SourceInfo(
            title=article.title,
            url=article.url,
            provider=article.source,
            published_at=article.published_at,
        )
        for article in news_context
    ]


def _sanitize_hypotheses(
    *,
    hypotheses: Sequence[AnalysisHypothesis],
    allowed_sources: Mapping[str, SourceInfo],
) -> list[AnalysisHypothesis]:
    sanitized: list[AnalysisHypothesis] = []
    for hypothesis in hypotheses:
        title = hypothesis.title.strip()
        description = hypothesis.description.strip()
        if not title or not description:
            continue

        sanitized.append(
            AnalysisHypothesis(
                title=title,
                description=description,
                basis=[
                    basis.strip()
                    for basis in hypothesis.basis[:MAX_BASIS_ITEMS]
                    if basis.strip()
                ],
                sources=_filter_allowed_sources(
                    sources=hypothesis.sources,
                    allowed_sources=allowed_sources,
                ),
            )
        )
    return sanitized


def _filter_allowed_sources(
    *,
    sources: Sequence[SourceInfo],
    allowed_sources: Mapping[str, SourceInfo],
) -> list[SourceInfo]:
    filtered: list[SourceInfo] = []
    seen_urls: set[str] = set()
    for source in sources:
        allowed_source = allowed_sources.get(source.url)
        if allowed_source is None or allowed_source.url in seen_urls:
            continue
        seen_urls.add(allowed_source.url)
        filtered.append(allowed_source)
    return filtered


def _deduplicate_hypotheses(
    hypotheses: Sequence[AnalysisHypothesis],
) -> list[AnalysisHypothesis]:
    deduplicated: list[AnalysisHypothesis] = []
    seen_titles: set[str] = set()
    for hypothesis in hypotheses:
        if hypothesis.title in seen_titles:
            continue
        seen_titles.add(hypothesis.title)
        deduplicated.append(hypothesis)
    return deduplicated


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


def _read_sector(state: AgentState | Mapping[str, Any]) -> SectorCode | None:
    if isinstance(state, AgentState):
        return state.sector

    value = state.get("sector")
    if isinstance(value, SectorCode):
        return value
    if isinstance(value, str):
        try:
            return SectorCode(value)
        except ValueError:
            return None
    return None


def _read_chat_history(state: AgentState | Mapping[str, Any]) -> list[ChatTurn]:
    if isinstance(state, AgentState):
        return list(state.chat_history)

    raw = state.get("chat_history", [])
    if not isinstance(raw, list):
        return []

    history: list[ChatTurn] = []
    for item in raw:
        if isinstance(item, ChatTurn):
            history.append(item)
        elif isinstance(item, Mapping):
            history.append(ChatTurn.model_validate(item))
    return history


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


def _read_existing_hypotheses(
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


def _format_sector_label(sector: SectorCode | None) -> str:
    if sector is None:
        return "대상"
    return SECTOR_LABELS.get(sector, sector.value)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
