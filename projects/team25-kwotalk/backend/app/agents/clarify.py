"""clarify_node — 분류 신뢰도 낮을 때 명확화 질문 반환 (MVP: 정적 메시지)."""
from app.constants import DISCLAIMER
from app.state import LegalState


async def clarify_node(state: LegalState) -> dict:
    msg = (
        "어떤 교통 사건인지 좀 더 구체적으로 알려주실 수 있나요? "
        "(예: 뺑소니, 음주운전, 보행자 사고 등)"
    )
    return {
        "clarification_question": msg,
        "answer_text": msg + "\n\n" + DISCLAIMER,
        "citations": [],
    }
