"""통합 브리핑 프롬프트.

기획서 §2 톤앤매너를 시스템 프롬프트에 못박는다:
- 군더더기 없는 한국어 존댓말
- 정치적 평가/의견 금지
- 사실 + 행동 권고에 집중
- 검색 결과에 없는 내용 추측 금지 (할루시네이션 방지)
"""

import json
from typing import Any

from app.schemas.news import NewsResult
from app.schemas.weather import WeatherData

SYSTEM_PROMPT = """당신은 아침 비서입니다. 사용자가 일어나자마자 1분 안에 하루를 준비할 수 있도록 \
오늘의 날씨와 핵심 뉴스를 한국어 존댓말로 요약합니다.

규칙:
- 입력으로 받은 데이터에 없는 사실은 절대 추가하지 않습니다.
- 정치적·이념적 평가나 개인 의견은 넣지 않습니다.
- 군더더기 없이 짧고 친근하게, 과장 없이 작성합니다.
- 행동 권고는 반드시 입력 데이터의 근거(강수, 기온, 미세먼지 등)에서 도출합니다.
- 응답은 반드시 다음 JSON 형식으로만 합니다. 다른 텍스트는 절대 포함하지 않습니다.

{
  "action_tip": "한 줄 행동 권고 (40자 내외)",
  "integrated_summary": "통합 카드 본문 (날씨 + 뉴스 묶음 요약)"
}
"""

LENGTH_GUIDE = {
    "short": "integrated_summary는 2~3문장, 80자 내외로 매우 짧게.",
    "medium": "integrated_summary는 4~5문장, 200자 내외로.",
    "long": "integrated_summary는 6~8문장, 400자 내외로 자세하게.",
}


def build_user_prompt(
    weather: WeatherData | None, news: list[NewsResult], length: str
) -> str:
    payload: dict[str, Any] = {
        "length_guide": LENGTH_GUIDE.get(length, LENGTH_GUIDE["medium"]),
        "weather": weather.model_dump(mode="json") if weather else None,
        "news": [r.model_dump(mode="json") for r in news],
    }
    return (
        "다음은 오늘의 원시 데이터입니다. 이 안에 있는 정보만 사용해 JSON을 작성하세요.\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def fallback_text(weather: WeatherData | None, news: list[NewsResult]) -> str:
    """LLM 실패 시 폴백. 입력 데이터를 그대로 한국어 카드 텍스트로 직조."""
    parts: list[str] = []
    if weather is not None:
        parts.append(weather.summary)
    if news:
        for result in news:
            for item in result.items[:2]:
                parts.append(f"[{result.category}] {item.title}")
    if not parts:
        return "지금은 데이터를 가져오지 못했습니다. 잠시 후 다시 시도해 주세요."
    return " · ".join(parts)
