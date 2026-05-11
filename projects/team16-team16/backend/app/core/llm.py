"""Upstage Solar 비동기 래퍼.

Solar는 OpenAI SDK 호환이므로 `AsyncOpenAI(base_url=...)`로 감싼다.
LLM을 다른 제공자로 바꿀 일이 생기면 이 파일만 수정.
"""

import json
from functools import lru_cache
from typing import Any

from openai import APIError, AsyncOpenAI

from app.core.config import get_settings
from app.core.errors import LLMError


class LLMClient:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    async def generate_text(
        self, system: str, user: str, *, temperature: float = 0.3, max_tokens: int = 600
    ) -> str:
        try:
            resp = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except APIError as exc:
            raise LLMError(f"Upstage Solar API 실패: {exc}") from exc

        content = resp.choices[0].message.content or ""
        return content.strip()

    async def generate_json(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 800,
    ) -> dict[str, Any]:
        """JSON 강제. 시스템 프롬프트에 'JSON으로만 응답' 지시가 들어 있어야 한다."""
        try:
            resp = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
        except APIError as exc:
            raise LLMError(f"Upstage Solar API 실패: {exc}") from exc

        content = resp.choices[0].message.content or "{}"
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMError(f"LLM 응답이 JSON이 아님: {content[:200]}") from exc


@lru_cache
def get_llm() -> LLMClient:
    settings = get_settings()
    if not settings.upstage_api_key:
        raise LLMError("UPSTAGE_API_KEY 미설정")
    return LLMClient(
        api_key=settings.upstage_api_key,
        base_url=settings.upstage_base_url,
        model=settings.upstage_model,
    )
