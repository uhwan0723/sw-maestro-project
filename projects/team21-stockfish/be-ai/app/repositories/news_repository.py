from collections.abc import Sequence
from datetime import date
from typing import cast

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SectorCode
from app.models.news import NewsArticle


class NewsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert_if_new(self, article: NewsArticle) -> NewsArticle | None:
        statement = (
            insert(NewsArticle)
            .values(
                sector=article.sector,
                reference_date=article.reference_date,
                title=article.title,
                url=article.url,
                source=article.source,
                published_at=article.published_at,
                summary=article.summary,
                keywords=article.keywords,
            )
            .on_conflict_do_nothing(index_elements=["url"])
        )
        result = cast(CursorResult, await self.session.execute(statement))
        await self.session.flush()
        if result.rowcount == 0:
            return None
        return await self.get_by_url(article.url)

    async def get_by_url(self, url: str) -> NewsArticle:
        statement = select(NewsArticle).where(NewsArticle.url == url)
        return (await self.session.execute(statement)).scalar_one()

    async def list_by_sector_and_date(
        self,
        *,
        sector: SectorCode,
        reference_date: date,
    ) -> Sequence[NewsArticle]:
        statement = select(NewsArticle).where(
            NewsArticle.sector == sector,
            NewsArticle.reference_date == reference_date,
        )
        return (await self.session.execute(statement)).scalars().all()

    async def list_recent_by_sector(
        self,
        *,
        sector: SectorCode,
        limit: int,
    ) -> Sequence[NewsArticle]:
        statement = (
            select(NewsArticle)
            .where(NewsArticle.sector == sector)
            .order_by(
                NewsArticle.published_at.is_(None),
                NewsArticle.published_at.desc(),
                NewsArticle.created_at.desc(),
                NewsArticle.id.desc(),
            )
            .limit(limit)
        )
        return (await self.session.execute(statement)).scalars().all()
