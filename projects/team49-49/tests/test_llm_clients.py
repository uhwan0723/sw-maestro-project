from types import SimpleNamespace

from app.core.config import Settings
from app.services.llm import (
    AnthropicClaudeClient,
    CLAUDE_MODEL,
    CODEX_MODEL,
    NoOpLLMClient,
    OpenAICompatibleChatClient,
    UPSTAGE_BASE_URL,
    UPSTAGE_MODEL,
    build_llm_client,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeHTTPClient:
    def __init__(self, payload):
        self.payload = payload
        self.requests = []

    def post(self, url, headers, json, timeout):
        self.requests.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse(self.payload)


def test_default_settings_prefer_upstage_provider(monkeypatch):
    monkeypatch.delenv("UPSTAGE_API_KEY", raising=False)
    monkeypatch.delenv("ICH_UPSTAGE_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ICH_CLAUDE_API_KEY", raising=False)
    monkeypatch.delenv("ICH_CODEX_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("LANGGRAPH_DEPLOYMENT_URL", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGGRAPH_QA_ASSISTANT_ID", raising=False)
    settings = Settings(_env_file=None)

    assert settings.llm_provider == "auto"
    assert settings.upstage_api_key == ""
    assert settings.claude_api_key == ""
    assert settings.codex_oauth_token == ""
    assert settings.langgraph_deployment_url == ""
    assert settings.langsmith_api_key == ""
    assert settings.langgraph_qa_assistant_id == ""


def test_langgraph_settings_support_public_and_internal_aliases(monkeypatch):
    monkeypatch.setenv("LANGGRAPH_DEPLOYMENT_URL", "https://langgraph.example")
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2_public")
    monkeypatch.setenv("LANGGRAPH_QA_ASSISTANT_ID", "qa_assistant")
    monkeypatch.setenv("ICH_LANGGRAPH_REVIEW_ASSISTANT_ID", "review_assistant")

    settings = Settings(_env_file=None)

    assert settings.langgraph_deployment_url == "https://langgraph.example"
    assert settings.langsmith_api_key == "lsv2_public"
    assert settings.langgraph_qa_assistant_id == "qa_assistant"
    assert settings.langgraph_review_assistant_id == "review_assistant"


def test_upstage_client_uses_openai_compatible_chat_completion_shape():
    http_client = FakeHTTPClient({"choices": [{"message": {"content": "근거 기반 답변"}}]})
    client = OpenAICompatibleChatClient(
        api_key="upstage-key",
        base_url=UPSTAGE_BASE_URL,
        model=UPSTAGE_MODEL,
        http_client=http_client,
    )

    answer = client.complete(system_prompt="system", user_prompt="question")

    request = http_client.requests[0]
    assert answer == "근거 기반 답변"
    assert request["url"] == "https://api.upstage.ai/v1/chat/completions"
    assert request["headers"]["Authorization"] == "Bearer upstage-key"
    assert request["json"]["model"] == UPSTAGE_MODEL
    assert request["json"]["messages"] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "question"},
    ]


def test_claude_client_uses_anthropic_messages_api_shape():
    http_client = FakeHTTPClient({"content": [{"type": "text", "text": "Claude 답변"}]})
    client = AnthropicClaudeClient(
        api_key="claude-key",
        model=CLAUDE_MODEL,
        http_client=http_client,
    )

    answer = client.complete(system_prompt="system", user_prompt="question")

    request = http_client.requests[0]
    assert answer == "Claude 답변"
    assert request["url"] == "https://api.anthropic.com/v1/messages"
    assert request["headers"]["x-api-key"] == "claude-key"
    assert request["headers"]["anthropic-version"] == "2023-06-01"
    assert request["json"]["system"] == "system"
    assert request["json"]["messages"] == [{"role": "user", "content": "question"}]


def test_codex_oauth_provider_uses_bearer_token_with_openai_compatible_endpoint():
    http_client = FakeHTTPClient({"choices": [{"message": {"content": "Codex OAuth 답변"}}]})
    settings = SimpleNamespace(
        llm_provider="codex_oauth",
        codex_oauth_token="codex-token",
    )

    client = build_llm_client(settings, http_client=http_client)
    answer = client.complete(system_prompt="system", user_prompt="question")

    request = http_client.requests[0]
    assert answer == "Codex OAuth 답변"
    assert request["url"] == "https://api.openai.com/v1/chat/completions"
    assert request["headers"]["Authorization"] == "Bearer codex-token"
    assert request["json"]["model"] == CODEX_MODEL


def test_auto_provider_uses_upstage_when_key_exists():
    upstage_http = FakeHTTPClient({"choices": [{"message": {"content": "upstage"}}]})
    upstage_client = build_llm_client(
        SimpleNamespace(
            llm_provider="auto",
            upstage_api_key="upstage-key",
            claude_api_key="claude-key",
            codex_oauth_token="codex-token",
        ),
        http_client=upstage_http,
    )
    assert upstage_client.complete("system", "question") == "upstage"
    assert upstage_http.requests[0]["headers"]["Authorization"] == "Bearer upstage-key"


def test_auto_provider_returns_noop_without_upstage_even_when_other_keys_exist():
    client = build_llm_client(
        SimpleNamespace(
            llm_provider="auto",
            upstage_api_key="",
            claude_api_key="claude-key",
            codex_oauth_token="codex-token",
        )
    )

    assert isinstance(client, NoOpLLMClient)


def test_explicit_claude_provider_uses_claude_key():
    claude_http = FakeHTTPClient({"content": [{"type": "text", "text": "claude"}]})
    claude_client = build_llm_client(
        SimpleNamespace(
            llm_provider="claude",
            upstage_api_key="",
            claude_api_key="claude-key",
            codex_oauth_token="codex-token",
        ),
        http_client=claude_http,
    )
    assert claude_client.complete("system", "question") == "claude"
    assert claude_http.requests[0]["headers"]["x-api-key"] == "claude-key"


def test_missing_provider_key_uses_noop_client():
    settings = SimpleNamespace(
        llm_provider="auto",
        upstage_api_key="",
        claude_api_key="",
        codex_oauth_token="",
    )

    client = build_llm_client(settings)

    assert isinstance(client, NoOpLLMClient)
    assert client.complete("system", "question") is None
