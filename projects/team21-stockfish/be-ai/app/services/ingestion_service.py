from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.collector import CollectionResult, DataCollector
from app.models.enums import SECTOR_LABELS, SectorCode
from app.schemas.common import WarningMessage
from app.services.context_service import AgentInputContext, ContextService


class SectorCollector(Protocol):
    async def collect_sector(
        self,
        sector: SectorCode,
        *,
        reference_date: date | None = None,
        news_display: int | None = None,
    ) -> CollectionResult: ...


class SectorCollectorContext(Protocol):
    async def __aenter__(self) -> SectorCollector: ...

    async def __aexit__(self, *_: object) -> None: ...


class SectorContextService(Protocol):
    async def build_sector_context(
        self,
        sector: SectorCode,
        *,
        reference_date: date | None = None,
    ) -> AgentInputContext: ...


CollectorFactory = Callable[
    [AsyncSession],
    SectorCollectorContext,
]
ContextServiceFactory = Callable[[AsyncSession], SectorContextService]


def _build_data_collector(
    session: AsyncSession,
) -> SectorCollectorContext:
    return DataCollector(session=session)


@dataclass(frozen=True)
class SectorIngestionResult:
    sector: SectorCode
    reference_date: date
    market_metric_count: int
    news_article_count: int
    warnings: tuple[WarningMessage, ...]


@dataclass(frozen=True)
class SectorIngestionFailure:
    sector: SectorCode
    message: str


@dataclass(frozen=True)
class DailyIngestionResult:
    reference_date: date
    sector_results: tuple[SectorIngestionResult, ...]
    failed_sectors: tuple[SectorIngestionFailure, ...]
    warnings: tuple[WarningMessage, ...]

    @property
    def is_successful(self) -> bool:
        return not self.failed_sectors


class IngestionService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        collector_factory: CollectorFactory | None = None,
        context_service_factory: ContextServiceFactory | None = None,
    ) -> None:
        self._session = session
        self._collector_factory = collector_factory or _build_data_collector
        self._context_service_factory = context_service_factory or ContextService

    async def run_daily_collection(
        self,
        *,
        reference_date: date | None = None,
        sectors: Iterable[SectorCode] | None = None,
        news_display: int | None = None,
    ) -> DailyIngestionResult:
        target_date = reference_date or date.today()
        target_sectors = tuple(SectorCode) if sectors is None else tuple(sectors)
        sector_results: list[SectorIngestionResult] = []
        failed_sectors: list[SectorIngestionFailure] = []
        warnings: list[WarningMessage] = []

        async with self._collector_factory(self._session) as collector:
            context_service = self._context_service_factory(self._session)
            for sector in target_sectors:
                try:
                    collection_result = await collector.collect_sector(
                        sector,
                        reference_date=target_date,
                        news_display=news_display,
                    )
                    context = await context_service.build_sector_context(
                        sector,
                        reference_date=target_date,
                    )
                    sector_warning_messages = context.warnings
                    await self._session.commit()
                except Exception as exc:
                    await self._session.rollback()
                    failure = SectorIngestionFailure(
                        sector=sector,
                        message=str(exc),
                    )
                    failed_sectors.append(failure)
                    warnings.append(_build_failure_warning(failure))
                    continue

                sector_results.append(
                    _build_sector_ingestion_result(
                        collection_result=collection_result,
                        warnings=sector_warning_messages,
                    )
                )
                warnings.extend(sector_warning_messages)

        return DailyIngestionResult(
            reference_date=target_date,
            sector_results=tuple(sector_results),
            failed_sectors=tuple(failed_sectors),
            warnings=_deduplicate_warnings(warnings),
        )


def _build_sector_ingestion_result(
    *,
    collection_result: CollectionResult,
    warnings: tuple[WarningMessage, ...],
) -> SectorIngestionResult:
    return SectorIngestionResult(
        sector=collection_result.sector,
        reference_date=collection_result.reference_date,
        market_metric_count=collection_result.market_metric_count,
        news_article_count=collection_result.news_article_count,
        warnings=warnings,
    )


def _build_failure_warning(
    failure: SectorIngestionFailure,
) -> WarningMessage:
    sector_label = SECTOR_LABELS.get(failure.sector, failure.sector.value)
    return WarningMessage(
        code="sector_collection_failed",
        message=f"{sector_label} 데이터 수집에 실패했습니다: {failure.message}",
    )


def _deduplicate_warnings(
    warnings: list[WarningMessage],
) -> tuple[WarningMessage, ...]:
    deduplicated: list[WarningMessage] = []
    seen: set[tuple[str, str]] = set()
    for warning in warnings:
        key = (warning.code, warning.message)
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(warning)
    return tuple(deduplicated)
