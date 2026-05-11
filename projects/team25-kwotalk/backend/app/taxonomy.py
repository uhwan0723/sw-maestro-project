"""교통 도메인 case_type enum + 표시용 매핑."""
from typing import Literal

CaseType = Literal[
    "HIT_AND_RUN",
    "WRONG_WAY_DRIVING",
    "DRUNK_DRIVING",
    "PEDESTRIAN_ACCIDENT",
    "RECKLESS_DRIVING",
    "OUT_OF_SCOPE",
]

CASE_TYPE_KOREAN: dict[str, str] = {
    "HIT_AND_RUN": "뺑소니",
    "WRONG_WAY_DRIVING": "역주행·중앙선침범",
    "DRUNK_DRIVING": "음주운전",
    "PEDESTRIAN_ACCIDENT": "보행자사고",
    "RECKLESS_DRIVING": "난폭운전·안전운전위반",
    "OUT_OF_SCOPE": "교통 무관",
}

NEEDS_SETTLEMENT_CANDIDATES: set[str] = {
    "HIT_AND_RUN",
    "WRONG_WAY_DRIVING",
    "DRUNK_DRIVING",
    "PEDESTRIAN_ACCIDENT",
}
