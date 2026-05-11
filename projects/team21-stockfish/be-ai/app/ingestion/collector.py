import asyncio
from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.ingestion.naver_news_client import NaverNewsClient
from app.ingestion.news_processor import process_naver_news_articles
from app.ingestion.yfinance_client import MarketQuote, YFinanceClient
from app.models.enums import SectorCode
from app.models.market import MarketMetric
from app.models.news import NewsArticle
from app.repositories.market_repository import MarketRepository
from app.repositories.news_repository import NewsRepository
from app.schemas.ingestion import (
    NormalizedMarketQuote,
    NormalizedMarketQuoteBatch,
    NormalizedNewsArticleBatch,
)


@dataclass(frozen=True)
class CollectionResult:
    sector: SectorCode
    reference_date: date
    market_metric_count: int
    news_article_count: int


class DataCollector:
    def __init__(
        self,
        *,
        session: AsyncSession,
        yfinance_client: YFinanceClient | None = None,
        naver_news_client: NaverNewsClient | None = None,
    ) -> None:
        self._market_repository = MarketRepository(session)
        self._news_repository = NewsRepository(session)
        self._yfinance_client = yfinance_client or YFinanceClient()
        self._naver_news_client = naver_news_client or NaverNewsClient()
        self._owns_naver_news_client = naver_news_client is None

    async def __aenter__(self) -> "DataCollector":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_naver_news_client:
            await self._naver_news_client.aclose()

    async def collect_sector(
        self,
        sector: SectorCode,
        *,
        reference_date: date | None = None,
        news_display: int | None = None,
    ) -> CollectionResult:
        target_date = reference_date or date.today()
        display = news_display or settings.naver_news_display
        market_batch = await asyncio.to_thread(
            self.collect_market_quotes,
            sector=sector,
            reference_date=target_date,
        )
        news_batch = await self.collect_news_articles(
            sector=sector,
            reference_date=target_date,
            display=display,
        )

        market_metric_count = await self.save_market_quotes(market_batch)
        news_article_count = await self.save_news_articles(news_batch)

        return CollectionResult(
            sector=sector,
            reference_date=target_date,
            market_metric_count=market_metric_count,
            news_article_count=news_article_count,
        )

    def collect_market_quotes(
        self,
        *,
        sector: SectorCode,
        reference_date: date,
    ) -> NormalizedMarketQuoteBatch:
        quotes = self._yfinance_client.fetch_sector_quotes(sector)
        return NormalizedMarketQuoteBatch(
            sector=sector,
            reference_date=reference_date,
            quotes=[_normalize_market_quote(quote) for quote in quotes],
        )

    async def collect_news_articles(
        self,
        *,
        sector: SectorCode,
        reference_date: date,
        display: int,
    ) -> NormalizedNewsArticleBatch:
        articles = await self._naver_news_client.search_sector_news(
            sector,
            display=display,
        )
        return NormalizedNewsArticleBatch(
            sector=sector,
            reference_date=reference_date,
            articles=process_naver_news_articles(articles),
        )

    async def save_market_quotes(self, batch: NormalizedMarketQuoteBatch) -> int:
        saved_count = 0
        for quote in batch.quotes:
            for metric_name, metric_value in _iter_market_metrics(quote):
                await self._market_repository.upsert(
                    MarketMetric(
                        sector=batch.sector,
                        reference_date=batch.reference_date,
                        metric_name=metric_name,
                        metric_value=metric_value,
                        source=quote.source,
                    )
                )
                saved_count += 1
        return saved_count

    async def save_news_articles(self, batch: NormalizedNewsArticleBatch) -> int:
        saved_count = 0
        for article in batch.articles:
            saved_article = await self._news_repository.insert_if_new(
                NewsArticle(
                    sector=batch.sector,
                    reference_date=batch.reference_date,
                    title=article.title,
                    url=article.original_url or article.url,
                    source=article.source,
                    published_at=article.published_at,
                    summary=article.summary,
                    keywords=article.keywords,
                )
            )
            if saved_article is not None:
                saved_count += 1
        return saved_count


def _normalize_market_quote(quote: MarketQuote) -> NormalizedMarketQuote:
    return NormalizedMarketQuote(
        sector=quote.sector,
        ticker=quote.ticker,
        price=quote.price,
        change_percent=quote.change_percent,
        volume=quote.volume,
        source=quote.source,
    )


def _iter_market_metrics(quote: NormalizedMarketQuote) -> list[tuple[str, float]]:
    metrics: list[tuple[str, float]] = []
    if quote.price is not None:
        metrics.append((f"{quote.ticker}:price", quote.price))
    if quote.change_percent is not None:
        metrics.append((f"{quote.ticker}:change_percent", quote.change_percent))
    if quote.volume is not None:
        metrics.append((f"{quote.ticker}:volume", float(quote.volume)))
    return metrics
