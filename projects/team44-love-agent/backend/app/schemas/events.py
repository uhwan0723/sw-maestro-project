from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from app.schemas.consultation import SchemaModel, utc_now_iso


EventType = Literal[
    "status_changed",
    "analysis_completed",
    "agent_message_added",
    "supervisor_note_added",
    "error_occurred",
    "completed",
]


class StreamEvent(SchemaModel):
    consultation_id: str
    sequence: int = Field(ge=1)
    event_type: EventType
    payload: dict[str, Any]
    emitted_at: str = Field(default_factory=utc_now_iso)
