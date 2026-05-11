from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import SectorCode


def utc_now() -> datetime:
    return datetime.now(UTC)


class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    __table_args__ = (
        UniqueConstraint(
            "sector",
            "reference_date",
            name="uq_analysis_results_sector_date",
        ),
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="ck_analysis_results_confidence_range",
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
    trend_label: Mapped[str] = mapped_column(String(100))
    confidence: Mapped[float] = mapped_column(Float)
    beginner_summary: Mapped[str] = mapped_column(Text)
    key_evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    sources: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    caution: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
