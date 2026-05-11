import time

from fastapi import APIRouter

from app.rag.chroma_service import RAG_INDICES, count_chroma_collections
from app.settings import settings

router = APIRouter()

_startup_time = time.time()

def _count_rag_chunks() -> dict[str, int]:
    return count_chroma_collections(settings.chroma_path)


@router.get(
    "/health",
    summary="서버 상태 확인",
    description="""
서버와 Chroma RAG 인덱스의 현재 상태를 반환합니다.

- `status`: RAG 인덱스 중 하나라도 비어 있으면 `degraded`, 모두 정상이면 `ok`
- `rag_chunks`: 8개 인덱스(units, traits, items, augments, deck_templates, playbook, patch_summary, glossary)별 chunk 수
- `uptime_s`: 서버 기동 후 경과 시간(초)
""",
)
async def health():
    rag_chunks = _count_rag_chunks()
    status = "degraded" if any(rag_chunks[index] == 0 for index in RAG_INDICES) else "ok"
    return {
        "status": status,
        "patch_version": settings.patch_version,
        "rag_chunks": rag_chunks,
        "uptime_s": int(time.time() - _startup_time),
    }
