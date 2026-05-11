import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.ai.state import AgentState
from app.models.enums import RequestType
from app.schemas.common import WarningMessage

UNSAFE_INVESTMENT_WARNING = WarningMessage(
    code="investment_advice_request_blocked",
    message="매수 또는 매도 요청은 답변하지 않습니다.",
)

_UNSAFE_INVESTMENT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"사도\s*(돼|되|될까|될까요)",
        r"(살까|살까요|사야\s*(해|하나|할까|할까요))",
        r"(팔까|팔까요|팔아야|팔아도)",
        r"(매수|매도)\s*(해|할까|해도|추천|타이밍|시점)",
        r"(추매|추가\s*매수)",
        r"\b(buy|sell)\b",
    )
)


@dataclass(frozen=True)
class SafetyCheckResult:
    request_type: RequestType | None
    final_answer: str | None
    warnings: tuple[WarningMessage, ...]

    @property
    def is_blocked(self) -> bool:
        return self.final_answer is not None


def safety_check(state: AgentState | Mapping[str, Any]) -> dict[str, Any]:
    result = check_request_safety(_read_user_message(state))
    warnings = (*_read_existing_warnings(state), *result.warnings)

    update: dict[str, Any] = {"warnings": list(warnings)}
    if result.request_type is not None:
        update["request_type"] = result.request_type
    if result.final_answer is not None:
        update["final_answer"] = result.final_answer
    return update


def check_request_safety(user_message: str) -> SafetyCheckResult:
    normalized_message = _normalize_message(user_message)
    if _is_unsafe_investment_advice_request(normalized_message):
        return SafetyCheckResult(
            request_type=RequestType.OUT_OF_SCOPE,
            final_answer=(
                "매수 또는 매도처럼 직접적인 투자 판단은 제공할 수 없습니다. "
                "대신 해당 섹터나 기업의 지표와 뉴스가 어떤 의미인지 "
                "교육 목적의 설명으로 도와드릴 수 있습니다."
            ),
            warnings=(UNSAFE_INVESTMENT_WARNING,),
        )

    return SafetyCheckResult(
        request_type=None,
        final_answer=None,
        warnings=(),
    )


def _is_unsafe_investment_advice_request(message: str) -> bool:
    return any(pattern.search(message) for pattern in _UNSAFE_INVESTMENT_PATTERNS)


def _normalize_message(message: str) -> str:
    return " ".join(message.casefold().split())


def _read_user_message(state: AgentState | Mapping[str, Any]) -> str:
    if isinstance(state, AgentState):
        return state.user_message

    value = state.get("user_message", "")
    return value if isinstance(value, str) else ""


def _read_existing_warnings(
    state: AgentState | Mapping[str, Any],
) -> Sequence[WarningMessage]:
    if isinstance(state, AgentState):
        return tuple(state.warnings)

    warnings = state.get("warnings", ())
    if not isinstance(warnings, Sequence) or isinstance(warnings, str):
        return ()
    return tuple(_parse_warning(warning) for warning in warnings)


def _parse_warning(value: Any) -> WarningMessage:
    if isinstance(value, WarningMessage):
        return value
    if isinstance(value, Mapping):
        return WarningMessage.model_validate(value)
    return WarningMessage(
        code="unknown_warning",
        message=str(value),
    )
