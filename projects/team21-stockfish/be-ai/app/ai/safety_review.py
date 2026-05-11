from collections.abc import Mapping, Sequence
import json
from typing import Any, Protocol, Self

from pydantic import BaseModel, Field, model_validator

from app.ai.prompts.loader import load_prompt_messages
from app.ai.state import AgentState
from app.core.llm import ChatMessage, UpstageLLMClient
from app.models.enums import RequestType
from app.schemas.common import SourceInfo, WarningMessage


DEFAULT_SAFETY_NOTICE = (
    "이 답변은 교육용 정보이며, 매수/매도/보유 판단이나 매매 시점 추천이 아닙니다."
)
ANSWER_REWRITTEN_WARNING = WarningMessage(
    code="answer_safety_rewritten",
    message="안전하지 않은 투자 조언으로 오해될 수 있는 표현을 보수적으로 수정했습니다.",
)
SAFETY_NOTICE_SECTION_LABEL = "안전 안내"


class SafetyReviewLLMResponse(BaseModel):
    answer: str = Field(
        description=(
            "사용자에게 보여줄 답변 본문만 작성합니다. safety_notice 내용이나 "
            "'안전 안내' 섹션은 포함하지 않습니다."
        )
    )
    safety_notice: str | None = Field(
        default=None,
        description=(
            "투자 조언이 아니라는 안내 문구입니다. 이 문구는 answer에 반복하지 "
            "않습니다."
        ),
    )
    warnings: list[WarningMessage] = Field(default_factory=list)
    is_safe: bool

    @model_validator(mode="after")
    def validate_safety_notice_is_separate(self) -> Self:
        _ensure_safety_notice_is_separate(
            field_name="answer",
            value=self.answer,
            safety_notice=self.safety_notice,
        )
        return self


class StructuredLLMClient(Protocol):
    async def complete_structured(
        self,
        messages: Sequence[ChatMessage],
        *,
        response_model: type[SafetyReviewLLMResponse],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> SafetyReviewLLMResponse: ...


async def safety_review(
    state: AgentState | Mapping[str, Any],
    *,
    llm_client: StructuredLLMClient | None = None,
) -> dict[str, Any]:
    if _should_skip(state):
        return {}

    draft_answer = _read_final_answer(state)
    request_type = _read_request_type(state)
    user_message = _read_user_message(state)
    sources = _read_sources(state)
    warnings = _read_existing_warnings(state)

    if llm_client is not None:
        review = await _request_safety_review(
            llm_client=llm_client,
            user_message=user_message,
            request_type=request_type,
            draft_answer=draft_answer,
            sources=sources,
            warnings=warnings,
        )
    else:
        client = UpstageLLMClient()
        try:
            review = await _request_safety_review(
                llm_client=client,
                user_message=user_message,
                request_type=request_type,
                draft_answer=draft_answer,
                sources=sources,
                warnings=warnings,
            )
        finally:
            await client.aclose()

    return _build_state_update(
        review=review,
        state=state,
    )


async def _request_safety_review(
    *,
    llm_client: StructuredLLMClient,
    user_message: str,
    request_type: RequestType | None,
    draft_answer: str,
    sources: Sequence[SourceInfo],
    warnings: Sequence[WarningMessage],
) -> SafetyReviewLLMResponse:
    return await llm_client.complete_structured(
        _build_safety_review_messages(
            user_message=user_message,
            request_type=request_type,
            draft_answer=draft_answer,
            sources=sources,
            warnings=warnings,
        ),
        response_model=SafetyReviewLLMResponse,
        temperature=0.0,
        max_tokens=1200,
    )


def _build_safety_review_messages(
    *,
    user_message: str,
    request_type: RequestType | None,
    draft_answer: str,
    sources: Sequence[SourceInfo],
    warnings: Sequence[WarningMessage],
) -> list[ChatMessage]:
    return load_prompt_messages(
        "safety_review",
        user_message=user_message,
        request_type=request_type.value if request_type else "unknown",
        draft_answer=draft_answer,
        sources=_serialize_sources(sources),
        warnings=_serialize_warnings(warnings),
    )


def _build_state_update(
    *,
    review: SafetyReviewLLMResponse,
    state: AgentState | Mapping[str, Any],
) -> dict[str, Any]:
    warnings = [
        *_read_existing_warnings(state),
        *review.warnings,
    ]
    if not review.is_safe:
        warnings.append(ANSWER_REWRITTEN_WARNING)

    safety_notice = _resolve_safety_notice(
        review_safety_notice=review.safety_notice,
        state=state,
    )

    return {
        "final_answer": review.answer,
        "safety_notice": safety_notice,
        "draft_answer_is_safe": review.is_safe,
        "warnings": _deduplicate_warnings(warnings),
    }


def _resolve_safety_notice(
    *,
    review_safety_notice: str | None,
    state: AgentState | Mapping[str, Any],
) -> str:
    return (
        review_safety_notice
        or _read_safety_notice(state)
        or _read_caution(state)
        or DEFAULT_SAFETY_NOTICE
    )


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


def _deduplicate_warnings(
    warnings: Sequence[WarningMessage],
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


def _should_skip(state: AgentState | Mapping[str, Any]) -> bool:
    if _read_request_type(state) is RequestType.OUT_OF_SCOPE:
        return True
    return not _read_final_answer(state)


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


def _read_final_answer(state: AgentState | Mapping[str, Any]) -> str:
    if isinstance(state, AgentState):
        return state.final_answer or ""

    value = state.get("final_answer", "")
    return value if isinstance(value, str) else ""


def _read_safety_notice(state: AgentState | Mapping[str, Any]) -> str | None:
    if isinstance(state, AgentState):
        return state.safety_notice

    value = state.get("safety_notice")
    return value if isinstance(value, str) and value else None


def _read_caution(state: AgentState | Mapping[str, Any]) -> str | None:
    if isinstance(state, AgentState):
        return state.caution

    value = state.get("caution")
    return value if isinstance(value, str) and value else None


def _read_sources(
    state: AgentState | Mapping[str, Any],
) -> tuple[SourceInfo, ...]:
    if isinstance(state, AgentState):
        return tuple(state.sources)

    value = state.get("sources", ())
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ()
    return tuple(_parse_source(source) for source in value)


def _parse_source(value: Any) -> SourceInfo:
    if isinstance(value, SourceInfo):
        return value
    if isinstance(value, Mapping):
        return SourceInfo.model_validate(value)
    raise ValueError("sources items must be SourceInfo-compatible")


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


def _serialize_sources(sources: Sequence[SourceInfo]) -> str:
    return json.dumps(
        [source.model_dump(mode="json") for source in sources],
        ensure_ascii=False,
    )


def _serialize_warnings(warnings: Sequence[WarningMessage]) -> str:
    return json.dumps(
        [warning.model_dump(mode="json") for warning in warnings],
        ensure_ascii=False,
    )
