import json
import time

import aiosqlite
from cachetools import LRUCache

from app.settings import settings


class CacheService:
    def __init__(self) -> None:
        self._l1: LRUCache = LRUCache(maxsize=settings.cache_l1_size)
        self._db_path = str(settings.sqlite_path)
        self._hits = 0
        self._misses = 0

    async def init_db(self) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    patch_version TEXT NOT NULL,
                    expires_at REAL NOT NULL
                )
                """
            )
            await db.execute("DELETE FROM cache WHERE expires_at < ?", (time.time(),))
            await db.commit()

    async def get(self, key: str) -> dict | None:
        if key in self._l1:
            self._hits += 1
            return self._l1[key]

        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT data FROM cache WHERE key = ? AND expires_at > ?",
                (key, time.time()),
            ) as cursor:
                row = await cursor.fetchone()

        if row:
            self._hits += 1
            data = json.loads(row[0])
            self._l1[key] = data
            return data

        self._misses += 1
        return None

    async def put(self, key: str, value: dict, *, patch_version: str) -> None:
        self._l1[key] = value
        expires_at = time.time() + settings.cache_l2_ttl_days * 86400
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO cache (key, data, patch_version, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (key, json.dumps(value), patch_version, expires_at),
            )
            await db.commit()

    async def stats(self) -> dict:
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM cache WHERE expires_at > ?", (time.time(),)) as cursor:
                row = await cursor.fetchone()
                l2_size = row[0] if row else 0

        total = self._hits + self._misses
        hit_rate = round(self._hits / total, 4) if total > 0 else 0.0
        return {
            "l1_size": len(self._l1),
            "l2_size": l2_size,
            "hit_rate_session": hit_rate,
        }


cache_service = CacheService()
