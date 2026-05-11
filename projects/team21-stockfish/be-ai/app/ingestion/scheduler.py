import logging
from datetime import date
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.db.session import async_session_factory
from app.models.enums import SECTOR_LABELS
from app.services.ingestion_service import DailyIngestionResult, IngestionService


DAILY_COLLECTION_JOB_ID = "daily_collection"
SCHEDULER_TIMEZONE = ZoneInfo("Asia/Seoul")

logger = logging.getLogger(__name__)


def create_daily_collection_scheduler(
    *,
    collection_hour: int | None = None,
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=SCHEDULER_TIMEZONE)
    scheduler.add_job(
        run_daily_collection_job,
        CronTrigger(
            hour=_resolve_collection_hour(collection_hour),
            minute=0,
            timezone=SCHEDULER_TIMEZONE,
        ),
        id=DAILY_COLLECTION_JOB_ID,
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=60 * 60,
    )
    return scheduler


async def run_daily_collection_job(
    *,
    reference_date: date | None = None,
) -> DailyIngestionResult:
    async with async_session_factory() as session:
        result = await IngestionService(session).run_daily_collection(
            reference_date=reference_date,
        )

    _log_daily_collection_result(result)
    return result


def _resolve_collection_hour(collection_hour: int | None) -> int:
    hour = settings.daily_collection_hour if collection_hour is None else collection_hour
    if not 0 <= hour <= 23:
        raise ValueError("daily collection hour must be between 0 and 23")
    return hour


def _log_daily_collection_result(result: DailyIngestionResult) -> None:
    if result.is_successful:
        logger.info(
            "Daily data collection succeeded for %s sectors on %s",
            len(result.sector_results),
            result.reference_date.isoformat(),
        )
    else:
        logger.warning(
            "Daily data collection finished with %s failed sectors on %s",
            len(result.failed_sectors),
            result.reference_date.isoformat(),
        )

    for sector_result in result.sector_results:
        logger.info(
            "Collected sector=%s market_metrics=%s news_articles=%s warnings=%s",
            sector_result.sector.value,
            sector_result.market_metric_count,
            sector_result.news_article_count,
            len(sector_result.warnings),
        )

    for failure in result.failed_sectors:
        logger.error(
            "Failed to collect sector=%s message=%s",
            SECTOR_LABELS.get(failure.sector, failure.sector.value),
            failure.message,
        )

    for warning in result.warnings:
        logger.warning(
            "Daily data collection warning code=%s message=%s",
            warning.code,
            warning.message,
        )
