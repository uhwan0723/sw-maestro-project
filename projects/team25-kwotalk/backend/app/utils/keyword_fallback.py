"""LLM 장애 시 키워드 매칭 분류 폴백."""
from pydantic import BaseModel, Field

from app.taxonomy import CaseType

KEYWORDS: dict[str, list[str]] = {
    "HIT_AND_RUN": ["뺑소니", "도주", "사고 내고 도망", "구호조치", "사고 후 그냥", "사고 신고 안 함", "차로 친 후"],
    "DRUNK_DRIVING": ["음주운전", "술 마시고", "음주측정", "혈중알코올", "음주 단속", "만취", "DUI"],
    "WRONG_WAY_DRIVING": ["역주행", "중앙선", "반대 차선", "일방통행 거꾸로", "중앙선 침범", "중앙선 넘"],
    "PEDESTRIAN_ACCIDENT": ["보행자", "횡단보도", "어린이보호구역", "스쿨존", "행인", "사람을 침"],
    "RECKLESS_DRIVING": ["난폭운전", "난폭", "보복운전", "위협운전", "칼치기", "급제동", "진로방해"],
}

SETTLEMENT_TRIGGERS = {"합의금", "보상", "치료비", "위자료", "병원", "다쳤"}


class ClassificationOutput(BaseModel):
    case_type: CaseType
    needs_settlement: bool = Field(description="피해자 합의금 추정이 필요한 사안인가")
    confidence: float = Field(ge=0.0, le=1.0, description="분류 신뢰도")


def classify_by_keyword(query: str) -> ClassificationOutput:
    """문자열 매칭으로 case_type 추정. 매치 없으면 OUT_OF_SCOPE 반환."""
    matched: CaseType = "OUT_OF_SCOPE"

    for case_type, keywords in KEYWORDS.items():
        if any(kw in query for kw in keywords):
            matched = case_type  # type: ignore[assignment]
            break

    needs_settlement = (
        matched not in ("OUT_OF_SCOPE", "RECKLESS_DRIVING")
        and any(trigger in query for trigger in SETTLEMENT_TRIGGERS)
    )

    return ClassificationOutput(
        case_type=matched,
        needs_settlement=needs_settlement,
        confidence=0.3,
    )
