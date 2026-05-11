from app.ai.compose_report import compose_report
from app.ai.graph import (
    _route_after_request,
    _route_after_safety_check,
)
from app.ai.prompts.loader import PromptTemplateError, load_prompt_messages
from app.ai.safety_check import check_request_safety, safety_check
from app.models.enums import RequestType, SectorCode


def test_check_request_safety_blocks_direct_buy_request() -> None:
    result = check_request_safety("삼성전자 지금 살까?")

    assert result.request_type is RequestType.OUT_OF_SCOPE
    assert result.final_answer is not None
    assert result.warnings[0].code == "investment_advice_request_blocked"
    assert result.is_blocked


def test_safety_check_keeps_safe_request_unblocked() -> None:
    result = check_request_safety("PER이 뭐야?")

    assert result.request_type is None
    assert result.final_answer is None
    assert result.warnings == ()
    assert not result.is_blocked


def test_safety_check_preserves_existing_warnings() -> None:
    update = safety_check(
        {
            "user_message": "하이닉스 매도 타이밍 알려줘",
            "warnings": [
                {
                    "code": "existing_warning",
                    "message": "기존 경고",
                }
            ],
        }
    )

    assert update["request_type"] is RequestType.OUT_OF_SCOPE
    assert [warning.code for warning in update["warnings"]] == [
        "existing_warning",
        "investment_advice_request_blocked",
    ]


def test_graph_routes_known_paths_without_llm_calls() -> None:
    assert _route_after_safety_check({"final_answer": "차단"}) == "end"
    assert (
        _route_after_safety_check({"request_type": RequestType.SECTOR_ANALYSIS})
        == "sector_analysis"
    )
    assert _route_after_safety_check({}) == "route_request"

    assert (
        _route_after_request({"request_type": RequestType.SECTOR_ANALYSIS})
        == "sector_analysis"
    )
    assert (
        _route_after_request({"request_type": RequestType.TERM_EXPLANATION})
        == "term_explanation"
    )
    assert _route_after_request({"request_type": RequestType.OUT_OF_SCOPE}) == "end"


def test_compose_report_selects_supported_hypotheses_and_builds_summary() -> None:
    update = compose_report(
        {
            "request_type": RequestType.SECTOR_ANALYSIS,
            "sector": SectorCode.SEMICONDUCTOR,
            "indicator_context": {
                "sector": "semiconductor",
                "reference_date": "2026-05-08",
                "comparison": {"average_change_percent": 0.7},
            },
            "hypotheses": [
                {
                    "title": "수출 개선",
                    "description": "반도체 수출 개선 기대가 확인됩니다.",
                    "basis": ["오늘 평균 등락률이 양수입니다.", "뉴스가 수출 개선을 언급합니다."],
                    "sources": [
                        {
                            "title": "시장 지표",
                            "url": "market://semiconductor/2026-05-08",
                            "provider": "yfinance",
                        }
                    ],
                },
                {
                    "title": "검증 안 된 이슈",
                    "description": "근거가 부족한 가설입니다.",
                    "basis": ["확인되지 않은 주장입니다."],
                    "sources": [],
                },
            ],
            "verification_results": [
                {
                    "hypothesis_title": "수출 개선",
                    "is_supported": True,
                    "reason": "지표와 뉴스가 함께 뒷받침합니다.",
                    "confidence": 0.82,
                    "warnings": [],
                },
                {
                    "hypothesis_title": "검증 안 된 이슈",
                    "is_supported": False,
                    "reason": "근거가 부족합니다.",
                    "confidence": 0.1,
                    "warnings": [],
                },
            ],
            "confidence": 0.82,
            "warnings": [],
        }
    )

    assert update["trend_label"] == "상승 우세"
    assert update["confidence"] == 0.82
    assert update["beginner_summary"].startswith("현재 KOSPI 반도체 섹터는")
    assert [evidence.title for evidence in update["key_evidence"]] == ["수출 개선"]
    assert [source.url for source in update["sources"]] == [
        "market://semiconductor/2026-05-08"
    ]
    assert "매수/매도/보유 판단이나 수익률 예측이 아닙니다" in update["caution"]


def test_compose_report_returns_hold_summary_when_hypotheses_are_missing() -> None:
    update = compose_report(
        {
            "request_type": "sector_analysis",
            "sector": "pharmaceutical",
            "warnings": [],
        }
    )

    assert update["trend_label"] == "분석 보류"
    assert update["confidence"] == 0.0
    assert update["key_evidence"] == []
    assert update["warnings"][0].code == "report_hypotheses_missing"
    assert "현재 리포트에 사용할 핵심 근거가 부족합니다" in update["final_answer"]


def test_prompt_loader_renders_template_values() -> None:
    messages = load_prompt_messages(
        "request_routing",
        user_message="PER이 뭐야?",
        chat_history="이전 대화 없음",
    )

    assert [message.role for message in messages] == ["system", "user"]
    assert "PER이 뭐야?" in messages[1].content
    assert "이전 대화 없음" in messages[1].content


def test_prompt_loader_reports_missing_template_value() -> None:
    try:
        load_prompt_messages("request_routing", user_message="PER이 뭐야?")
    except PromptTemplateError as exc:
        assert "chat_history" in str(exc)
    else:
        raise AssertionError("PromptTemplateError was not raised")
