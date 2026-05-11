from collections.abc import Sequence
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SectorCode
from app.models.market import MarketMetric


class MarketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(self, metric: MarketMetric) -> MarketMetric:
        statement = (
            insert(MarketMetric)
            .values(
                sector=metric.sector,
                reference_date=metric.reference_date,
                metric_name=metric.metric_name,
                metric_value=metric.metric_value,
                source=metric.source,
            )
            .on_conflict_do_update(
                index_elements=[
                    "sector",
                    "reference_date",
                    "metric_name",
                    "source",
                ],
                set_={"metric_value": metric.metric_value},
            )
        )
        await self.session.execute(statement)
        await self.session.flush()
        return await self.get_one(
            sector=metric.sector,
            reference_date=metric.reference_date,
            metric_name=metric.metric_name,
            source=metric.source,
        )

    async def get_one(
        self,
        *,
        sector: SectorCode,
        reference_date: date,
        metric_name: str,
        source: str,
    ) -> MarketMetric:
        statement = select(MarketMetric).where(
            MarketMetric.sector == sector,
            MarketMetric.reference_date == reference_date,
            MarketMetric.metric_name == metric_name,
            MarketMetric.source == source,
        )
        return (await self.session.execute(statement)).scalar_one()

    async def list_by_sector_and_date(
        self,
        *,
        sector: SectorCode,
        reference_date: date,
    ) -> Sequence[MarketMetric]:
        statement = select(MarketMetric).where(
            MarketMetric.sector == sector,
            MarketMetric.reference_date == reference_date,
        )
        return (await self.session.execute(statement)).scalars().all()
