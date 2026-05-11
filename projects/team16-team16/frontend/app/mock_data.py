"""백엔드/Agent 미완성 동안 카드 UI를 개발하기 위한 가짜 응답.

contract(`BriefingResponse`)는 그대로 따른다. 값만 그럴듯하게 채운다.
실제 백엔드가 채우는 톤/길이는 다를 수 있어, 카드 UI는 길이 변동에 견고해야 한다.
"""
from datetime import datetime, timezone

from app.schemas import (
    BriefingRequest,
    BriefingResponse,
    NewsItem,
    NewsResult,
    WeatherData,
)

_NEWS_BY_CATEGORY: dict[str, list[tuple[str, str]]] = {
    "IT": [
        ("삼성전자, 차세대 AI 반도체 공개", "삼성전자가 추론 성능을 두 배 끌어올린 신형 NPU를 공개했습니다."),
        ("오픈소스 LLM 한국어 벤치마크 1위 갱신", "국내 스타트업 모델이 KMMLU에서 새 기록을 세웠습니다."),
        ("애플, 아이폰 보급형 신모델 발표 임박", "다음 주 키노트에서 새 보급형 라인업이 공개될 전망입니다."),
    ],
    "경제": [
        ("코스피 2,650선 회복 마감", "외국인 매수세에 힘입어 사흘 만에 반등 마감했습니다."),
        ("한은 기준금리 동결 시사", "5월 금통위에서 동결이 유력하다는 분석이 나왔습니다."),
        ("원/달러 환율 1,360원대 진입", "달러 약세 흐름에 환율이 한 달 만에 최저치를 기록했습니다."),
    ],
    "사회": [
        ("서울 지하철 2호선 일부 구간 지연", "출근길 신호 장애로 약 15분간 운행이 늦어졌습니다."),
        ("전국 미세먼지 보통 수준", "중부 지역 일부에서 나쁨이 예보되었습니다."),
        ("어린이날 연휴 고속도로 정체 시작", "오전부터 주요 노선에서 정체가 시작됐습니다."),
    ],
    "문화": [
        ("국립현대미술관 기획전 개막", "한국 현대 회화 50년을 조명하는 대규모 기획전이 시작됐습니다."),
        ("부산국제영화제 개막작 공개", "올해 개막작으로 한국 신인 감독의 장편 데뷔작이 선정됐습니다."),
        ("연극 햄릿 재공연 매진 행렬", "10년 만의 재공연이 전 회차 매진을 기록했습니다."),
    ],
    "정치": [
        ("국회, 본회의 일정 조율", "여야 원내대표가 다음 주 본회의 안건을 협상 중입니다."),
        ("총리 후보자 인사청문회 일정 확정", "다음 주 화요일 인사청문회가 열립니다."),
        ("지방선거 사전투표 안내", "사전투표 일정과 장소가 공개됐습니다."),
    ],
    "스포츠": [
        ("손흥민, 시즌 20호 골 기록", "토트넘이 원정 경기에서 3-1 승리를 거뒀습니다."),
        ("KBO 주말 주요 경기 결과", "주말 경기에서 1위 팀이 위닝 시리즈를 이어갔습니다."),
        ("LPGA 한국 선수 공동 2위", "최종 라운드 막판 추격전이 펼쳐졌습니다."),
    ],
}


def make_mock_briefing(req: BriefingRequest, *, scenario: str = "normal") -> BriefingResponse:
    """카드 UI 개발용 가짜 응답.

    scenario:
      - "normal":   모든 필드 정상
      - "no_weather": weather=None, degraded=["weather"]
      - "no_news":    news=[],     degraded=["news"]
      - "all_failed": weather=None, news=[], degraded=["weather", "news"], LLM 미호출 안내 문구
      - "llm_fail":   degraded=["llm"], 폴백 텍스트 사용
    """
    now = datetime.now(timezone.utc)

    weather = WeatherData(
        location=req.location,
        temperature_min=10.0,
        temperature_max=18.0,
        precipitation_probability=70,
        pm25=35,
        pm10=55,
        summary=f"{req.location} 오늘 10~18°C, 오후 강수 확률 70%, 미세먼지 보통입니다.",
        fetched_at=now,
    )
    news = [
        NewsResult(
            category=cat,
            items=[
                NewsItem(
                    title=title,
                    summary=summary,
                    url=f"https://example.com/news/{cat}/{i}",
                    published_at=now,
                )
                for i, (title, summary) in enumerate(
                    _NEWS_BY_CATEGORY.get(cat, []), start=1
                )
            ],
        )
        for cat in req.categories
    ]

    if scenario == "no_weather":
        return BriefingResponse(
            weather=None,
            news=news,
            action_tip="오늘 헤드라인 1건만 확인하시기 바랍니다.",
            integrated_summary=(
                f"날씨 정보를 일시적으로 가져오지 못했습니다. "
                f"관심 카테고리({', '.join(req.categories)})의 주요 헤드라인은 아래 카드에서 확인하실 수 있습니다."
            ),
            generated_at=now,
            degraded=["weather"],
        )
    if scenario == "no_news":
        return BriefingResponse(
            weather=weather,
            news=[],
            action_tip="비가 올 수 있으니 우산을 챙기시기 바랍니다.",
            integrated_summary=(
                f"오늘 {req.location}은 10~18°C, 오후 강수 확률이 높습니다. "
                f"뉴스 정보는 일시적으로 가져오지 못했습니다."
            ),
            generated_at=now,
            degraded=["news"],
        )
    if scenario == "all_failed":
        return BriefingResponse(
            weather=None,
            news=[],
            action_tip="",
            integrated_summary="외부 데이터 수집에 실패했습니다. 잠시 후 다시 시도해 주세요.",
            generated_at=now,
            degraded=["weather", "news"],
        )
    if scenario == "llm_fail":
        return BriefingResponse(
            weather=weather,
            news=news,
            action_tip="",
            integrated_summary=(
                f"{req.location} 10~18°C, 강수 70%. "
                f"카테고리: {', '.join(req.categories)}."
            ),
            generated_at=now,
            degraded=["llm"],
        )

    return BriefingResponse(
        weather=weather,
        news=news,
        action_tip="비가 올 수 있으니 우산을 챙기시고, 출근길 헤드라인을 한 번 확인해 보시기 바랍니다.",
        integrated_summary=(
            f"오늘 {req.location}은 10~18°C로 일교차가 크고 오후 강수 확률이 높습니다. "
            f"관심 카테고리({', '.join(req.categories)})의 주요 헤드라인은 아래 카드에서 확인하실 수 있습니다."
        ),
        generated_at=now,
        degraded=[],
    )
