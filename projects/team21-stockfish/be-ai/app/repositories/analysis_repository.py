from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import AnalysisResult
from app.models.enums import SectorCode


class AnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(self, analysis: AnalysisResult) -> AnalysisResult:
        statement = (
            insert(AnalysisResult)
            .values(
                sector=analysis.sector,
                reference_date=analysis.reference_date,
                trend_label=analysis.trend_label,
                confidence=analysis.confidence,
                beginner_summary=analysis.beginner_summary,
                key_evidence=analysis.key_evidence,
                sources=analysis.sources,
                caution=analysis.caution,
            )
            .on_conflict_do_update(
                index_elements=["sector", "reference_date"],
                set_={
                    "trend_label": analysis.trend_label,
                    "confidence": analysis.confidence,
                    "beginner_summary": analysis.beginner_summary,
                    "key_evidence": analysis.key_evidence,
                    "sources": analysis.sources,
                    "caution": analysis.caution,
                },
            )
        )
        await self.session.execute(statement)
        await self.session.flush()
        return await self.get_by_sector_and_date(
            sector=analysis.sector,
            reference_date=analysis.reference_date,
        )

    async def get_by_sector_and_date(
        self,
        *,
        sector: SectorCode,
        reference_date: date,
    ) -> AnalysisResult:
        statement = select(AnalysisResult).where(
            AnalysisResult.sector == sector,
            AnalysisResult.reference_date == reference_date,
        )
        return (await self.session.execute(statement)).scalar_one()

    async def get_optional_by_sector_and_date(
        self,
        *,
        sector: SectorCode,
        reference_date: date,
    ) -> AnalysisResult | None:
        statement = select(AnalysisResult).where(
            AnalysisResult.sector == sector,
            AnalysisResult.reference_date == reference_date,
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def update_payload(
        self,
        *,
        sector: SectorCode,
        reference_date: date,
        values: dict[str, Any],
    ) -> AnalysisResult:
        analysis = await self.get_by_sector_and_date(
            sector=sector,
            reference_date=reference_date,
        )
        for key, value in values.items():
            setattr(analysis, key, value)
        await self.session.flush()
        return analysis
