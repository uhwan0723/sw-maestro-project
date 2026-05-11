"""백엔드 `app/schemas/`의 Pydantic 모델을 그대로 미러링한다.

contract가 어긋나면 `BriefingResponse.model_validate(...)`에서 즉시 실패해 FE에서 발견할 수 있다.
백엔드 schemas가 변경되면 이 파일도 함께 갱신한다.
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class WeatherData(BaseModel):
    location: str
    temperature_min: float
    temperature_max: float
    precipitation_probability: int
    pm25: int | None = None
    pm10: int | None = None
    summary: str
    fetched_at: datetime


class NewsItem(BaseModel):
    title: str
    summary: str
    url: HttpUrl
    published_at: datetime


class NewsResult(BaseModel):
    category: str
    items: list[NewsItem]


class BriefingRequest(BaseModel):
    location: str = Field(..., min_length=1, max_length=20)
    categories: list[str] = Field(..., min_length=1, max_length=5)
    length: Literal["short", "medium", "long"] = "medium"


class BriefingResponse(BaseModel):
    weather: WeatherData | None = None
    news: list[NewsResult] = Field(default_factory=list)
    action_tip: str
    integrated_summary: str
    generated_at: datetime
    degraded: list[Literal["weather", "news", "llm"]] = Field(default_factory=list)
