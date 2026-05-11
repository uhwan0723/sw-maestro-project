from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import consultations, events
from app.services.event_broker import EventBroker
from app.services.llm_client import LLMClient, build_llm_client_from_env
from app.store.memory import MemoryStore
from app.workflow.graph import WorkflowRunner


def _cors_allow_origins() -> list[str]:
    configured = os.getenv("CORS_ALLOW_ORIGINS", "")
    if configured.strip():
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return [
        "http://localhost",
        "http://127.0.0.1",
    ]


def create_app(llm_client: LLMClient | None = None) -> FastAPI:
    app = FastAPI(title="Love Agent Consultation Backend")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_allow_origins(),
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1):\d+",
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    app.state.store = MemoryStore()
    app.state.broker = EventBroker()
    app.state.llm_client = llm_client or build_llm_client_from_env()
    app.state.workflow_runner = WorkflowRunner(
        app.state.store,
        app.state.broker,
        app.state.llm_client,
    )
    app.state.running_tasks = set()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(consultations.router)
    app.include_router(events.router)
    return app


app = create_app()
