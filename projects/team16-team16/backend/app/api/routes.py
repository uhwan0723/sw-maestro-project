from fastapi import APIRouter, HTTPException

from app.core.errors import BriefingError
from app.schemas.briefing import BriefingRequest, BriefingResponse
from app.services.briefing import build_briefing

router = APIRouter(prefix="/api/v1")


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/briefing", response_model=BriefingResponse)
async def create_briefing(request: BriefingRequest) -> BriefingResponse:
    try:
        return await build_briefing(request)
    except BriefingError as exc:
        # services에서 도메인 예외가 핸들링되지 않고 올라온 경우 (정상 경로면 잡혀 있어야 함)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
