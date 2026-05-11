from datetime import datetime

from pydantic import BaseModel, Field


class WeatherData(BaseModel):
    """배영빈 모듈(`app.services.weather.fetch_weather`)이 반환하는 타입.

    fetch_weather는 OpenWeatherMap 등 외부 API에서 원시 데이터를 가져와
    이 스키마로 정규화한다. summary는 LLM으로 한 줄 요약하거나, LLM 실패 시
    원시 데이터에서 만든 폴백 문자열을 채운다.
    """

    location: str = Field(..., description="조회한 도시명 (한국어)")
    temperature_min: float = Field(..., description="오늘 최저 기온 (°C)")
    temperature_max: float = Field(..., description="오늘 최고 기온 (°C)")
    precipitation_probability: int = Field(..., ge=0, le=100, description="강수 확률 (%)")
    pm25: int | None = Field(default=None, description="초미세먼지 농도 (㎍/㎥)")
    pm10: int | None = Field(default=None, description="미세먼지 농도 (㎍/㎥)")
    summary: str = Field(..., description="한 줄 요약 (LLM 가공 결과 또는 폴백)")
    fetched_at: datetime = Field(..., description="외부 API 호출 시각")
