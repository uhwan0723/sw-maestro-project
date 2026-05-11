import asyncio

import httpx
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.api import analysis as analysis_module
from app.api import chat as chat_module
from app.core.llm import (
    ChatMessage,
    LLMAPIError,
    LLMConfigurationError,
    LLMResponseFormatError,
    UpstageLLMClient,
)
from app.main import app
from app.models.enums import RequestType, SectorCode
from app.schemas.analysis import SectorAnalysisResponse
from app.schemas.chat import ChatResponse
from app.schemas.common import WarningMessage


class FakeStructuredResponse(BaseModel):
    answer: str
    score: float


class FakeHTTPClient:
    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.requests: list[dict[str, object]] = []
        self.closed = False

    async def post(self, url: str, **kwargs):
        self.requests.append({"url": url, **kwargs})
        return self.response

    async def aclose(self) -> None:
        self.closed = True


def test_health_endpoint_returns_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_endpoint_delegates_to_chat_service(monkeypatch) -> None:
    seen_message: str | None = None

    class FakeChatService:
        async def respond(self, request):
            nonlocal seen_message
            seen_message = request.message
            return ChatResponse(
                request_type=RequestType.TERM_EXPLANATION,
                answer="PER 설명",
                safety_notice="교육용 정보입니다.",
                warnings=[WarningMessage(code="notice", message="안내")],
                session_id="session-1",
            )

    monkeypatch.setattr(chat_module, "ChatService", FakeChatService)

    with TestClient(app) as client:
        response = client.post("/api/v1/chat", json={"message": "PER이 뭐야?"})

    assert response.status_code == 200
    assert seen_message == "PER이 뭐야?"
    assert response.json() == {
        "request_type": "term_explanation",
        "answer": "PER 설명",
        "safety_notice": "교육용 정보입니다.",
        "warnings": [{"code": "notice", "message": "안내"}],
        "session_id": "session-1",
    }


def test_sector_analysis_endpoint_delegates_to_analysis_service(monkeypatch) -> None:
    seen_args: tuple[SectorCode, bool] | None = None

    class FakeAnalysisService:
        def __init__(self, _session) -> None:
            pass

        async def get_today_sector_analysis(
            self,
            sector: SectorCode,
            *,
            refresh: bool = False,
        ) -> SectorAnalysisResponse:
            nonlocal seen_args
            seen_args = (sector, refresh)
            return SectorAnalysisResponse(
                sector=sector,
                beginner_summary="반도체 요약",
                key_evidence=[],
                sources=[],
                confidence=0.7,
                caution="교육용 분석입니다.",
                warnings=[],
            )

    monkeypatch.setattr(analysis_module, "AnalysisService", FakeAnalysisService)

    with TestClient(app) as client:
        response = client.get("/api/v1/sectors/semiconductor/analysis?refresh=true")

    assert response.status_code == 200
    assert seen_args == (SectorCode.SEMICONDUCTOR, True)
    assert response.json()["sector"] == "semiconductor"
    assert response.json()["beginner_summary"] == "반도체 요약"
    assert response.json()["confidence"] == 0.7


def test_upstage_client_complete_structured_parses_model_response() -> None:
    response = httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {"content": '{"answer":"ok","score":0.9}'},
                    "finish_reason": "stop",
                }
            ],
            "model": "solar-pro3",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        },
        request=httpx.Request("POST", "https://api.upstage.ai/v1/chat/completions"),
    )
    http_client = FakeHTTPClient(response)
    client = UpstageLLMClient(api_key="test-key", http_client=http_client)

    result = asyncio.run(
        client.complete_structured(
            [ChatMessage(role="user", content="응답해줘")],
            response_model=FakeStructuredResponse,
            temperature=0.0,
            max_tokens=100,
        )
    )

    assert result == FakeStructuredResponse(answer="ok", score=0.9)
    request_payload = http_client.requests[0]["json"]
    assert request_payload["model"] == "solar-pro3"
    assert request_payload["response_format"] == {"type": "json_object"}
    assert request_payload["temperature"] == 0.0
    assert request_payload["max_tokens"] == 100
    assert "JSON Schema" in request_payload["messages"][0]["content"]


def test_upstage_client_requires_api_key() -> None:
    client = UpstageLLMClient(api_key="test-key", http_client=FakeHTTPClient(httpx.Response(200)))
    client._api_key = ""

    try:
        asyncio.run(
            client.complete([ChatMessage(role="user", content="안녕")])
        )
    except LLMConfigurationError as exc:
        assert "UPSTAGE_API_KEY" in str(exc)
    else:
        raise AssertionError("LLMConfigurationError was not raised")


def test_upstage_client_wraps_http_status_errors() -> None:
    response = httpx.Response(
        429,
        json={"error": {"message": "rate limited"}},
        request=httpx.Request("POST", "https://api.upstage.ai/v1/chat/completions"),
    )
    client = UpstageLLMClient(
        api_key="test-key",
        http_client=FakeHTTPClient(response),
    )

    try:
        asyncio.run(
            client.complete([ChatMessage(role="user", content="안녕")])
        )
    except LLMAPIError as exc:
        assert "HTTP 429" in str(exc)
        assert "rate limited" in str(exc)
    else:
        raise AssertionError("LLMAPIError was not raised")


def test_upstage_client_rejects_invalid_structured_json() -> None:
    response = httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {"content": "not-json"},
                    "finish_reason": "stop",
                }
            ]
        },
        request=httpx.Request("POST", "https://api.upstage.ai/v1/chat/completions"),
    )
    client = UpstageLLMClient(
        api_key="test-key",
        http_client=FakeHTTPClient(response),
    )

    try:
        asyncio.run(
            client.complete_structured(
                [ChatMessage(role="user", content="응답해줘")],
                response_model=FakeStructuredResponse,
            )
        )
    except LLMResponseFormatError as exc:
        assert "not valid JSON" in str(exc)
    else:
        raise AssertionError("LLMResponseFormatError was not raised")
