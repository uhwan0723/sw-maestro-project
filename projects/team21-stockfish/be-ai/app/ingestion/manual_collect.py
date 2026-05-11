import argparse
import asyncio
from datetime import date
import logging

from app.db.init import init_db
from app.ingestion.scheduler import run_daily_collection_job
from app.models.enums import SECTOR_LABELS
from app.services.ingestion_service import DailyIngestionResult


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    args = _parse_args()
    result = asyncio.run(_run(reference_date=args.date))
    _print_result(result)


async def _run(*, reference_date: date | None) -> DailyIngestionResult:
    await init_db()
    return await run_daily_collection_job(reference_date=reference_date)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manually collect daily KOSPI sector data once.",
    )
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=None,
        help="Collection reference date in YYYY-MM-DD format. Defaults to today.",
    )
    return parser.parse_args()


def _print_result(result: DailyIngestionResult) -> None:
    print(f"reference_date={result.reference_date.isoformat()}")
    print(f"successful={str(result.is_successful).lower()}")
    print(f"sector_results={len(result.sector_results)}")
    for sector_result in result.sector_results:
        sector_label = SECTOR_LABELS.get(
            sector_result.sector,
            sector_result.sector.value,
        )
        print(
            "sector="
            f"{sector_result.sector.value} "
            f"label={sector_label} "
            f"market_metrics={sector_result.market_metric_count} "
            f"news_articles={sector_result.news_article_count} "
            f"warnings={len(sector_result.warnings)}"
        )

    print(f"failed_sectors={len(result.failed_sectors)}")
    for failure in result.failed_sectors:
        sector_label = SECTOR_LABELS.get(failure.sector, failure.sector.value)
        print(
            "failure="
            f"{failure.sector.value} "
            f"label={sector_label} "
            f"message={failure.message}"
        )

    print(f"warnings={len(result.warnings)}")
    for warning in result.warnings:
        print(f"warning={warning.code} message={warning.message}")


if __name__ == "__main__":
    main()
