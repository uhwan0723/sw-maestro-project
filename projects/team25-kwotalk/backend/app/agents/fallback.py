"""폴백 노드 — 분류 실패·검색 0건·법률 무관·LLM 장애."""
from app.constants import DISCLAIMER
from app.state import LegalState


_MESSAGES = {
    "no_domain": "교통 관련 사건만 상담 가능합니다. 사건 유형을 구체적으로 알려주세요.",
    "no_docs": "관련 법령·판례를 충분히 찾지 못했습니다. 일반 안내만 제공합니다.",
    "llm_error": "응답 생성 중 일시적 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    "unknown": "처리할 수 없는 요청입니다.",
}


async def fallback_node(state: LegalState) -> dict:
    reason = state.get("fallback_reason") or "unknown"
    msg = _MESSAGES.get(reason, _MESSAGES["unknown"])
    return {
        "answer_text": msg + "\n\n" + DISCLAIMER,
        "citations": [],
        "confidence_score": 0.0,
        "recommend_lawyer": True,
    }
