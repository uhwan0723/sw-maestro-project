from collections.abc import Awaitable, Callable, Sequence
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.graph import run_agent
from app.ai.state import AgentState
from app.core.errors import AnalysisConfidenceError
from app.models.analysis import AnalysisResult
from app.models.enums import RequestType, SECTOR_LABELS, SectorCode
from app.repositories.analysis_repository import AnalysisRepository
from app.schemas.analysis import KeyEvidence, SectorAnalysisResponse
from app.schemas.common import SourceInfo, WarningMessage


AgentRunner = Callable[[AgentState], Awaitable[AgentState]]

DEFAULT_ANALYSIS_CAUTION = (
    "이 리포트는 수집된 KOSPI 시장 지표와 뉴스 요약을 바탕으로 한 "
    "교육용 해석이며, 매수/매도/보유 판단이나 수익률 예측이 아닙니다."
)
MIN_ANALYSIS_CONFIDENCE = 0.0


class AnalysisService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        agent_runner: AgentRunner = run_agent,
    ) -> None:
        self._session = session
        self._analysis_repository = AnalysisRepository(session)
        self._agent_runner = agent_runner

    async def get_today_sector_analysis(
        self,
        sector: SectorCode,
        *,
        refresh: bool = False,
    ) -> SectorAnalysisResponse:
        reference_date = date.today()
        if not refresh:
            cached_analysis = (
                await self._analysis_repository.get_optional_by_sector_and_date(
                    sector=sector,
                    reference_date=reference_date,
                )
            )
            if cached_analysis is not None:
                return _build_analysis_response(cached_analysis)

        state = await self._agent_runner(
            AgentState(
                user_message=_build_sector_analysis_message(sector),
                request_type=RequestType.SECTOR_ANALYSIS,
                sector=sector,
            )
        )
        _ensure_analysis_confidence(state)
        analysis = await self._analysis_repository.upsert(
            _build_analysis_result(
                sector=sector,
                reference_date=reference_date,
                state=state,
            )
        )
        await self._session.commit()
        return _build_analysis_response(analysis, warnings=state.warnings)


def _build_sector_analysis_message(sector: SectorCode) -> str:
    sector_label = SECTOR_LABELS.get(sector, sector.value)
    return f"KOSPI {sector_label} 섹터의 오늘 시장 흐름을 분석해줘."


def _ensure_analysis_confidence(state: AgentState) -> None:
    confidence = state.confidence if state.confidence is not None else 0.0
    if confidence <= MIN_ANALYSIS_CONFIDENCE:
        raise AnalysisConfidenceError(
            confidence=confidence,
            warnings=state.warnings,
        )


def _build_analysis_result(
    *,
    sector: SectorCode,
    reference_date: date,
    state: AgentState,
) -> AnalysisResult:
    return AnalysisResult(
        sector=sector,
        reference_date=reference_date,
        trend_label=state.trend_label or "분석 보류",
        confidence=state.confidence if state.confidence is not None else 0.0,
        beginner_summary=_resolve_beginner_summary(state),
        key_evidence=_dump_key_evidence(state.key_evidence),
        sources=_dump_sources(state.sources),
        caution=state.caution or state.safety_notice or DEFAULT_ANALYSIS_CAUTION,
    )


def _resolve_beginner_summary(state: AgentState) -> str:
    if state.beginner_summary:
        return state.beginner_summary
    if state.final_answer:
        return state.final_answer
    return "분석에 필요한 데이터가 부족해 오늘 섹터 흐름을 요약하지 못했습니다."


def _dump_key_evidence(key_evidence: Sequence[KeyEvidence]) -> list[dict[str, object]]:
    return [evidence.model_dump(mode="json") for evidence in key_evidence]


def _dump_sources(sources: Sequence[SourceInfo]) -> list[dict[str, object]]:
    return [source.model_dump(mode="json") for source in sources]


def _build_analysis_response(
    analysis: AnalysisResult,
    *,
    warnings: Sequence[WarningMessage] = (),
) -> SectorAnalysisResponse:
    return SectorAnalysisResponse(
        sector=analysis.sector,
        beginner_summary=analysis.beginner_summary,
        key_evidence=[
            KeyEvidence.model_validate(evidence)
            for evidence in analysis.key_evidence
        ],
        sources=[SourceInfo.model_validate(source) for source in analysis.sources],
        confidence=analysis.confidence,
        caution=analysis.caution,
        warnings=list(warnings),
    )
