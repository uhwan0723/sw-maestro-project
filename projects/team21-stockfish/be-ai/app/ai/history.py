from app.core.llm import ChatMessage
from app.schemas.chat import ChatTurn


EMPTY_HISTORY_PLACEHOLDER = "(이전 대화 없음)"

_ROLE_LABELS: dict[str, str] = {
    "user": "사용자",
    "assistant": "어시스턴트",
}


def to_chat_messages(history: list[ChatTurn]) -> list[ChatMessage]:
    return [ChatMessage(role=turn.role, content=turn.content) for turn in history]


def format_history_text(
    history: list[ChatTurn],
    *,
    empty_placeholder: str = "",
) -> str:
    if not history:
        return empty_placeholder
    return "\n".join(
        f"{_ROLE_LABELS[turn.role]}: {turn.content}" for turn in history
    )
