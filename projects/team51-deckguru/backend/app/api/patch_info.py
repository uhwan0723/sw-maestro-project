import json
import time
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter

from app.observability import elapsed_ms
from app.rag.chroma_service import resolve_chroma_path
from app.settings import settings

router = APIRouter()
logger = structlog.get_logger()

_PATCH_MANIFEST_CANDIDATES = [
    "deck_templates/current_patch.json",
    "patch_summary/current_patch.json",
]


def _load_last_updated() -> tuple[datetime | None, str | None]:
    processed_dir = resolve_chroma_path(settings.chroma_path).parent.parent / "processed"
    for candidate in _PATCH_MANIFEST_CANDIDATES:
        manifest = processed_dir / candidate
        if manifest.exists():
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
                raw = data.get("fetched_at") or data.get("last_updated")
                if raw:
                    return datetime.fromisoformat(raw.replace("Z", "+00:00")), candidate
                return None, candidate
            except Exception as exc:
                logger.warning(
                    "patch_info_manifest_read_failed",
                    stage="patch_info",
                    manifest=candidate,
                    error=str(exc),
                )
    return None, None


@router.get(
    "/patch-info",
    summary="현재 패치 정보",
    description="""
현재 서비스가 기준으로 삼는 패치 버전과 데이터 갱신 시각을 반환합니다.

- `patch_version`: 현재 패치 버전 (예: `17.2`)
- `last_updated`: RAG 데이터 마지막 갱신 시각 (ISO 8601)
- `warnings`: 패치 직후 데이터 부족 시 `data_may_be_insufficient_after_patch` 포함
""",
)
async def patch_info():
    started = time.perf_counter()
    logger.info(
        "patch_info_start",
        stage="patch_info",
        patch_version=settings.patch_version,
        chroma_path=str(resolve_chroma_path(settings.chroma_path)),
    )
    last_updated, manifest = _load_last_updated()
    warnings: list[str] = []

    if last_updated:
        now = datetime.now(timezone.utc)
        patch_age_days = (now - last_updated).days
        if patch_age_days >= 1:
            warnings.append("data_may_be_insufficient_after_patch")
        last_updated_str = last_updated.isoformat()
    else:
        last_updated_str = None
        warnings.append("data_may_be_insufficient_after_patch")

    logger.info(
        "patch_info_done",
        stage="patch_info",
        patch_version=settings.patch_version,
        manifest=manifest or "-",
        has_last_updated=last_updated is not None,
        warnings=warnings,
        latency_ms=elapsed_ms(started),
    )
    return {
        "patch_version": settings.patch_version,
        "last_updated": last_updated_str,
        "warnings": warnings,
    }
