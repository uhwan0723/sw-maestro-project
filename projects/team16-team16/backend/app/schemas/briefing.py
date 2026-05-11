from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.news import NewsResult
from app.schemas.weather import WeatherData


class BriefingRequest(BaseModel):
    location: str = Field(..., min_length=1, max_length=20, description="도시명 (한국 주요 도시)")
    categories: list[str] = Field(
        ..., min_length=1, max_length=5, description="관심 뉴스 카테고리. 예: ['IT', '경제']"
    )
    length: Literal["short", "medium", "long"] = Field(
        default="medium", description="브리핑 길이"
    )


class BriefingResponse(BaseModel):
    weather: WeatherData | None = Field(default=None, description="날씨 실패 시 null")
    news: list[NewsResult] = Field(default_factory=list, description="뉴스 실패 시 빈 리스트")
    action_tip: str = Field(..., description="한 줄 행동 권고 (LLM 실패 시 빈 문자열)")
    integrated_summary: str = Field(..., description="통합 카드 본문 (LLM 실패 시 폴백 텍스트)")
    generated_at: datetime = Field(..., description="브리핑 생성 시각")
    degraded: list[Literal["weather", "news", "llm"]] = Field(
        default_factory=list,
        description="부분 실패 표시. FE가 안내 문구로 활용",
    )
