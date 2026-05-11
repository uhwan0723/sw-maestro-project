"""classify_node 평가셋 테스트 — 12개 시나리오, 정확도 80% 이상."""
import json
import os
from unittest.mock import patch

import pytest

from app.agents.classify import classify_node
from app.constants import CLARIFY_THRESHOLD
from app.utils.keyword_fallback import ClassificationOutput

SCENARIOS_PATH = os.path.join(os.path.dirname(__file__), "scenarios.json")


def _load_scenarios():
    with open(SCENARIOS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _make_state(query: str) -> dict:
    return {
        "session_id": "test",
        "user_query": query,
        "history": [],
        "retrieved_docs": [],
    }


def _mock_flash(case_type: str, needs_settlement: bool, confidence: float):
    async def _call(*args, **kwargs):
        return ClassificationOutput(
            case_type=case_type,
            needs_settlement=needs_settlement,
            confidence=confidence,
        )

    return _call


@pytest.mark.asyncio
async def test_classify_accuracy():
    """평가셋 12개 중 case_type 정확도 80% 이상."""
    scenarios = _load_scenarios()
    correct = 0

    for sc in scenarios:
        expected_ct = sc["expected"]["case_type"]
        expected_ns = sc["expected"]["needs_settlement"]
        expected_conf = sc["expected"]["confidence"]

        mock_fn = _mock_flash(expected_ct, expected_ns, expected_conf)
        with patch("app.agents.classify.call_flash_json", side_effect=mock_fn):
            result = await classify_node(_make_state(sc["input"]))

        if result["case_type"] == expected_ct:
            correct += 1

    accuracy = correct / len(scenarios)
    assert accuracy >= 0.80, f"정확도 {accuracy:.1%} < 80% (정답 {correct}/{len(scenarios)})"


@pytest.mark.asyncio
async def test_classify_oos_high_confidence():
    """OUT_OF_SCOPE 케이스는 confidence >= 0.9 이어야 함."""
    mock_fn = _mock_flash("OUT_OF_SCOPE", False, 0.99)
    with patch("app.agents.classify.call_flash_json", side_effect=mock_fn):
        result = await classify_node(_make_state("오늘 점심 뭐 먹지?"))

    assert result["case_type"] == "OUT_OF_SCOPE"
    assert result["classification_confidence"] >= 0.9


@pytest.mark.asyncio
async def test_classify_low_confidence_triggers_clarify():
    """모호한 질문에 대해 confidence < 0.4 가 나와야 함."""
    mock_fn = _mock_flash("RECKLESS_DRIVING", False, 0.3)
    with patch("app.agents.classify.call_flash_json", side_effect=mock_fn):
        result = await classify_node(_make_state("차 사고 났어요"))

    assert result["classification_confidence"] < CLARIFY_THRESHOLD


@pytest.mark.asyncio
async def test_classify_reckless_needs_settlement_forced_false():
    """RECKLESS_DRIVING은 needs_settlement가 강제로 false."""
    mock_fn = _mock_flash("RECKLESS_DRIVING", True, 0.9)
    with patch("app.agents.classify.call_flash_json", side_effect=mock_fn):
        result = await classify_node(_make_state("앞차에 위협운전을 했어요"))

    assert result["needs_settlement"] is False


@pytest.mark.asyncio
async def test_classify_fallback_on_api_error():
    """SolarAPIError 발생 시 키워드 폴백이 동작해야 함."""
    from app.llm.solar_client import SolarAPIError

    async def _raise(*args, **kwargs):
        raise SolarAPIError("테스트 오류")

    with patch("app.agents.classify.call_flash_json", side_effect=_raise):
        result = await classify_node(_make_state("음주운전 단속됐어요"))

    assert result["case_type"] == "DRUNK_DRIVING"
    assert result["classification_confidence"] == 0.3
