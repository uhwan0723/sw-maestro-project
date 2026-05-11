"""배영빈 영역 — 날씨 모듈.

이 파일은 BE 코어가 정의한 시그니처와 스텁만 들어 있다. 영빈은 본문을
실제 OpenWeatherMap(또는 동등한 API) 호출로 교체한다.

규칙:
- 반환 타입은 반드시 `WeatherData`(`app.schemas.weather`).
- 실패 시 `WeatherError`(`app.core.errors`)를 raise. HTTPException 던지지 말 것.
- LLM 한 줄 요약이 필요하면 `app.core.llm.get_llm()`을 import해서 사용.
"""

from datetime import UTC, datetime

import httpx

from app.core.config import get_settings
from app.core.errors import LLMError, WeatherError
from app.core.llm import get_llm
from app.schemas.weather import WeatherData

# 한글 도시명 → OpenWeatherMap 영어 도시명 매핑
CITY_NAME_MAP = {
    "서울": "Seoul",
    "강남": "Gangnam",
    "부산": "Busan",
    "대구": "Daegu",
    "인천": "Incheon",
    "광주": "Gwangju",
    "대전": "Daejeon",
    "울산": "Ulsan",
    "경기": "Gyeonggi",
    "강원": "Gangwon",
    "충청": "Chungcheong",
    "전라": "Jeolla",
    "경상": "Gyeongsang",
    "제주": "Jeju",
}


async def fetch_weather(location: str) -> WeatherData:
    """위치 문자열을 받아 오늘 날씨 데이터를 반환한다.

    Args:
        location: 한국 주요 도시명 (예: "서울", "강남").

    Returns:
        정규화된 `WeatherData`. summary 필드는 영빈이 LLM 또는 폴백으로 채운다.

    Raises:
        WeatherError: 외부 API 실패, 응답 파싱 실패, 위치 미지원 등.
    """
    # 배영빈: 한글 도시명을 OpenWeatherMap이 지원하는 영어명으로 변환
    city_en = CITY_NAME_MAP.get(location, location)
    
    settings = get_settings()
    if not settings.openweather_api_key:
        raise WeatherError("OPENWEATHER_API_KEY 미설정")

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. OpenWeatherMap에서 현재 날씨 정보 가져오기
        weather_url = "https://api.openweathermap.org/data/2.5/weather"
        weather_params = {
            "q": city_en,
            "appid": settings.openweather_api_key,
            "units": "metric",
            "lang": "ko",
        }

        try:
            resp = await client.get(weather_url, params=weather_params)
            if resp.status_code != 200:
                raise WeatherError(f"OpenWeatherMap API 오류: {resp.status_code}")
            weather_data = resp.json()
        except WeatherError:
            raise
        except httpx.RequestError as exc:
            raise WeatherError(f"날씨 API 호출 실패: {exc}") from exc
        except Exception as exc:
            raise WeatherError(f"날씨 데이터 처리 실패: {exc}") from exc

        # 2. 필요한 데이터 파싱
        try:
            temp_min = weather_data["main"]["temp_min"]
            temp_max = weather_data["main"]["temp_max"]
            clouds = weather_data.get("clouds", {}).get("all", 0)
            # 강수확률: OpenWeather에는 직접 제공 안 함, 구름양으로 추정
            precipitation_prob = clouds
            lat = weather_data["coord"]["lat"]
            lon = weather_data["coord"]["lon"]
            weather_desc = weather_data.get("weather", [{}])[0].get("description", "")
        except (KeyError, TypeError, IndexError) as exc:
            raise WeatherError(f"날씨 응답 파싱 실패: {exc}") from exc

        # 3. 미세먼지 정보 가져오기 (Air Pollution API)
        pm25 = None
        pm10 = None
        try:
            air_url = "https://api.openweathermap.org/data/2.5/air_pollution"
            air_params = {"lat": lat, "lon": lon, "appid": settings.openweather_api_key}
            resp = await client.get(air_url, params=air_params)
            if resp.status_code == 200:
                air_data = resp.json()
                components = air_data.get("list", [{}])[0].get("components", {})
                pm25 = int(components.get("pm2_5", 0))
                pm10 = int(components.get("pm10", 0))
        except Exception:
            # 미세먼지 정보는 옵션이므로 실패해도 무시
            pass

        # 4. LLM으로 한 줄 요약 생성
        summary = await _generate_summary(location, temp_min, temp_max, precipitation_prob, pm25, pm10, weather_desc)

        return WeatherData(
            location=location,
            temperature_min=temp_min,
            temperature_max=temp_max,
            precipitation_probability=precipitation_prob,
            pm25=pm25,
            pm10=pm10,
            summary=summary,
            fetched_at=datetime.now(UTC),
        )


async def _generate_summary(
    location: str, temp_min: float, temp_max: float, precip_prob: int, pm25: int | None, pm10: int | None, weather_desc: str
) -> str:
    """배영빈: LLM을 사용하여 날씨를 한 줄로 요약한다. 실패 시 폴백."""
    try:
        llm = get_llm()
        weather_info = f"{location} 오늘 최저 {temp_min}°C, 최고 {temp_max}°C, 강수확률 {precip_prob}%, {weather_desc}"
        if pm25 is not None:
            weather_info += f", 초미세먼지 {pm25}㎍/㎥, 미세먼지 {pm10}㎍/㎥"

        system_prompt = "사용자가 제공한 날씨 정보를 바탕으로 한국어 한 줄 날씨 요약을 작성하세요. 간결하고 명확하게."
        summary = await llm.generate_text(system=system_prompt, user=weather_info, max_tokens=100, temperature=0.3)
        return summary
    except LLMError:
        # LLM 실패 시 폴백 요약
        return _fallback_summary(location, temp_min, temp_max, precip_prob, pm25, pm10)


def _fallback_summary(location: str, temp_min: float, temp_max: float, precip_prob: int, pm25: int | None, pm10: int | None) -> str:
    """배영빈: LLM 호출 실패 시 기본 요약."""
    summary = f"{location} 오늘 {temp_min}~{temp_max}°C, 강수 확률 {precip_prob}%"
    if pm25 is not None:
        pm_level = "좋음" if pm25 < 35 else "보통" if pm25 < 75 else "나쁨"
        summary += f", 미세먼지 {pm_level}"
    return summary


def _stub_weather(location: str) -> WeatherData:
    """개발/테스트용 더미 데이터. 영빈 모듈 완성 전 BE 검증에만 사용."""
    return WeatherData(
        location=location,
        temperature_min=10.0,
        temperature_max=18.0,
        precipitation_probability=70,
        pm25=35,
        pm10=55,
        summary=f"{location} 오늘 10~18°C, 오후 강수 확률 70%, 미세먼지 보통",
        fetched_at=datetime.now(UTC),
    )
