import sqlite3
from datetime import datetime

DB_PATH = "calendar.db"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            description TEXT,
            start_time  TEXT NOT NULL,
            end_time    TEXT,
            category    TEXT,
            synced_at   TEXT
        );
        CREATE TABLE IF NOT EXISTS reminders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id    TEXT NOT NULL REFERENCES events(id),
            remind_at   TEXT NOT NULL,
            message     TEXT NOT NULL,
            is_sent     INTEGER NOT NULL DEFAULT 0,
            created_by  TEXT NOT NULL DEFAULT 'ai'
        );
    """)
    conn.commit()
    conn.close()


def save_event(event: dict):
    conn = _connect()
    conn.execute("""
        INSERT INTO events (id, title, description, start_time, end_time, category, synced_at)
        VALUES (:id, :title, :description, :start_time, :end_time, :category, :synced_at)
        ON CONFLICT(id) DO UPDATE SET
            title=excluded.title,
            description=excluded.description,
            start_time=excluded.start_time,
            end_time=excluded.end_time,
            category=excluded.category,
            synced_at=excluded.synced_at
    """, {
        "id": event["id"],
        "title": event["title"],
        "description": event.get("description"),
        "start_time": event["start_time"],
        "end_time": event.get("end_time"),
        "category": event.get("category"),
        "synced_at": event.get("synced_at", datetime.now().isoformat()),
    })
    conn.commit()
    conn.close()


def delete_ai_reminders(event_id: str):
    conn = _connect()
    conn.execute(
        "DELETE FROM reminders WHERE event_id = ? AND created_by = 'ai'",
        (event_id,)
    )
    conn.commit()
    conn.close()


def save_reminders(reminders: list[dict]):
    conn = _connect()
    for r in reminders:
        conn.execute("""
            INSERT INTO reminders (event_id, remind_at, message, is_sent, created_by)
            VALUES (:event_id, :remind_at, :message, :is_sent, :created_by)
        """, {
            "event_id": r["event_id"],
            "remind_at": r["remind_at"],
            "message": r["message"],
            "is_sent": r.get("is_sent", 0),
            "created_by": r.get("created_by", "ai"),
        })
    conn.commit()
    conn.close()


def get_all_events() -> list[dict]:
    conn = _connect()
    rows = conn.execute("SELECT * FROM events ORDER BY start_time").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_reminders_for_event(event_id: str) -> list[dict]:
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM reminders WHERE event_id = ? ORDER BY remind_at",
        (event_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_reminder(reminder_id: int, remind_at: str):
    conn = _connect()
    conn.execute(
        "UPDATE reminders SET remind_at = ?, is_sent = 0, created_by = 'user' WHERE id = ?",
        (remind_at, reminder_id)
    )
    conn.commit()
    conn.close()


def add_reminder(event_id: str, remind_at: str, message: str):
    conn = _connect()
    conn.execute(
        "INSERT INTO reminders (event_id, remind_at, message, is_sent, created_by) VALUES (?, ?, ?, 0, 'user')",
        (event_id, remind_at, message)
    )
    conn.commit()
    conn.close()


def delete_reminder(reminder_id: int):
    conn = _connect()
    conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()


def get_unsent_reminders() -> list[dict]:
    conn = _connect()
    now = datetime.now().isoformat()
    rows = conn.execute(
        "SELECT r.*, e.title as event_title, e.category as event_category "
        "FROM reminders r JOIN events e ON r.event_id = e.id "
        "WHERE r.is_sent = 0 AND r.remind_at <= ? ORDER BY r.remind_at",
        (now,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_upcoming_reminders(limit: int = 10) -> list[dict]:
    conn = _connect()
    now = datetime.now().isoformat()
    rows = conn.execute(
        "SELECT r.id, r.remind_at, r.message, e.title as event_title, e.category as event_category "
        "FROM reminders r JOIN events e ON r.event_id = e.id "
        "WHERE r.is_sent = 0 AND r.remind_at > ? ORDER BY r.remind_at LIMIT ?",
        (now, limit)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def mark_as_sent(reminder_id: int):
    conn = _connect()
    conn.execute("UPDATE reminders SET is_sent = 1 WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("DB 초기화 완료")
