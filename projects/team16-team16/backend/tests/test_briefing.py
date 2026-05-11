"""오케스트레이터 부분 실패 매트릭스 테스트.

가이드의 4가지 케이스:
  1) 정상 경로 → degraded=[]
  2) weather 실패 → degraded=["weather"], news만 LLM에 전달
  3) news 실패 → degraded=["news"], weather만 LLM에 전달
  4) 둘 다 실패 → LLM 미호출, degraded=["weather","news"]
  5) LLM 실패 → fallback_text 사용, degraded=["llm"]
  6) 캐시: 같은 요청 두 번 → LLM 호출 0번
"""

from __future__ import annotations

from typing import Any

import pytest

from app.core.errors import LLMError, NewsError, WeatherError
from app.schemas.briefing import BriefingRequest


@pytest.fixture
def patch_services(monkeypatch, fake_weather, fake_news):
    """fetch_weather/fetch_news를 monkeypatch하기 위한 헬퍼.

    `behavior`로 'ok' / 'raise'를 지정.
    """

    def _apply(*, weather: str = "ok", news: str = "ok") -> dict[str, Any]:
        call_count = {"weather": 0, "news": 0}

        async def fake_fetch_weather(location: str):
            call_count["weather"] += 1
            if weather == "raise":
                raise WeatherError("forced")
            return fake_weather

        async def fake_fetch_news(categories: list[str], limit: int = 5):
            call_count["news"] += 1
            if news == "raise":
                raise NewsError("forced")
            return fake_news

        monkeypatch.setattr("app.services.briefing.fetch_weather", fake_fetch_weather)
        monkeypatch.setattr("app.services.briefing.fetch_news", fake_fetch_news)
        return call_count

    return _apply


@pytest.fixture
def patch_llm(monkeypatch):
    """LLM 통합 함수를 monkeypatch."""

    def _apply(*, behavior: str = "ok") -> dict[str, int]:
        count = {"calls": 0}

        async def fake_integrate(weather, news, length):
            count["calls"] += 1
            if behavior == "raise":
                raise LLMError("forced")
            return ("우산 챙기세요", "통합 요약")

        monkeypatch.setattr("app.services.briefing._llm_integrate", fake_integrate)
        return count

    return _apply


def _req() -> BriefingRequest:
    return BriefingRequest(location="서울", categories=["IT"], length="medium")


@pytest.mark.asyncio
async def test_happy_path(patch_services, patch_llm):
    patch_services()
    llm_calls = patch_llm()

    from app.services.briefing import build_briefing

    resp = await build_briefing(_req())

    assert resp.degraded == []
    assert resp.weather is not None
    assert len(resp.news) == 1
    assert resp.action_tip == "우산 챙기세요"
    assert resp.integrated_summary == "통합 요약"
    assert llm_calls["calls"] == 1


@pytest.mark.asyncio
async def test_weather_fails(patch_services, patch_llm):
    patch_services(weather="raise")
    llm_calls = patch_llm()

    from app.services.briefing import build_briefing

    resp = await build_briefing(_req())

    assert resp.weather is None
    assert len(resp.news) == 1
    assert resp.degraded == ["weather"]
    assert llm_calls["calls"] == 1  # 뉴스만 가지고도 LLM 호출


@pytest.mark.asyncio
async def test_news_fails(patch_services, patch_llm):
    patch_services(news="raise")
    llm_calls = patch_llm()

    from app.services.briefing import build_briefing

    resp = await build_briefing(_req())

    assert resp.weather is not None
    assert resp.news == []
    assert resp.degraded == ["news"]
    assert llm_calls["calls"] == 1


@pytest.mark.asyncio
async def test_both_fail_skip_llm(patch_services, patch_llm):
    patch_services(weather="raise", news="raise")
    llm_calls = patch_llm()

    from app.services.briefing import build_briefing

    resp = await build_briefing(_req())

    assert resp.weather is None
    assert resp.news == []
    assert sorted(resp.degraded) == ["news", "weather"]
    assert resp.integrated_summary  # 안내 문구가 들어있어야 함
    assert llm_calls["calls"] == 0  # LLM 호출 안 함


@pytest.mark.asyncio
async def test_llm_fails_uses_fallback(patch_services, patch_llm):
    patch_services()
    patch_llm(behavior="raise")

    from app.services.briefing import build_briefing

    resp = await build_briefing(_req())

    assert "llm" in resp.degraded
    assert resp.weather is not None
    assert len(resp.news) == 1
    assert resp.action_tip == ""
    assert resp.integrated_summary  # fallback_text가 채움


@pytest.mark.asyncio
async def test_cache_hits_on_second_call(patch_services, patch_llm):
    counts = patch_services()
    llm_calls = patch_llm()

    from app.services.briefing import build_briefing

    req = _req()
    resp1 = await build_briefing(req)
    resp2 = await build_briefing(req)

    assert resp1 == resp2
    # 두 번째는 캐시 hit이라 외부/LLM 호출이 한 번씩만
    assert counts["weather"] == 1
    assert counts["news"] == 1
    assert llm_calls["calls"] == 1
