import asyncio

import pytest
from pydantic import ValidationError

from app.ai.explain_term import TermExplanationLLMResponse, explain_term
from app.ai.generate_hypotheses import (
    HypothesisGenerationLLMResponse,
    generate_hypotheses,
)
from app.ai.route_request import RouteRequestLLMResponse, route_request
from app.ai.safety_review import SafetyReviewLLMResponse, safety_review
from app.ai.verify_hypotheses import (
    HypothesisVerificationLLMResponse,
    verify_hypotheses,
)
from app.models.enums import RequestType, SectorCode
from app.schemas.common import SourceInfo, WarningMessage


class FakeStructuredLLM:
    def __init__(self, response) -> None:
        self.response = response
        self.calls = []

    async def complete_structured(self, messages, **kwargs):
        self.calls.append({"messages": messages, **kwargs})
        return self.response


class FakeSafetyReviewResult:
    answer = "교육용 설명으로 정리했습니다.\n\n안전 안내\n투자 조언이 아닙니다."
    safety_notice = "투자 조언이 아닙니다."
    warnings = []
    is_safe = True


def run(coro):
    return asyncio.run(coro)


def test_route_request_maps_llm_sector_analysis_result_to_state_update() -> None:
    llm = FakeStructuredLLM(
        RouteRequestLLMResponse(
            request_type=RequestType.SECTOR_ANALYSIS,
            sector=SectorCode.SEMICONDUCTOR,
            reason="반도체 섹터 요청입니다.",
            confidence=0.95,
        )
    )

    update = run(
        route_request(
            {"user_message": "반도체 흐름 알려줘", "chat_history": []},
            llm_client=llm,
        )
    )

    assert update == {
        "request_type": RequestType.SECTOR_ANALYSIS,
        "sector": SectorCode.SEMICONDUCTOR,
    }
    assert llm.calls[0]["response_model"] is RouteRequestLLMResponse


def test_route_request_out_of_scope_adds_default_answer_and_warning() -> None:
    llm = FakeStructuredLLM(
        RouteRequestLLMResponse(
            request_type=RequestType.OUT_OF_SCOPE,
            sector=None,
            reason="지원하지 않는 요청입니다.",
            confidence=0.8,
            final_answer=None,
        )
    )

    update = run(
        route_request(
            {"user_message": "비트코인 전망 알려줘", "warnings": []},
            llm_client=llm,
        )
    )

    assert update["request_type"] is RequestType.OUT_OF_SCOPE
    assert update["sector"] is None
    assert "현재는 KOSPI" in update["final_answer"]
    assert update["warnings"][0].code == "out_of_scope_request"


def test_explain_term_formats_answer_example_without_safety_notice() -> None:
    llm = FakeStructuredLLM(
        TermExplanationLLMResponse(
            request_type=RequestType.TERM_EXPLANATION,
            term="PER",
            answer="주가를 주당순이익으로 나눈 지표입니다.",
            example="주가 10,000원, EPS 1,000원이면 PER은 10입니다.",
            safety_notice="교육용 정보입니다.",
        )
    )

    update = run(
        explain_term(
            {
                "request_type": "term_explanation",
                "user_message": "PER이 뭐야?",
                "chat_history": [],
            },
            llm_client=llm,
        )
    )

    assert update["request_type"] is RequestType.TERM_EXPLANATION
    assert "용어\nPER" in update["final_answer"]
    assert "예시\n주가 10,000원" in update["final_answer"]
    assert "안전 안내" not in update["final_answer"]
    assert "교육용 정보입니다." not in update["final_answer"]
    assert update["safety_notice"] == "교육용 정보입니다."
    assert update["warnings"] == []


def test_term_explanation_response_rejects_answer_with_safety_notice() -> None:
    with pytest.raises(ValidationError):
        TermExplanationLLMResponse(
            request_type=RequestType.TERM_EXPLANATION,
            term="PER",
            answer="주가를 주당순이익으로 나눈 지표입니다.\n\n안전 안내\n교육용 정보입니다.",
            example=None,
            safety_notice="교육용 정보입니다.",
        )


def test_generate_hypotheses_filters_sources_to_loaded_context() -> None:
    allowed_source = SourceInfo(
        title="시장 지표",
        url="market://semiconductor/2026-05-08",
        provider="yfinance",
    )
    rejected_source = SourceInfo(
        title="허용되지 않은 출처",
        url="https://example.com/not-in-context",
        provider="external",
    )
    llm = FakeStructuredLLM(
        HypothesisGenerationLLMResponse(
            hypotheses=[
                {
                    "title": "지표 개선",
                    "description": "대표 종목 평균 등락률이 개선됐습니다.",
                    "basis": ["평균 등락률이 0.7%입니다."],
                    "sources": [allowed_source, rejected_source],
                }
            ],
            warnings=[WarningMessage(code="note", message="참고")],
        )
    )

    update = run(
        generate_hypotheses(
            {
                "request_type": RequestType.SECTOR_ANALYSIS,
                "user_message": "반도체 흐름 알려줘",
                "sector": SectorCode.SEMICONDUCTOR,
                "indicator_context": {
                    "sector": "semiconductor",
                    "reference_date": "2026-05-08",
                    "tickers": [
                        {
                            "ticker": "005930.KS",
                            "price": 70_000,
                            "change_percent": 0.7,
                            "volume": 1000,
                            "sources": ["yfinance"],
                        }
                    ],
                    "comparison": {"average_change_percent": 0.7},
                },
                "news_context": [],
                "chat_history": [],
                "warnings": [],
            },
            llm_client=llm,
        )
    )

    assert len(update["hypotheses"]) == 1
    assert update["hypotheses"][0].title == "지표 개선"
    assert [source.url for source in update["hypotheses"][0].sources] == [
        allowed_source.url
    ]
    assert update["warnings"][0].code == "note"


def test_verify_hypotheses_adds_missing_result_for_unreturned_hypothesis() -> None:
    llm = FakeStructuredLLM(
        HypothesisVerificationLLMResponse(
            verification_results=[
                {
                    "hypothesis_title": "검증된 가설",
                    "is_supported": True,
                    "reason": "컨텍스트로 확인됩니다.",
                    "confidence": 0.8,
                    "warnings": [],
                }
            ],
            confidence=0.9,
        )
    )

    update = run(
        verify_hypotheses(
            {
                "request_type": "sector_analysis",
                "user_message": "분석해줘",
                "hypotheses": [
                    {
                        "title": "검증된 가설",
                        "description": "설명",
                        "basis": [],
                        "sources": [],
                    },
                    {
                        "title": "누락된 가설",
                        "description": "설명",
                        "basis": [],
                        "sources": [],
                    },
                ],
                "warnings": [],
            },
            llm_client=llm,
        )
    )

    assert [result.hypothesis_title for result in update["verification_results"]] == [
        "검증된 가설",
        "누락된 가설",
    ]
    assert update["verification_results"][1].confidence == 0.0
    assert update["verification_results"][1].warnings[0].code == (
        "hypothesis_verification_missing"
    )
    assert update["confidence"] == 0.4


def test_safety_review_keeps_safety_notice_out_of_final_answer() -> None:
    llm = FakeStructuredLLM(
        SafetyReviewLLMResponse(
            answer="교육용 설명으로 정리했습니다.",
            safety_notice="투자 조언이 아닙니다.",
            warnings=[WarningMessage(code="rewritten", message="수정됨")],
            is_safe=False,
        )
    )

    update = run(
        safety_review(
            {
                "request_type": RequestType.SECTOR_ANALYSIS,
                "user_message": "반도체 분석해줘",
                "final_answer": "초안",
                "sources": [],
                "warnings": [],
            },
            llm_client=llm,
        )
    )

    assert update["draft_answer_is_safe"] is False
    assert update["safety_notice"] == "투자 조언이 아닙니다."
    assert update["final_answer"] == "교육용 설명으로 정리했습니다."
    assert [warning.code for warning in update["warnings"]] == [
        "rewritten",
        "answer_safety_rewritten",
    ]


def test_safety_review_response_rejects_answer_with_safety_notice() -> None:
    with pytest.raises(ValidationError):
        SafetyReviewLLMResponse(
            answer="교육용 설명으로 정리했습니다.\n\n안전 안내\n투자 조언이 아닙니다.",
            safety_notice="투자 조언이 아닙니다.",
            warnings=[],
            is_safe=True,
        )


def test_safety_review_does_not_mutate_llm_answer() -> None:
    llm = FakeStructuredLLM(FakeSafetyReviewResult())

    update = run(
        safety_review(
            {
                "request_type": RequestType.SECTOR_ANALYSIS,
                "user_message": "반도체 분석해줘",
                "final_answer": "초안",
                "sources": [],
                "warnings": [],
            },
            llm_client=llm,
        )
    )

    assert update["final_answer"] == FakeSafetyReviewResult.answer
