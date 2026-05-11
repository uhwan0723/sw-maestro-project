from enum import StrEnum


class SectorCode(StrEnum):
    SEMICONDUCTOR = "semiconductor"
    PHARMACEUTICAL = "pharmaceutical"


class RequestType(StrEnum):
    SECTOR_ANALYSIS = "sector_analysis"
    TERM_EXPLANATION = "term_explanation"
    OUT_OF_SCOPE = "out_of_scope"


SECTOR_LABELS: dict[SectorCode, str] = {
    SectorCode.SEMICONDUCTOR: "반도체",
    SectorCode.PHARMACEUTICAL: "제약",
}
