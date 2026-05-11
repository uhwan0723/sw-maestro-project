"""오케스트레이터.

흐름:
  1) 캐시 hit 시 즉시 반환
  2) weather/news를 asyncio.gather로 병렬 호출 (return_exceptions=True)
  3) 둘 다 실패면 LLM 건너뛰고 안내 메시지
  4) LLM 통합 요약 (실패 시 fallback_text)
  5) 캐시에 저장 후 반환
"""

import asyncio
from datetime import UTC, datetime

from app.core import cache
from app.core.errors import LLMError
from app.core.llm import get_llm
from app.prompts.briefing import SYSTEM_PROMPT, build_user_prompt, fallback_text
from app.schemas.briefing import BriefingRequest, BriefingResponse
from app.schemas.news import NewsResult
from app.schemas.weather import WeatherData
from app.services.news import fetch_news
from app.services.weather import fetch_weather


def _cache_key(req: BriefingRequest) -> tuple:
    return (req.location, tuple(sorted(req.categories)), req.length)


async def _llm_integrate(
    weather: WeatherData | None, news: list[NewsResult], length: str
) -> tuple[str, str]:
    llm = get_llm()
    user_prompt = build_user_prompt(weather, news, length)
    payload = await llm.generate_json(SYSTEM_PROMPT, user_prompt)
    action_tip = str(payload.get("action_tip", "")).strip()
    integrated_summary = str(payload.get("integrated_summary", "")).strip()
    if not integrated_summary:
        raise LLMError("LLM이 integrated_summary를 비워서 반환")
    return action_tip, integrated_summary


async def build_briefing(req: BriefingRequest) -> BriefingResponse:
    key = _cache_key(req)
    if (cached := cache.get(key)) is not None:
        return cached

    weather_raw, news_raw = await asyncio.gather(
        fetch_weather(req.location),
        fetch_news(req.categories),
        return_exceptions=True,
    )

    degraded: list[str] = []
    weather: WeatherData | None
    news: list[NewsResult]

    # `return_exceptions=True`라 raw가 BaseException이면 실패. WeatherError/NewsError가 아닌
    # 예상 못 한 예외도 일단 해당 슬롯 실패로 간주해 사용자 응답을 막지 않는다.
    if isinstance(weather_raw, BaseException):
        weather = None
        degraded.append("weather")
    else:
        weather = weather_raw

    if isinstance(news_raw, BaseException):
        news = []
        degraded.append("news")
    else:
        news = news_raw

    now = datetime.now(UTC)

    if weather is None and not news:
        return BriefingResponse(
            weather=None,
            news=[],
            action_tip="",
            integrated_summary="외부 데이터 수집에 실패했어요. 잠시 후 다시 시도해 주세요.",
            generated_at=now,
            degraded=["weather", "news"],
        )

    try:
        action_tip, integrated_summary = await _llm_integrate(weather, news, req.length)
    except LLMError:
        action_tip = ""
        integrated_summary = fallback_text(weather, news)
        degraded.append("llm")

    response = BriefingResponse(
        weather=weather,
        news=news,
        action_tip=action_tip,
        integrated_summary=integrated_summary,
        generated_at=now,
        degraded=degraded,  # type: ignore[arg-type]
    )
    cache.set(key, response)
    return response
