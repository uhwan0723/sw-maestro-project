from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Enum, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import SectorCode


def utc_now() -> datetime:
    return datetime.now(UTC)


class NewsArticle(Base):
    __tablename__ = "news_articles"

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
    title: Mapped[str] = mapped_column(String(300))
    url: Mapped[str] = mapped_column(String(500), unique=True)
    source: Mapped[str] = mapped_column(String(100))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    summary: Mapped[str | None] = mapped_column(Text)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
