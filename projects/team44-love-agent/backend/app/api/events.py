from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.schemas.events import StreamEvent

router = APIRouter(prefix="/consultations", tags=["consultation-events"])


@router.get("/{consultation_id}/events")
async def stream_consultation_events(
    consultation_id: str,
    request: Request,
    after_sequence: int = 0,
) -> StreamingResponse:
    state = await request.app.state.store.get(consultation_id)
    if state is None:
        raise HTTPException(status_code=404, detail="consultation not found")

    async def event_generator():
        async for event in request.app.state.broker.subscribe(
            consultation_id,
            after_sequence=after_sequence,
        ):
            if await request.is_disconnected():
                break
            yield encode_sse(event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def encode_sse(event: StreamEvent) -> str:
    data = json.dumps(event.model_dump(mode="json"), ensure_ascii=False)
    return f"id: {event.sequence}\nevent: {event.event_type}\ndata: {data}\n\n"
