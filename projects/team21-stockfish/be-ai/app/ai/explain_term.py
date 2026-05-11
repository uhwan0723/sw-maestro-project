from collections.abc import Mapping, Sequence
from typing import Any, Protocol, Self

from pydantic import BaseModel, Field, model_validator

from app.ai.history import EMPTY_HISTORY_PLACEHOLDER, format_history_text
from app.ai.prompts.loader import load_prompt_messages
from app.ai.state import AgentState
from app.core.llm import ChatMessage, UpstageLLMClient
from app.models.enums import SECTOR_LABELS, RequestType, SectorCode
from app.schemas.chat import ChatTurn
from app.schemas.common import WarningMessage

TERM_EXPLANATION_SAFETY_NOTICE = (
    "이 설명은 경제 용어 이해를 돕기 위한 교육용 정보이며, "
    "매수/매도/보유 판단이나 매매 시점 추천이 아닙니다."
)
OUT_OF_SCOPE_WARNING = WarningMessage(
    code="term_explanation_out_of_scope",
    message="경제, 금융, 주식시장 용어 설명 범위를 벗어난 요청입니다.",
)
SAFETY_NOTICE_SECTION_LABEL = "안전 안내"


class TermExplanationLLMResponse(BaseModel):
    request_type: RequestType
    term: str | None = None
    answer: str = Field(
        description=(
            "용어 설명 본문만 작성합니다. safety_notice 내용이나 '안전 안내' 섹션은 포함하지 않습니다."
        )
    )
    example: str | None = Field(
        default=None,
        description=(
            "선택 예시만 작성합니다. safety_notice 내용이나 '안전 안내' 섹션은 포함하지 않습니다."
        ),
    )
    safety_notice: str | None = Field(
        default=None,
        description=(
            "투자 조언이 아니라는 안내 문구입니다. 이 문구는 answer나 example에 반복하지 않습니다."
        ),
    )
    warnings: list[WarningMessage] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_safety_notice_is_separate(self) -> Self:
        _ensure_safety_notice_is_separate(
            field_name="answer",
            value=self.answer,
            safety_notice=self.safety_notice,
        )
        _ensure_safety_notice_is_separate(
            field_name="example",
            value=self.example,
            safety_notice=self.safety_notice,
        )
        return self


class StructuredLLMClient(Protocol):
    async def complete_structured(
        self,
        messages: Sequence[ChatMessage],
        *,
        response_model: type[TermExplanationLLMResponse],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> TermExplanationLLMResponse: ...


async def explain_term(
    state: AgentState | Mapping[str, Any],
    *,
    llm_client: StructuredLLMClient | None = None,
) -> dict[str, Any]:
    if _should_skip(state):
        return {}

    user_message = _read_user_message(state)
    sector = _read_sector(state)
    chat_history = _read_chat_history(state)
    if llm_client is not None:
        explanation = await _request_term_explanation(
            llm_client=llm_client,
            user_message=user_message,
            sector=sector,
            chat_history=chat_history,
        )
    else:
        client = UpstageLLMClient()
        try:
            explanation = await _request_term_explanation(
                llm_client=client,
                user_message=user_message,
                sector=sector,
                chat_history=chat_history,
            )
        finally:
            await client.aclose()

    return _build_state_update(
        explanation=explanation,
        state=state,
    )


async def _request_term_explanation(
    *,
    llm_client: StructuredLLMClient,
    user_message: str,
    sector: SectorCode | None,
    chat_history: list[ChatTurn],
) -> TermExplanationLLMResponse:
    return await llm_client.complete_structured(
        _build_term_explanation_messages(
            user_message=user_message,
            sector=sector,
            chat_history=chat_history,
        ),
        response_model=TermExplanationLLMResponse,
        temperature=0.2,
        max_tokens=900,
    )


def _build_term_explanation_messages(
    *,
    user_message: str,
    sector: SectorCode | None,
    chat_history: list[ChatTurn],
) -> list[ChatMessage]:
    return load_prompt_messages(
        "term_explanation",
        user_message=user_message,
        sector=_format_sector_label(sector),
        chat_history=format_history_text(
            chat_history,
            empty_placeholder=EMPTY_HISTORY_PLACEHOLDER,
        ),
    )


def _build_state_update(
    *,
    explanation: TermExplanationLLMResponse,
    state: AgentState | Mapping[str, Any],
) -> dict[str, Any]:
    request_type = _normalize_request_type(explanation.request_type)
    warnings = [
        *_read_existing_warnings(state),
        *explanation.warnings,
    ]
    safety_notice = explanation.safety_notice

    if request_type is RequestType.OUT_OF_SCOPE:
        warnings.append(OUT_OF_SCOPE_WARNING)
        return {
            "request_type": RequestType.OUT_OF_SCOPE,
            "final_answer": explanation.answer,
            "safety_notice": safety_notice,
            "warnings": warnings,
        }

    safety_notice = safety_notice or TERM_EXPLANATION_SAFETY_NOTICE
    return {
        "request_type": RequestType.TERM_EXPLANATION,
        "final_answer": _format_term_answer(
            term=explanation.term,
            answer=explanation.answer,
            example=explanation.example,
        ),
        "safety_notice": safety_notice,
        "warnings": warnings,
    }


def _format_term_answer(
    *,
    term: str | None,
    answer: str,
    example: str | None,
) -> str:
    sections: list[str] = []
    if term:
        sections.append(f"용어\n{term}")
    sections.append(f"쉬운 설명\n{answer}")
    if example:
        sections.append(f"예시\n{example}")
    return "\n\n".join(sections)


def _normalize_request_type(request_type: RequestType) -> RequestType:
    if request_type is RequestType.TERM_EXPLANATION:
        return RequestType.TERM_EXPLANATION
    return RequestType.OUT_OF_SCOPE


def _ensure_safety_notice_is_separate(
    *,
    field_name: str,
    value: str | None,
    safety_notice: str | None,
) -> None:
    if not value:
        return

    notice = safety_notice.strip() if safety_notice else ""
    if SAFETY_NOTICE_SECTION_LABEL in value or (notice and notice in value):
        raise ValueError(f"{field_name} must not include safety_notice")


def _should_skip(state: AgentState | Mapping[str, Any]) -> bool:
    if _has_final_answer(state):
        return True
    return _read_request_type(state) != RequestType.TERM_EXPLANATION


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


def _format_sector_label(sector: SectorCode | None) -> str:
    if sector is None:
        return "없음"
    return SECTOR_LABELS.get(sector, sector.value)


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
