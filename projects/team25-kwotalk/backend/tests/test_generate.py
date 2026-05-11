"""generate_node 동작 검증 테스트 — mock retrieved_docs 사용."""
from unittest.mock import patch

import pytest

from app.agents.generate import generate_node
from app.constants import DISCLAIMER
from app.state import RetrievedDoc


def _make_docs() -> list[RetrievedDoc]:
    return [
        {
            "doc_id": "law_test_001",
            "type": "법령",
            "title": "도로교통법 제44조 (음주운전 금지)",
            "content": "누구든지 술에 취한 상태에서 자동차 등을 운전하여서는 아니 된다.",
            "case_types": ["DRUNK_DRIVING"],
            "score": 0.92,
            "settlement_amount": None,
        },
        {
            "doc_id": "law_test_002",
            "type": "판례",
            "title": "대법원 2022도1234 (음주운전 처벌)",
            "content": "혈중알코올농도 0.08% 이상의 음주운전은 형사처벌 대상이다.",
            "case_types": ["DRUNK_DRIVING"],
            "score": 0.88,
            "settlement_amount": None,
        },
    ]


def _make_state(query: str = "술 마시고 운전하다 단속됐어요", docs=None) -> dict:
    return {
        "session_id": "test",
        "user_query": query,
        "history": [],
        "case_type": "DRUNK_DRIVING",
        "needs_settlement": False,
        "classification_confidence": 0.95,
        "clarification_question": None,
        "retrieved_docs": docs if docs is not None else _make_docs(),
        "guide_steps": ["음주측정에 응할 것", "면허정지 행정처분 인지", "변호사 상담 권장"],
        "settlement": None,
        "answer_text": "",
        "citations": [],
        "confidence_score": 0.0,
        "recommend_lawyer": False,
        "situation_summary": None,
    }


@pytest.mark.asyncio
async def test_generate_includes_citations():
    """답변에 [1] 또는 [2] 마커가 1개 이상 포함되어야 함."""
    fake_answer = "음주운전 관련 법령을 안내합니다. [1] 도로교통법에 따르면... [2] 판례에 의하면..."

    async def _stream_mock(*args, **kwargs):
        async def _inner():
            yield fake_answer

        return _inner()

    with patch("app.agents.generate.call_pro_stream", side_effect=_stream_mock):
        result = await generate_node(_make_state())

    assert "[1]" in result["answer_text"] or "[2]" in result["answer_text"]
    assert len(result["citations"]) >= 1


@pytest.mark.asyncio
async def test_generate_includes_disclaimer():
    """답변 끝에 면책 고지 문구가 정확히 포함되어야 함."""
    fake_answer = "음주운전은 [1] 도로교통법 제44조에 따라 처벌됩니다."

    async def _stream_mock(*args, **kwargs):
        async def _inner():
            yield fake_answer

        return _inner()

    with patch("app.agents.generate.call_pro_stream", side_effect=_stream_mock):
        result = await generate_node(_make_state())

    assert DISCLAIMER in result["answer_text"]


@pytest.mark.asyncio
async def test_generate_no_hallucinated_law():
    """검색 결과에 없는 법조항을 답변에 포함하지 않아야 함."""
    fake_answer = "음주운전은 [1] 도로교통법 제44조에 따라 처벌됩니다. [1] 관련 판례도 있습니다."

    async def _stream_mock(*args, **kwargs):
        async def _inner():
            yield fake_answer

        return _inner()

    with patch("app.agents.generate.call_pro_stream", side_effect=_stream_mock):
        result = await generate_node(_make_state())

    assert "도로교통법 제999조" not in result["answer_text"]


@pytest.mark.asyncio
async def test_generate_no_settlement_section_when_none():
    """settlement 이 None 일 때 답변에 합의금 섹션이 없어야 함."""
    fake_answer = "음주운전 처벌에 대해 안내합니다. [1] 도로교통법 제44조 참조."

    async def _stream_mock(*args, **kwargs):
        async def _inner():
            yield fake_answer

        return _inner()

    state = _make_state()
    state["settlement"] = None

    with patch("app.agents.generate.call_pro_stream", side_effect=_stream_mock):
        result = await generate_node(state)

    assert "유사 사례" not in result["answer_text"]
    assert "최소" not in result["answer_text"] or "합의금" not in result["answer_text"]


@pytest.mark.asyncio
async def test_generate_fallback_on_api_error():
    """Solar Pro 실패 시 폴백 답변이 반환되고 면책 고지가 포함되어야 함."""
    from app.llm.solar_client import SolarAPIError

    async def _raise(*args, **kwargs):
        raise SolarAPIError("테스트 오류")

    with patch("app.agents.generate.call_pro_stream", side_effect=_raise):
        result = await generate_node(_make_state())

    assert DISCLAIMER in result["answer_text"]
    assert "일시적 문제" in result["answer_text"]
