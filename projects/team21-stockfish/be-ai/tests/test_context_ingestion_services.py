import asyncio
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.enums import SectorCode
from app.models.market import MarketMetric
from app.models.news import NewsArticle
from app.schemas.common import WarningMessage
from app.services.context_service import ContextService
from app.services.ingestion_service import IngestionService


def run(coro):
    return asyncio.run(coro)


async def with_session(callback):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            return await callback(session)
    finally:
        await engine.dispose()


def test_context_service_builds_sector_context_with_market_fallback() -> None:
    async def scenario(session):
        session.add_all(
            [
                MarketMetric(
                    sector=SectorCode.SEMICONDUCTOR,
                    reference_date=date(2026, 5, 7),
                    metric_name="005930.KS:change_percent",
                    metric_value=1.2,
                    source="yfinance",
                ),
                NewsArticle(
                    sector=SectorCode.SEMICONDUCTOR,
                    reference_date=date(2026, 5, 8),
                    title="삼성전자 HBM 수출 기대",
                    url="https://example.com/news/1",
                    source="naver_news",
                    published_at=datetime(2026, 5, 8, 9, 0),
                    summary="반도체 수출 개선 기대가 있습니다.",
                    keywords=["삼성전자", "HBM"],
                ),
            ]
        )
        await session.commit()

        context = await ContextService(session).build_sector_context(
            SectorCode.SEMICONDUCTOR,
            reference_date=date(2026, 5, 8),
        )

        assert context.sector is SectorCode.SEMICONDUCTOR
        assert context.market_reference_date == date(2026, 5, 7)
        assert context.news_reference_date == date(2026, 5, 8)
        assert context.is_data_sufficient
        assert context.indicators.comparison.average_change_percent == 1.2
        assert context.news_articles[0].title == "삼성전자 HBM 수출 기대"
        assert [warning.code for warning in context.warnings] == [
            "market_previous_day_fallback"
        ]

    run(with_session(scenario))


def test_context_service_warns_when_data_is_missing() -> None:
    async def scenario(session):
        context = await ContextService(session).build_sector_context(
            SectorCode.PHARMACEUTICAL,
            reference_date=date(2026, 5, 8),
        )

        assert context.market_reference_date is None
        assert context.news_reference_date is None
        assert not context.is_data_sufficient
        assert [warning.code for warning in context.warnings] == [
            "market_data_missing",
            "news_data_missing",
            "insufficient_context_data",
        ]

    run(with_session(scenario))


@dataclass
class FakeCollectionResult:
    sector: SectorCode
    reference_date: date
    market_metric_count: int
    news_article_count: int


class FakeCollector:
    def __init__(self, failures: set[SectorCode] | None = None) -> None:
        self.failures = failures or set()
        self.collected: list[SectorCode] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args) -> None:
        pass

    async def collect_sector(
        self,
        sector: SectorCode,
        *,
        reference_date: date | None = None,
        news_display: int | None = None,
    ) -> FakeCollectionResult:
        if sector in self.failures:
            raise RuntimeError("수집 실패")
        self.collected.append(sector)
        return FakeCollectionResult(
            sector=sector,
            reference_date=reference_date or date(2026, 5, 8),
            market_metric_count=3,
            news_article_count=2,
        )


class FakeContextService:
    async def build_sector_context(
        self,
        sector: SectorCode,
        *,
        reference_date: date | None = None,
    ):
        return type(
            "FakeContext",
            (),
            {
                "warnings": (
                    WarningMessage(
                        code=f"{sector.value}_warning",
                        message="섹터 경고",
                    ),
                )
            },
        )()


def test_ingestion_service_collects_requested_sectors_and_deduplicates_warnings() -> None:
    collector = FakeCollector()

    async def scenario(session):
        result = await IngestionService(
            session,
            collector_factory=lambda _session: collector,
            context_service_factory=lambda _session: FakeContextService(),
        ).run_daily_collection(
            reference_date=date(2026, 5, 8),
            sectors=[SectorCode.SEMICONDUCTOR, SectorCode.SEMICONDUCTOR],
            news_display=10,
        )

        assert result.is_successful
        assert collector.collected == [
            SectorCode.SEMICONDUCTOR,
            SectorCode.SEMICONDUCTOR,
        ]
        assert [sector_result.sector for sector_result in result.sector_results] == [
            SectorCode.SEMICONDUCTOR,
            SectorCode.SEMICONDUCTOR,
        ]
        assert [warning.code for warning in result.warnings] == [
            "semiconductor_warning"
        ]

    run(with_session(scenario))


def test_ingestion_service_records_failed_sector_and_continues() -> None:
    collector = FakeCollector(failures={SectorCode.PHARMACEUTICAL})

    async def scenario(session):
        result = await IngestionService(
            session,
            collector_factory=lambda _session: collector,
            context_service_factory=lambda _session: FakeContextService(),
        ).run_daily_collection(
            reference_date=date(2026, 5, 8),
            sectors=[SectorCode.PHARMACEUTICAL, SectorCode.SEMICONDUCTOR],
        )

        assert not result.is_successful
        assert [failure.sector for failure in result.failed_sectors] == [
            SectorCode.PHARMACEUTICAL
        ]
        assert collector.collected == [SectorCode.SEMICONDUCTOR]
        assert result.sector_results[0].sector is SectorCode.SEMICONDUCTOR
        assert result.warnings[0].code == "sector_collection_failed"
        assert result.warnings[1].code == "semiconductor_warning"

    run(with_session(scenario))
