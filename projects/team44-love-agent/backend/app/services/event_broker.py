from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator

from app.schemas.events import EventType, StreamEvent


class EventBroker:
    """In-memory SSE event broker with per-consultation history."""

    def __init__(self) -> None:
        self._history: dict[str, list[StreamEvent]] = defaultdict(list)
        self._subscribers: dict[str, set[asyncio.Queue[StreamEvent]]] = defaultdict(set)
        self._sequences: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    async def publish(
        self,
        consultation_id: str,
        event_type: EventType,
        payload: dict,
    ) -> StreamEvent:
        async with self._lock:
            self._sequences[consultation_id] += 1
            event = StreamEvent(
                consultation_id=consultation_id,
                sequence=self._sequences[consultation_id],
                event_type=event_type,
                payload=payload,
            )
            self._history[consultation_id].append(event)
            subscribers = list(self._subscribers[consultation_id])

        for queue in subscribers:
            await queue.put(event)
        return event

    async def subscribe(
        self,
        consultation_id: str,
        *,
        after_sequence: int = 0,
    ) -> AsyncIterator[StreamEvent]:
        queue: asyncio.Queue[StreamEvent] = asyncio.Queue()
        async with self._lock:
            history = [
                event
                for event in self._history.get(consultation_id, [])
                if event.sequence > after_sequence
            ]
            terminal_in_history = any(_is_terminal(event) for event in history)
            if not terminal_in_history:
                self._subscribers[consultation_id].add(queue)

        try:
            for event in history:
                yield event
                if _is_terminal(event):
                    return

            while True:
                event = await queue.get()
                yield event
                if _is_terminal(event):
                    return
        finally:
            async with self._lock:
                self._subscribers[consultation_id].discard(queue)


def _is_terminal(event: StreamEvent) -> bool:
    return event.event_type == "completed"
