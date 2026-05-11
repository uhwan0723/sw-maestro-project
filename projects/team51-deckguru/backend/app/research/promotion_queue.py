"""Live Research fact를 향후 RAG 인덱싱 후보로 쌓는 큐.

Live Research에서 얻은 fact는 즉시 사용자 답변에 쓸 수는 있지만, 바로 정적
RAG 인덱스에 넣으면 잘못된 정보가 장기 기억처럼 남을 위험이 있다.

그래서 여기서는 `backend/data/promotion_queue.jsonl`에 append-only로 저장만
하고, 사람이 검토한 뒤 별도 ingest 파이프라인에서 RAG에 반영하도록 분리한다.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from app.schemas.shared import WebFact

from .state import utc_now_iso


def _backend_dir() -> Path:
    """backend/ 디렉토리 경로."""
    return Path(__file__).resolve().parents[2]


def _queue_path() -> Path:
    """promotion queue JSONL 파일 위치."""
    return Path(
        os.getenv(
            "PROMOTION_QUEUE_PATH",
            str(_backend_dir() / "data" / "promotion_queue.jsonl"),
        )
    )


def _append_lines(lines: list[str]) -> None:
    """동기 파일 append. asyncio.to_thread에서 호출된다."""
    path = _queue_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for line in lines:
            f.write(line)
            f.write("\n")


async def enqueue_facts(
    request_id: str,
    facts: list[WebFact],
    *,
    patch_version: str,
    linked_index: str = "deck_templates",
) -> int:
    """WebFact 목록을 JSONL 큐에 적재한다."""
    if not facts:
        return 0

    queued_at = utc_now_iso()
    lines = [
        # 한 줄이 하나의 검토 단위다. fact 원문, patch_version, 어떤 인덱스에
        # 연결될 후보인지(linked_index)를 함께 남긴다.
        json.dumps(
            {
                "queued_at": queued_at,
                "request_id": request_id,
                "fact": fact.model_dump(mode="json"),
                "patch_version": patch_version,
                "linked_index": linked_index,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        for fact in facts
    ]
    await asyncio.to_thread(_append_lines, lines)
    return len(lines)
