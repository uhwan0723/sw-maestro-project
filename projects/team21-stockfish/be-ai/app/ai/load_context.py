from collections.abc import Mapping
from typing import Any, Protocol

from app.ai.state import AgentState, IndicatorContext, NewsContext
from app.db.session import async_session_factory
from app.models.enums import RequestType, SectorCode
from app.schemas.common import WarningMessage
from app.services.context_service import AgentInputContext, ContextService


class SectorContextService(Protocol):
    async def build_sector_context(
        self,
        sector: SectorCode,
    ) -> AgentInputContext: ...


async def load_context(
    state: AgentState | Mapping[str, Any],
    *,
    context_service: SectorContextService | None = None,
) -> dict[str, Any]:
    if _should_skip(state):
        return {}

    sector = _read_sector(state)
    if sector is None:
        return {
            "warnings": [
                *_read_existing_warnings(state),
                WarningMessage(
                    code="context_sector_missing",
                    message="섹터 분석 컨텍스트를 로딩할 섹터가 지정되지 않았습니다.",
                ),
            ],
        }

    if context_service is not None:
        context = await context_service.build_sector_context(sector)
    else:
        async with async_session_factory() as session:
            context = await ContextService(session).build_sector_context(sector)

    return {
        "indicator_context": IndicatorContext.model_validate(
            context.indicators.to_payload()
        ),
        "news_context": [
            NewsContext.model_validate(article.to_payload())
            for article in context.news_articles
        ],
        "warnings": _deduplicate_warnings(
            [
                *_read_existing_warnings(state),
                *context.warnings,
            ]
        ),
    }


def _should_skip(state: AgentState | Mapping[str, Any]) -> bool:
    if _has_final_answer(state):
        return True

    request_type = _read_request_type(state)
    return request_type is not RequestType.SECTOR_ANALYSIS


def _has_final_answer(state: AgentState | Mapping[str, Any]) -> bool:
    if isinstance(state, AgentState):
        return state.final_answer is not None

    value = state.get("final_answer")
    return isinstance(value, str) and bool(value)


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


def _read_existing_warnings(
    state: AgentState | Mapping[str, Any],
) -> tuple[WarningMessage, ...]:
    if isinstance(state, AgentState):
        return tuple(state.warnings)

    warnings = state.get("warnings", ())
    if not isinstance(warnings, list | tuple):
        return ()

    return tuple(_parse_warning(warning) for warning in warnings)


def _parse_warning(value: Any) -> WarningMessage:
    if isinstance(value, WarningMessage):
        return value
    if isinstance(value, Mapping):
        return WarningMessage.model_validate(value)
    raise ValueError("warnings must be WarningMessage-compatible")


def _deduplicate_warnings(
    warnings: list[WarningMessage],
) -> list[WarningMessage]:
    deduplicated: list[WarningMessage] = []
    seen: set[tuple[str, str]] = set()
    for warning in warnings:
        key = (warning.code, warning.message)
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(warning)
    return deduplicated
