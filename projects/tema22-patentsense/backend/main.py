from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.service import analyze_idea, stream_analysis_events, to_sse

app = FastAPI(
    title="PatentSense API",
    version="0.1.0",
    description="PatentSense agent wrapper API for Next.js migration",
)

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    idea_text: str = Field(..., min_length=5, description="사용자 아이디어 텍스트")


class AnalyzeResponse(BaseModel):
    report: str
    keywords: list[str]
    conflict_points: list[str]
    differentiators: list[Any]
    top_patents: list[dict[str, Any]]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> dict[str, Any]:
    return analyze_idea(request.idea_text)


@app.post("/v1/analyze/stream")
def analyze_stream(request: AnalyzeRequest) -> StreamingResponse:
    def event_stream():
        for event in stream_analysis_events(request.idea_text):
            yield to_sse(event)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
