from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.ingestion.scheduler import create_daily_collection_scheduler


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    scheduler = _start_daily_collection_scheduler()
    try:
        yield
    finally:
        if scheduler is not None and scheduler.running:
            scheduler.shutdown(wait=False)
            logger.info("Daily collection scheduler stopped")


def _start_daily_collection_scheduler() -> AsyncIOScheduler | None:
    if not settings.enable_daily_collection_scheduler:
        return None

    scheduler = create_daily_collection_scheduler()
    scheduler.start()
    logger.info(
        "Daily collection scheduler started at hour=%s timezone=Asia/Seoul",
        settings.daily_collection_hour,
    )
    return scheduler


def _configure_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )


app = FastAPI(lifespan=lifespan)
_configure_cors(app)
register_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")
