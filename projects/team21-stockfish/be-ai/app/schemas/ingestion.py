from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import SectorCode


class NormalizedMarketQuote(BaseModel):
    sector: SectorCode
    ticker: str
    price: float | None = None
    change_percent: float | None = None
    volume: int | None = None
    source: str


class NormalizedMarketQuoteBatch(BaseModel):
    sector: SectorCode
    reference_date: date
    quotes: list[NormalizedMarketQuote] = Field(default_factory=list)


class NormalizedNewsArticle(BaseModel):
    sector: SectorCode
    title: str
    url: str
    original_url: str | None = None
    summary: str
    published_at: datetime | None = None
    source: str
    keywords: list[str] = Field(default_factory=list)


class NormalizedNewsArticleBatch(BaseModel):
    sector: SectorCode
    reference_date: date
    articles: list[NormalizedNewsArticle] = Field(default_factory=list)
