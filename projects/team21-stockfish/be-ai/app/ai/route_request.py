from collections.abc import Mapping
from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.ai.history import EMPTY_HISTORY_PLACEHOLDER, format_history_text
from app.ai.prompts.loader import load_prompt_messages
from app.ai.state import AgentState
from app.core.llm import ChatMessage, UpstageLLMClient
from app.models.enums import RequestType, SectorCode
from app.schemas.chat import ChatTurn
from app.schemas.common import WarningMessage


OUT_OF_SCOPE_WARNING = WarningMessage(
    code="out_of_scope_request",
    message="지원 범위는 KOSPI 반도체/제약 섹터 분석과 경제 용어 설명입니다.",
)


class RouteRequestLLMResponse(BaseModel):
    request_type: RequestType
    sector: SectorCode | None = None
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    final_answer: str | None = None


class StructuredLLMClient(Protocol):
    async def complete_structured(
        self,
        messages: list[ChatMessage],
        *,
        response_model: type[RouteRequestLLMResponse],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> RouteRequestLLMResponse: ...


async def route_request(
    state: AgentState | Mapping[str, Any],
    *,
    llm_client: StructuredLLMClient | None = None,
) -> dict[str, Any]:
    if _is_already_blocked(state):
        return {}

    user_message = _read_user_message(state)
    chat_history = _read_chat_history(state)
    if llm_client is not None:
        route = await _classify_request(
            llm_client=llm_client,
            user_message=user_message,
            chat_history=chat_history,
        )
    else:
        client = UpstageLLMClient()
        try:
            route = await _classify_request(
                llm_client=client,
                user_message=user_message,
                chat_history=chat_history,
            )
        finally:
            await client.aclose()

    return _build_state_update(route=route, state=state)


async def _classify_request(
    *,
    llm_client: StructuredLLMClient,
    user_message: str,
    chat_history: list[ChatTurn],
) -> RouteRequestLLMResponse:
    return await llm_client.complete_structured(
        _build_route_messages(user_message=user_message, chat_history=chat_history),
        response_model=RouteRequestLLMResponse,
        temperature=0.0,
        max_tokens=500,
    )


def _build_route_messages(
    *,
    user_message: str,
    chat_history: list[ChatTurn],
) -> list[ChatMessage]:
    return load_prompt_messages(
        "request_routing",
        user_message=user_message,
        chat_history=format_history_text(
            chat_history,
            empty_placeholder=EMPTY_HISTORY_PLACEHOLDER,
        ),
    )


def _build_state_update(
    *,
    route: RouteRequestLLMResponse,
    state: AgentState | Mapping[str, Any],
) -> dict[str, Any]:
    update: dict[str, Any] = {
        "request_type": route.request_type,
        "sector": route.sector,
    }

    if route.request_type is RequestType.OUT_OF_SCOPE:
        update["final_answer"] = route.final_answer or (
            "현재는 KOSPI 반도체/제약 섹터 분석과 경제 용어 설명만 지원합니다."
        )
        update["warnings"] = [
            *_read_existing_warnings(state),
            OUT_OF_SCOPE_WARNING,
        ]

    return update


def _is_already_blocked(state: AgentState | Mapping[str, Any]) -> bool:
    if isinstance(state, AgentState):
        return state.final_answer is not None

    value = state.get("final_answer")
    return isinstance(value, str) and bool(value)


def _read_user_message(state: AgentState | Mapping[str, Any]) -> str:
    if isinstance(state, AgentState):
        return state.user_message

    value = state.get("user_message", "")
    return value if isinstance(value, str) else ""


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
    return WarningMessage(code="unknown_warning", message=str(value))
