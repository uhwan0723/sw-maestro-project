import uuid
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.graph import graph
from app.api.sse import stream_graph_events


app = FastAPI(title="Legal AI Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    user_query: str = Field(min_length=1)
    session_id: Optional[str] = None
    history: list[dict] = Field(default_factory=list)


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.post("/chat")
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    inputs = {
        "user_query": req.user_query,
        "history": req.history,
        "session_id": session_id,
    }
    headers = {
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    return StreamingResponse(
        stream_graph_events(graph, inputs),
        media_type="text/event-stream",
        headers=headers,
    )


@app.post("/chat/sync")
async def chat_sync(req: ChatRequest):
    """비스트리밍 디버그용."""
    session_id = req.session_id or str(uuid.uuid4())
    inputs = {
        "user_query": req.user_query,
        "history": req.history,
        "session_id": session_id,
    }
    final = await graph.ainvoke(inputs)
    return JSONResponse(final)
