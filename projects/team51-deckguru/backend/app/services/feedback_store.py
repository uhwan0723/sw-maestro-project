from datetime import datetime, timezone

import aiosqlite

from app.schemas.api import FeedbackRequest
from app.settings import settings


class FeedbackStore:
    def __init__(self) -> None:
        self._db_path = str(settings.sqlite_path)

    async def init_db(self) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    rating INTEGER NOT NULL,
                    comment TEXT,
                    deck_clicked TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            await db.commit()

    async def save(self, req: FeedbackRequest) -> None:
        created_at = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO feedback (request_id, rating, comment, deck_clicked, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (req.request_id, req.rating, req.comment, req.deck_clicked, created_at),
            )
            await db.commit()


feedback_store = FeedbackStore()
