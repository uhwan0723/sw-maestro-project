from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import SectorCode


def utc_now() -> datetime:
    return datetime.now(UTC)


class MarketMetric(Base):
    __tablename__ = "market_metrics"
    __table_args__ = (
        UniqueConstraint(
            "sector",
            "reference_date",
            "metric_name",
            "source",
            name="uq_market_metrics_sector_date_metric_source",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sector: Mapped[SectorCode] = mapped_column(
        Enum(
            SectorCode,
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        index=True,
    )
    reference_date: Mapped[date] = mapped_column(Date, index=True)
    metric_name: Mapped[str] = mapped_column(String(100))
    metric_value: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
