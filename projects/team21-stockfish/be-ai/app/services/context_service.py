from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.indicator_normalizer import (
    NormalizedIndicatorContext,
    normalize_market_metrics,
)
from app.ingestion.news_processor import (
    ProcessedNewsArticle,
    process_saved_news_articles,
)
from app.models.enums import SECTOR_LABELS, SectorCode
from app.models.market import MarketMetric
from app.models.news import NewsArticle
from app.repositories.market_repository import MarketRepository
from app.repositories.news_repository import NewsRepository
from app.schemas.common import WarningMessage

RECENT_NEWS_CONTEXT_LIMIT = 12


@dataclass(frozen=True)
class AgentInputContext:
    sector: SectorCode
    sector_label: str
    requested_reference_date: date
    market_reference_date: date | None
    news_reference_date: date | None
    indicators: NormalizedIndicatorContext
    news_articles: tuple[ProcessedNewsArticle, ...]
    is_data_sufficient: bool
    warnings: tuple[WarningMessage, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "sector": self.sector.value,
            "sector_label": self.sector_label,
            "requested_reference_date": self.requested_reference_date.isoformat(),
            "market_reference_date": (
                self.market_reference_date.isoformat()
                if self.market_reference_date
                else None
            ),
            "news_reference_date": (
                self.news_reference_date.isoformat()
                if self.news_reference_date
                else None
            ),
            "indicators": self.indicators.to_payload(),
            "news_articles": [
                article.to_payload() for article in self.news_articles
            ],
            "is_data_sufficient": self.is_data_sufficient,
            "warnings": [warning.model_dump() for warning in self.warnings],
        }


class ContextService:
    def __init__(self, session: AsyncSession) -> None:
        self._market_repository = MarketRepository(session)
        self._news_repository = NewsRepository(session)

    async def build_sector_context(
        self,
        sector: SectorCode,
        *,
        reference_date: date | None = None,
    ) -> AgentInputContext:
        target_date = reference_date or date.today()
        (
            market_reference_date,
            market_metrics,
            market_warnings,
        ) = await self._load_market_metrics_with_fallback(
            sector=sector,
            reference_date=target_date,
        )
        (
            news_reference_date,
            news_articles,
            news_warnings,
        ) = await self._load_recent_news_articles(sector=sector)

        indicators = normalize_market_metrics(
            sector=sector,
            reference_date=market_reference_date or target_date,
            metrics=market_metrics,
        )
        processed_news_articles = tuple(process_saved_news_articles(news_articles))
        is_data_sufficient = indicators.has_data and bool(processed_news_articles)
        warnings = (
            *market_warnings,
            *news_warnings,
            *_build_data_sufficiency_warnings(
                has_market_data=indicators.has_data,
                has_news_data=bool(processed_news_articles),
            ),
        )

        return AgentInputContext(
            sector=sector,
            sector_label=SECTOR_LABELS[sector],
            requested_reference_date=target_date,
            market_reference_date=market_reference_date,
            news_reference_date=news_reference_date,
            indicators=indicators,
            news_articles=processed_news_articles,
            is_data_sufficient=is_data_sufficient,
            warnings=warnings,
        )

    async def _load_market_metrics_with_fallback(
        self,
        *,
        sector: SectorCode,
        reference_date: date,
    ) -> tuple[date | None, Sequence[MarketMetric], tuple[WarningMessage, ...]]:
        metrics = await self._market_repository.list_by_sector_and_date(
            sector=sector,
            reference_date=reference_date,
        )
        if metrics:
            return reference_date, metrics, ()

        previous_date = reference_date - timedelta(days=1)
        previous_metrics = await self._market_repository.list_by_sector_and_date(
            sector=sector,
            reference_date=previous_date,
        )
        if previous_metrics:
            return previous_date, previous_metrics, (
                WarningMessage(
                    code="market_previous_day_fallback",
                    message="요청 기준일의 주가 지표가 없어 전일 데이터를 사용했습니다.",
                ),
            )

        return None, (), (
            WarningMessage(
                code="market_data_missing",
                message="요청 기준일과 전일의 주가 지표가 없습니다.",
            ),
        )

    async def _load_recent_news_articles(
        self,
        *,
        sector: SectorCode,
    ) -> tuple[date | None, Sequence[NewsArticle], tuple[WarningMessage, ...]]:
        articles = await self._news_repository.list_recent_by_sector(
            sector=sector,
            limit=RECENT_NEWS_CONTEXT_LIMIT,
        )
        if articles:
            return articles[0].reference_date, articles, ()

        return None, (), (
            WarningMessage(
                code="news_data_missing",
                message="분석에 사용할 저장된 최근 뉴스가 없습니다.",
            ),
        )


def _build_data_sufficiency_warnings(
    *,
    has_market_data: bool,
    has_news_data: bool,
) -> tuple[WarningMessage, ...]:
    if has_market_data and has_news_data:
        return ()
    return (
        WarningMessage(
            code="insufficient_context_data",
            message="분석에 필요한 주가 지표 또는 뉴스 데이터가 부족합니다.",
        ),
    )
