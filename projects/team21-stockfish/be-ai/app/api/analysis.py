from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.enums import SectorCode
from app.schemas.analysis import SectorAnalysisResponse
from app.services.analysis_service import AnalysisService


router = APIRouter(prefix="/sectors", tags=["analysis"])


@router.get("/{sector}/analysis", response_model=SectorAnalysisResponse)
async def get_sector_analysis(
    sector: SectorCode,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    refresh: bool = False,
) -> SectorAnalysisResponse:
    return await AnalysisService(session).get_today_sector_analysis(
        sector,
        refresh=refresh,
    )
