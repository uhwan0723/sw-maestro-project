"""Live Research 도구 결과용 SQLite 캐시.

외부 검색/페이지 결과는 시점에 따라 바뀔 수 있다. 같은 입력으로 다시 실행했을
때 다른 결과가 나오면 디버깅과 회귀 테스트가 어려우므로, 도구 결과를 7일간
raw JSON 형태로 저장한다.

캐시 key는 `(tool, tool_input)`을 정렬된 JSON으로 만든 뒤 sha256 해시한다.
예: `web_search + {"query": "...", "k": 5}`
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any


DEFAULT_TTL_S = 7 * 24 * 60 * 60


def _backend_dir() -> Path:
    """backend/ 디렉토리 경로."""
    return Path(__file__).resolve().parents[2]


def _cache_path() -> Path:
    """캐시 DB 파일 위치. 테스트에서는 RESEARCH_CACHE_PATH로 바꿀 수 있다."""
    return Path(
        os.getenv(
            "RESEARCH_CACHE_PATH",
            str(_backend_dir() / "data" / "research_cache.sqlite3"),
        )
    )


def _cache_key(tool: str, tool_input: dict[str, Any]) -> str:
    """도구 이름과 입력을 안정적인 해시 key로 변환한다."""
    raw = json.dumps(
        {"tool": tool, "tool_input": tool_input},
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _connect() -> sqlite3.Connection:
    """SQLite 연결을 열고 필요한 테이블을 보장한다."""
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS research_cache (
            key TEXT PRIMARY KEY,
            tool TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at REAL NOT NULL,
            expires_at REAL NOT NULL
        )
        """
    )
    return conn


def _get(tool: str, tool_input: dict[str, Any]) -> dict[str, Any] | list[Any] | None:
    """동기 SQLite cache read."""
    key = _cache_key(tool, tool_input)
    now = time.time()
    with _connect() as conn:
        row = conn.execute(
            "SELECT payload FROM research_cache WHERE key = ? AND expires_at > ?",
            (key, now),
        ).fetchone()
    if row is None:
        return None
    return json.loads(row[0])


def _set(
    tool: str,
    tool_input: dict[str, Any],
    payload: dict[str, Any] | list[Any],
    *,
    ttl_s: int = DEFAULT_TTL_S,
) -> None:
    """동기 SQLite cache write."""
    key = _cache_key(tool, tool_input)
    now = time.time()
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO research_cache
            (key, tool, payload, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (key, tool, encoded, now, now + ttl_s),
        )
        conn.commit()


async def get_cached_json(
    tool: str,
    tool_input: dict[str, Any],
) -> dict[str, Any] | list[Any] | None:
    """비동기 루프를 막지 않도록 thread에서 cache read를 실행한다."""
    return await asyncio.to_thread(_get, tool, tool_input)


async def set_cached_json(
    tool: str,
    tool_input: dict[str, Any],
    payload: dict[str, Any] | list[Any],
    *,
    ttl_s: int = DEFAULT_TTL_S,
) -> None:
    """비동기 루프를 막지 않도록 thread에서 cache write를 실행한다."""
    await asyncio.to_thread(_set, tool, tool_input, payload, ttl_s=ttl_s)
