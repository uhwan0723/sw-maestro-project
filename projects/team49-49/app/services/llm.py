from typing import Any, Protocol

import httpx

UPSTAGE_BASE_URL = "https://api.upstage.ai/v1"
UPSTAGE_MODEL = "solar-pro2"
CLAUDE_BASE_URL = "https://api.anthropic.com/v1"
CLAUDE_MODEL = "claude-sonnet-4-20250514"
CODEX_BASE_URL = "https://api.openai.com/v1"
CODEX_MODEL = "gpt-5.1-codex-mini"


class LLMClient(Protocol):
    def complete(self, system_prompt: str, user_prompt: str) -> str | None:
        """Return generated text, or None when no remote provider is configured."""


class NoOpLLMClient:
    def complete(self, system_prompt: str, user_prompt: str) -> str | None:
        return None


class OpenAICompatibleChatClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        http_client: Any | None = None,
        timeout: float = 30.0,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.http_client = http_client or httpx.Client()
        self.timeout = timeout

    def complete(self, system_prompt: str, user_prompt: str) -> str | None:
        response = self.http_client.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 900,
                "stream": False,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


class AnthropicClaudeClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.anthropic.com/v1",
        http_client: Any | None = None,
        timeout: float = 30.0,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.http_client = http_client or httpx.Client()
        self.timeout = timeout

    def complete(self, system_prompt: str, user_prompt: str) -> str | None:
        response = self.http_client.post(
            f"{self.base_url}/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": 900,
                "temperature": 0.2,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        for block in data.get("content", []):
            if block.get("type") == "text" and block.get("text"):
                return block["text"].strip()
        return None


def build_llm_client(settings: Any, http_client: Any | None = None) -> LLMClient:
    provider = _resolve_provider(settings)
    if provider == "none":
        return NoOpLLMClient()
    if provider == "upstage":
        api_key = getattr(settings, "upstage_api_key", "")
        if not api_key:
            return NoOpLLMClient()
        return OpenAICompatibleChatClient(
            api_key=api_key,
            base_url=UPSTAGE_BASE_URL,
            model=UPSTAGE_MODEL,
            http_client=http_client,
        )
    if provider == "claude":
        api_key = getattr(settings, "claude_api_key", "")
        if not api_key:
            return NoOpLLMClient()
        return AnthropicClaudeClient(
            api_key=api_key,
            model=CLAUDE_MODEL,
            base_url=CLAUDE_BASE_URL,
            http_client=http_client,
        )
    if provider == "codex_oauth":
        api_key = getattr(settings, "codex_oauth_token", "")
        if not api_key:
            return NoOpLLMClient()
        return OpenAICompatibleChatClient(
            api_key=api_key,
            base_url=CODEX_BASE_URL,
            model=CODEX_MODEL,
            http_client=http_client,
        )
    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")


def _resolve_provider(settings: Any) -> str:
    provider = (getattr(settings, "llm_provider", "") or "auto").lower()
    if provider != "auto":
        return provider
    if getattr(settings, "upstage_api_key", ""):
        return "upstage"
    return "none"
