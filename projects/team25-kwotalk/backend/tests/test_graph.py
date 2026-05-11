"""end-to-end 그래프 시나리오 — Solar API 호출은 mock."""
from unittest.mock import patch

import pytest

from app.constants import DISCLAIMER
from app.graph import graph
from app.utils.keyword_fallback import ClassificationOutput


def _mock_classify(case_type: str, needs_settlement: bool, confidence: float):
    async def _call(*args, **kwargs):
        return ClassificationOutput(
            case_type=case_type,
            needs_settlement=needs_settlement,
            confidence=confidence,
        )

    return _call


def _mock_generate(answer: str):
    async def _stream(*args, **kwargs):
        async def _inner():
            yield answer

        return _inner()

    return _stream


async def _run(inputs: dict, classify_args, generate_answer: str = "관련 법령을 안내합니다. [1] 참조."):
    with patch(
        "app.agents.classify.call_flash_json",
        side_effect=_mock_classify(*classify_args),
    ), patch(
        "app.agents.generate.call_pro_stream",
        side_effect=_mock_generate(generate_answer),
    ):
        return await graph.ainvoke(inputs)


@pytest.mark.asyncio
async def test_dui_golden_path():
    out = await _run(
        {"user_query": "음주운전 단속됐어요", "history": [], "session_id": "t1"},
        ("DRUNK_DRIVING", False, 0.95),
    )
    assert out["case_type"] == "DRUNK_DRIVING"
    assert out["retrieved_docs"]
    assert out["guide_steps"]
    assert out["answer_text"]
    assert DISCLAIMER in out["answer_text"]


@pytest.mark.asyncio
async def test_out_of_scope_routes_to_fallback():
    out = await _run(
        {"user_query": "오늘 점심 뭐 먹지", "history": [], "session_id": "t2"},
        ("OUT_OF_SCOPE", False, 0.99),
    )
    assert out["case_type"] == "OUT_OF_SCOPE"
    assert out["fallback_reason"] == "no_domain"
    assert "교통" in out["answer_text"] or "사건" in out["answer_text"]


@pytest.mark.asyncio
async def test_low_confidence_routes_to_clarify():
    out = await _run(
        {"user_query": "차 사고 났어요", "history": [], "session_id": "t3"},
        ("RECKLESS_DRIVING", False, 0.3),
    )
    assert out.get("clarification_question")
    assert "구체적" in out["answer_text"]


@pytest.mark.asyncio
async def test_pedestrian_settlement_computed():
    out = await _run(
        {"user_query": "보행자 사고 합의금", "history": [], "session_id": "t4"},
        ("PEDESTRIAN_ACCIDENT", True, 0.9),
    )
    assert out["case_type"] == "PEDESTRIAN_ACCIDENT"
    s = out.get("settlement")
    assert s is not None
    assert s["sample_size"] >= 1
    assert s["min"] <= s["median"] <= s["max"]


@pytest.mark.asyncio
async def test_dui_skips_settlement():
    out = await _run(
        {"user_query": "음주운전 처벌", "history": [], "session_id": "t5"},
        ("DRUNK_DRIVING", False, 0.95),
    )
    assert out.get("settlement") is None


@pytest.mark.asyncio
async def test_hit_and_run_has_guide():
    out = await _run(
        {"user_query": "뺑소니 어떻게 해야 하나요", "history": [], "session_id": "t6"},
        ("HIT_AND_RUN", False, 0.95),
    )
    assert out["case_type"] == "HIT_AND_RUN"
    assert out["guide_steps"]
    assert any("자수" in s for s in out["guide_steps"])


@pytest.mark.asyncio
async def test_post_check_recommends_lawyer():
    """인용 1개뿐인 mock 답변 → 변호사 권유 True."""
    out = await _run(
        {"user_query": "음주운전 단속", "history": [], "session_id": "t7"},
        ("DRUNK_DRIVING", False, 0.95),
        generate_answer="간단 답변. [1] 참조.",
    )
    assert out["recommend_lawyer"] is True
    assert "confidence_score" in out
