from fastapi import APIRouter, Header, HTTPException

from app.services.cache import cache_service
from app.settings import settings

router = APIRouter()


@router.get(
    "/_internal/cache-stats",
    summary="캐시 통계 (관리자 전용)",
    description="""
L1/L2 캐시 현황을 반환합니다.

`X-Admin-Token` 헤더에 관리자 토큰을 포함해야 합니다 (`.env`의 `ADMIN_TOKEN`).

- `l1_size`: 현재 메모리 LRU 캐시 항목 수
- `l2_size`: SQLite 유효 캐시 항목 수 (만료 제외)
- `hit_rate_session`: 서버 기동 이후 누적 캐시 히트율
""",
    include_in_schema=True,
)
async def cache_stats(x_admin_token: str | None = Header(default=None)):
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return await cache_service.stats()
