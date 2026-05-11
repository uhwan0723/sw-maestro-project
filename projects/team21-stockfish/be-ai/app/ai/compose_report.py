from collections.abc import Mapping, Sequence
from typing import Any

from app.ai.state import (
    AgentState,
    AnalysisHypothesis,
    HypothesisVerificationResult,
    IndicatorContext,
)
from app.models.enums import RequestType, SectorCode, SECTOR_LABELS
from app.schemas.analysis import KeyEvidence
from app.schemas.common import SourceInfo, WarningMessage


DEFAULT_CAUTION = (
    "이 리포트는 수집된 KOSPI 시장 지표와 뉴스 요약을 바탕으로 한 "
    "교육용 해석이며, 매수/매도/보유 판단이나 수익률 예측이 아닙니다."
)
MAX_BASIS_PER_EVIDENCE = 3


def compose_report(state: AgentState | Mapping[str, Any]) -> dict[str, Any]:
    if _should_skip(state):
        return {}

    warnings = list(_read_existing_warnings(state))
    hypotheses = _read_hypotheses(state)
    verification_results = _read_verification_results(state)
    confidence = _read_confidence(state)
    sector = _read_sector(state)

    if not hypotheses:
        warnings.append(
            WarningMessage(
                code="report_hypotheses_missing",
                message="최종 리포트를 작성할 분석 가설이 없습니다.",
            )
        )
        confidence = 0.0 if confidence is None else confidence
        return _build_report_update(
            beginner_summary=_build_empty_summary(sector),
            key_evidence=[],
            trend_label="분석 보류",
            sources=_read_existing_sources(state),
            confidence=confidence,
            caution=DEFAULT_CAUTION,
            warnings=warnings,
        )

    selected_hypotheses = _select_report_hypotheses(
        hypotheses=hypotheses,
        verification_results=verification_results,
    )
    if not verification_results:
        warnings.append(
            WarningMessage(
                code="report_verification_missing",
                message="가설 검증 결과가 없어 생성된 가설을 참고 수준으로만 사용합니다.",
            )
        )
    elif not any(result.is_supported for result in verification_results):
        warnings.append(
            WarningMessage(
                code="report_supported_hypothesis_missing",
                message="충분히 뒷받침된 가설이 없어 리포트 신뢰도가 낮습니다.",
            )
        )

    trend_label = _derive_trend_label(
        state=state,
        hypotheses=selected_hypotheses,
    )
    key_evidence = [
        _build_key_evidence(hypothesis) for hypothesis in selected_hypotheses
    ]
    sources = _deduplicate_sources(
        [
            *_read_existing_sources(state),
            *[
                source
                for hypothesis in selected_hypotheses
                for source in hypothesis.sources
            ],
        ]
    )
    if not sources:
        warnings.append(
            WarningMessage(
                code="report_source_missing",
                message="최종 리포트에 연결할 출처가 없습니다.",
            )
        )

    confidence = _resolve_confidence(
        existing_confidence=confidence,
        verification_results=verification_results,
    )
    beginner_summary = _build_beginner_summary(
        sector=sector,
        trend_label=trend_label,
        key_evidence=key_evidence,
        confidence=confidence,
    )

    return _build_report_update(
        beginner_summary=beginner_summary,
        key_evidence=key_evidence,
        trend_label=trend_label,
        sources=sources,
        confidence=confidence,
        caution=DEFAULT_CAUTION,
        warnings=warnings,
    )


def _build_report_update(
    *,
    beginner_summary: str,
    key_evidence: Sequence[KeyEvidence],
    trend_label: str,
    sources: Sequence[SourceInfo],
    confidence: float,
    caution: str,
    warnings: Sequence[WarningMessage],
) -> dict[str, Any]:
    return {
        "beginner_summary": beginner_summary,
        "key_evidence": list(key_evidence),
        "trend_label": trend_label,
        "final_answer": _format_final_answer(
            beginner_summary=beginner_summary,
            key_evidence=key_evidence,
            sources=sources,
            caution=caution,
        ),
        "sources": list(sources),
        "confidence": confidence,
        "caution": caution,
        "warnings": list(warnings),
    }


def _format_final_answer(
    *,
    beginner_summary: str,
    key_evidence: Sequence[KeyEvidence],
    sources: Sequence[SourceInfo],
    caution: str,
) -> str:
    evidence_lines = [
        f"- {evidence.title}: {evidence.description}"
        for evidence in key_evidence
    ] or ["- 현재 리포트에 사용할 핵심 근거가 부족합니다."]
    source_lines = [_format_source_line(source) for source in sources] or [
        "- 확인된 출처가 없습니다."
    ]

    return "\n\n".join(
        [
            f"초보자용 요약\n{beginner_summary}",
            "핵심 근거\n" + "\n".join(evidence_lines),
            "출처\n" + "\n".join(source_lines),
            f"주의 문구\n{caution}",
        ]
    )


def _format_source_line(source: SourceInfo) -> str:
    title = source.title or source.url
    provider = f" ({source.provider})" if source.provider else ""
    return f"- {title}{provider}: {source.url}"


def _build_beginner_summary(
    *,
    sector: SectorCode | None,
    trend_label: str,
    key_evidence: Sequence[KeyEvidence],
    confidence: float,
) -> str:
    sector_label = _format_sector_label(sector)
    if not key_evidence:
        return (
            f"현재 확인된 KOSPI {sector_label} 섹터 데이터만으로는 "
            "뚜렷한 흐름을 말하기 어렵습니다. 데이터를 더 모은 뒤 "
            "지표와 뉴스가 같은 방향을 가리키는지 다시 확인해야 합니다."
        )

    main_points = ", ".join(evidence.title for evidence in key_evidence[:2])
    return (
        f"현재 KOSPI {sector_label} 섹터는 '{trend_label}' 흐름으로 "
        f"정리할 수 있습니다. 핵심 근거는 {main_points}입니다. "
        f"{_format_confidence_guidance(confidence)}"
    )


def _build_empty_summary(sector: SectorCode | None) -> str:
    sector_label = _format_sector_label(sector)
    return (
        f"현재 KOSPI {sector_label} 섹터 리포트를 만들 수 있는 가설이 "
        "부족합니다. 시장 지표와 뉴스 데이터가 수집된 뒤 다시 분석해야 합니다."
    )


def _build_key_evidence(hypothesis: AnalysisHypothesis) -> KeyEvidence:
    basis = [
        item.strip()
        for item in hypothesis.basis[:MAX_BASIS_PER_EVIDENCE]
        if item.strip()
    ]
    description = hypothesis.description
    if basis:
        description = f"{description} 근거: {' '.join(basis)}"

    return KeyEvidence(
        title=hypothesis.title,
        description=description,
        source=hypothesis.sources[0] if hypothesis.sources else None,
    )


def _select_report_hypotheses(
    *,
    hypotheses: Sequence[AnalysisHypothesis],
    verification_results: Sequence[HypothesisVerificationResult],
) -> tuple[AnalysisHypothesis, ...]:
    supported_titles = {
        result.hypothesis_title
        for result in verification_results
        if result.is_supported
    }
    if not supported_titles:
        return tuple(hypotheses)

    selected = [
        hypothesis for hypothesis in hypotheses if hypothesis.title in supported_titles
    ]
    return tuple(selected or hypotheses)


def _derive_trend_label(
    *,
    state: AgentState | Mapping[str, Any],
    hypotheses: Sequence[AnalysisHypothesis],
) -> str:
    indicator_context = _read_indicator_context(state)
    if indicator_context is not None:
        average_change = indicator_context.comparison.average_change_percent
        if average_change is not None:
            if average_change >= 0.5:
                return "상승 우세"
            if average_change <= -0.5:
                return "하락 우세"
            return "혼조 또는 보합"

    titles = " ".join(hypothesis.title for hypothesis in hypotheses)
    if "상승" in titles:
        return "상승 우세"
    if "하락" in titles:
        return "하락 우세"
    if "혼조" in titles or "보합" in titles:
        return "혼조 또는 보합"
    return "이슈 점검 필요"


def _resolve_confidence(
    *,
    existing_confidence: float | None,
    verification_results: Sequence[HypothesisVerificationResult],
) -> float:
    if existing_confidence is not None:
        return existing_confidence
    if not verification_results:
        return 0.0

    target_results = [
        result for result in verification_results if result.is_supported
    ] or list(verification_results)
    confidence = sum(result.confidence for result in target_results) / len(
        target_results
    )
    return round(confidence, 2)


def _format_sector_label(sector: SectorCode | None) -> str:
    if sector is None:
        return "대상"
    return SECTOR_LABELS.get(sector, sector.value)


def _format_confidence_guidance(confidence: float) -> str:
    if confidence >= 0.75:
        return (
            "신뢰도가 비교적 높아, 현재 수집된 근거 안에서는 "
            "흐름 판단의 일관성이 있는 편입니다. "
            "다만 투자 판단에는 추가 지표 확인이 필요합니다."
        )
    if confidence >= 0.5:
        return (
            "신뢰도는 중간 수준입니다. 방향성은 참고하되, "
            "추가 지표와 뉴스 흐름을 함께 확인하는 편이 좋습니다."
        )
    if confidence > 0.0:
        return (
            "다만 신뢰도는 낮은 수준이므로, 이 결과는 "
            "방향성을 이해하기 위한 참고 자료로 보는 편이 적절합니다."
        )
    return (
        "신뢰도가 매우 낮아, 현재 요약만으로 섹터 흐름을 "
        "판단하기는 어렵습니다."
    )


def _deduplicate_sources(sources: Sequence[SourceInfo]) -> list[SourceInfo]:
    deduplicated: list[SourceInfo] = []
    seen_urls: set[str] = set()
    for source in sources:
        if source.url in seen_urls:
            continue
        seen_urls.add(source.url)
        deduplicated.append(source)
    return deduplicated


def _should_skip(state: AgentState | Mapping[str, Any]) -> bool:
    if _has_final_answer(state):
        return True
    return _read_request_type(state) != RequestType.SECTOR_ANALYSIS


def _has_final_answer(state: AgentState | Mapping[str, Any]) -> bool:
    if isinstance(state, AgentState):
        return state.final_answer is not None

    final_answer = state.get("final_answer")
    return isinstance(final_answer, str) and bool(final_answer)


def _read_request_type(state: AgentState | Mapping[str, Any]) -> RequestType | None:
    if isinstance(state, AgentState):
        return state.request_type

    value = state.get("request_type")
    if isinstance(value, RequestType):
        return value
    if isinstance(value, str):
        try:
            return RequestType(value)
        except ValueError:
            return None
    return None


def _read_sector(state: AgentState | Mapping[str, Any]) -> SectorCode | None:
    if isinstance(state, AgentState):
        return state.sector

    value = state.get("sector")
    if isinstance(value, SectorCode):
        return value
    if isinstance(value, str):
        try:
            return SectorCode(value)
        except ValueError:
            return None
    return None


def _read_confidence(state: AgentState | Mapping[str, Any]) -> float | None:
    if isinstance(state, AgentState):
        return state.confidence

    value = state.get("confidence")
    if isinstance(value, int | float):
        return float(value)
    return None


def _read_indicator_context(
    state: AgentState | Mapping[str, Any],
) -> IndicatorContext | None:
    if isinstance(state, AgentState):
        return state.indicator_context

    value = state.get("indicator_context")
    if value is None:
        return None
    if isinstance(value, IndicatorContext):
        return value
    if isinstance(value, Mapping):
        return IndicatorContext.model_validate(value)
    return None


def _read_hypotheses(
    state: AgentState | Mapping[str, Any],
) -> tuple[AnalysisHypothesis, ...]:
    if isinstance(state, AgentState):
        return tuple(state.hypotheses)

    value = state.get("hypotheses", ())
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ()
    return tuple(_parse_hypothesis(hypothesis) for hypothesis in value)


def _parse_hypothesis(value: Any) -> AnalysisHypothesis:
    if isinstance(value, AnalysisHypothesis):
        return value
    if isinstance(value, Mapping):
        return AnalysisHypothesis.model_validate(value)
    raise ValueError("hypotheses items must be AnalysisHypothesis-compatible")


def _read_verification_results(
    state: AgentState | Mapping[str, Any],
) -> tuple[HypothesisVerificationResult, ...]:
    if isinstance(state, AgentState):
        return tuple(state.verification_results)

    value = state.get("verification_results", ())
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ()
    return tuple(_parse_verification_result(result) for result in value)


def _parse_verification_result(value: Any) -> HypothesisVerificationResult:
    if isinstance(value, HypothesisVerificationResult):
        return value
    if isinstance(value, Mapping):
        return HypothesisVerificationResult.model_validate(value)
    raise ValueError(
        "verification_results items must be HypothesisVerificationResult-compatible"
    )


def _read_existing_sources(
    state: AgentState | Mapping[str, Any],
) -> tuple[SourceInfo, ...]:
    if isinstance(state, AgentState):
        return tuple(state.sources)

    value = state.get("sources", ())
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ()
    return tuple(_parse_source(source) for source in value)


def _parse_source(value: Any) -> SourceInfo:
    if isinstance(value, SourceInfo):
        return value
    if isinstance(value, Mapping):
        return SourceInfo.model_validate(value)
    raise ValueError("sources items must be SourceInfo-compatible")


def _read_existing_warnings(
    state: AgentState | Mapping[str, Any],
) -> tuple[WarningMessage, ...]:
    if isinstance(state, AgentState):
        return tuple(state.warnings)

    value = state.get("warnings", ())
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ()
    return tuple(_parse_warning(warning) for warning in value)


def _parse_warning(value: Any) -> WarningMessage:
    if isinstance(value, WarningMessage):
        return value
    if isinstance(value, Mapping):
        return WarningMessage.model_validate(value)
    return WarningMessage(code="unknown_warning", message=str(value))
