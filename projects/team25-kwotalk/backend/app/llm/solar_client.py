"""Upstage Solar API 래퍼 — 분류(JSON) / 생성(스트리밍). openai SDK 사용."""
import logging
import os
import time
from collections.abc import AsyncIterator

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.constants import LLM_CLASSIFY_MODEL, LLM_GENERATE_MODEL

# 프로젝트 루트의 .env 로딩 (이 파일은 backend/app/llm/solar_client.py)
load_dotenv(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        ".env",
    )
)

logger = logging.getLogger(__name__)

_UPSTAGE_BASE_URL = "https://api.upstage.ai/v1"

_client: AsyncOpenAI | None = None


class SolarAPIError(Exception):
    """Upstage Solar API 호출 실패."""


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("UPSTAGE_API_KEY")
        if not api_key:
            raise SolarAPIError("UPSTAGE_API_KEY 환경변수가 설정되지 않았습니다.")
        _client = AsyncOpenAI(api_key=api_key, base_url=_UPSTAGE_BASE_URL)
    return _client


async def call_flash_json(
    system_prompt: str,
    user_prompt: str,
    schema: type[BaseModel],
) -> BaseModel:
    """Solar mini 호출, JSON 응답을 Pydantic 으로 파싱 후 반환."""
    client = _get_client()
    start = time.perf_counter()
    logger.info("call_flash_json 시작 (model=%s)", LLM_CLASSIFY_MODEL)

    try:
        response = await client.chat.completions.create(
            model=LLM_CLASSIFY_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        raise SolarAPIError(f"Flash 호출 실패: {exc}") from exc

    elapsed = time.perf_counter() - start
    usage = response.usage
    logger.info(
        "call_flash_json 완료 (%.2fs) | 입력토큰=%s 출력토큰=%s",
        elapsed,
        getattr(usage, "prompt_tokens", "?"),
        getattr(usage, "completion_tokens", "?"),
    )

    content = response.choices[0].message.content or ""
    try:
        return schema.model_validate_json(content)
    except Exception as exc:
        raise SolarAPIError(f"JSON 파싱 실패: {exc}\n원문: {content}") from exc


async def call_pro_stream(
    system_prompt: str,
    user_prompt: str,
) -> AsyncIterator[str]:
    """Solar Pro 스트리밍 호출, 토큰 단위로 yield."""
    client = _get_client()
    start = time.perf_counter()
    logger.info("call_pro_stream 시작 (model=%s)", LLM_GENERATE_MODEL)

    return _iter_stream(client, system_prompt, user_prompt, start)


async def _iter_stream(
    client: AsyncOpenAI,
    system_prompt: str,
    user_prompt: str,
    start: float,
) -> AsyncIterator[str]:
    total_len = 0
    try:
        stream = await client.chat.completions.create(
            model=LLM_GENERATE_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,
        )
        async for chunk in stream:
            text = chunk.choices[0].delta.content or ""
            if text:
                total_len += len(text)
                yield text
    except Exception as exc:
        raise SolarAPIError(f"Pro 스트리밍 중 오류: {exc}") from exc

    elapsed = time.perf_counter() - start
    logger.info("call_pro_stream 완료 (%.2fs) | 누적 길이=%d자", elapsed, total_len)
