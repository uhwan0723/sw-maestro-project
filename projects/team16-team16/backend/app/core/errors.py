"""도메인 예외.

services/ 안에서는 이 예외들만 던진다. HTTPException은 절대 services에서 던지지 말 것.
api/routes.py의 글로벌 핸들러가 사용자 메시지로 변환한다.
"""


class BriefingError(Exception):
    """모든 도메인 예외의 기반."""


class WeatherError(BriefingError):
    """날씨 모듈(외부 API, 파싱, LLM 가공) 실패."""


class NewsError(BriefingError):
    """뉴스 모듈(외부 API, 파싱, LLM 가공) 실패."""


class LLMError(BriefingError):
    """BE 코어의 통합 요약 LLM 호출 실패."""
