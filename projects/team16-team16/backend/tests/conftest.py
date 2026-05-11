from datetime import UTC, datetime

import pytest

from app.core import cache as cache_module
from app.schemas.news import NewsItem, NewsResult
from app.schemas.weather import WeatherData


@pytest.fixture(autouse=True)
def _clear_cache():
    """각 테스트 전후로 캐시 비움."""
    cache_module.clear()
    yield
    cache_module.clear()


@pytest.fixture
def fake_weather() -> WeatherData:
    return WeatherData(
        location="서울",
        temperature_min=10.0,
        temperature_max=18.0,
        precipitation_probability=70,
        pm25=35,
        pm10=55,
        summary="서울 오늘 10~18°C, 오후 강수 70%, 미세먼지 보통",
        fetched_at=datetime.now(UTC),
    )


@pytest.fixture
def fake_news() -> list[NewsResult]:
    now = datetime.now(UTC)
    return [
        NewsResult(
            category="IT",
            items=[
                NewsItem(
                    title="IT 헤드라인 1",
                    summary="요약 1",
                    url="https://example.com/it/1",
                    published_at=now,
                )
            ],
        ),
    ]
