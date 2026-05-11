from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from html import unescape
import re
from typing import Any

from app.ingestion.naver_news_client import NaverNewsArticle
from app.models.enums import SectorCode
from app.models.news import NewsArticle
from app.schemas.ingestion import NormalizedNewsArticle


MAX_SUMMARY_LENGTH = 300
MAX_KEYWORD_COUNT = 8

COMMON_KEYWORDS = (
    "KOSPI",
    "코스피",
    "주가",
    "증시",
    "실적",
    "영업이익",
    "수출",
    "외국인",
    "기관",
)

SECTOR_KEYWORDS: dict[SectorCode, tuple[str, ...]] = {
    SectorCode.SEMICONDUCTOR: (
        "반도체",
        "삼성전자",
        "SK하이닉스",
        "HBM",
        "D램",
        "DRAM",
        "낸드",
        "메모리",
        "파운드리",
        "AI",
    ),
    SectorCode.PHARMACEUTICAL: (
        "제약",
        "바이오",
        "셀트리온",
        "삼성바이오로직스",
        "유한양행",
        "한미약품",
        "임상",
        "신약",
        "허가",
        "CDMO",
        "바이오시밀러",
    ),
}

_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_TOKEN_PATTERN = re.compile(r"[가-힣A-Za-z0-9][가-힣A-Za-z0-9&.+_-]{1,}")
_STOPWORDS = {
    "naver",
    "news",
    "관련",
    "기자",
    "뉴스",
    "오늘",
    "이번",
    "대한",
    "통해",
    "기준",
    "위해",
    "에서",
    "으로",
    "하고",
    "했다",
    "된다",
    "있는",
    "지난",
    "올해",
}


@dataclass(frozen=True)
class ProcessedNewsArticle:
    sector: SectorCode
    title: str
    url: str
    original_url: str | None
    summary: str
    source: str
    published_at: datetime | None
    keywords: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "sector": self.sector.value,
            "title": self.title,
            "url": self.original_url or self.url,
            "summary": self.summary,
            "source": self.source,
            "published_at": (
                self.published_at.isoformat() if self.published_at else None
            ),
            "keywords": list(self.keywords),
        }


def process_naver_news_articles(
    articles: Iterable[NaverNewsArticle],
) -> list[NormalizedNewsArticle]:
    processed_articles = [
        _build_processed_article(
            sector=article.sector,
            title=article.title,
            url=article.link,
            original_url=article.original_link,
            summary=article.description,
            source=article.source,
            published_at=article.published_at,
        )
        for article in articles
    ]
    return [
        NormalizedNewsArticle(
            sector=article.sector,
            title=article.title,
            url=article.url,
            original_url=article.original_url,
            summary=article.summary,
            published_at=article.published_at,
            source=article.source,
            keywords=list(article.keywords),
        )
        for article in _deduplicate_processed_articles(processed_articles)
    ]


def process_saved_news_articles(
    articles: Iterable[NewsArticle],
) -> list[ProcessedNewsArticle]:
    processed_articles = [
        _build_processed_article(
            sector=article.sector,
            title=article.title,
            url=article.url,
            original_url=None,
            summary=article.summary or "",
            source=article.source,
            published_at=article.published_at,
        )
        for article in articles
    ]
    return _deduplicate_processed_articles(processed_articles)


def clean_news_text(value: str) -> str:
    without_tags = _HTML_TAG_PATTERN.sub("", value)
    unescaped = unescape(without_tags)
    return _WHITESPACE_PATTERN.sub(" ", unescaped).strip()


def extract_keywords(
    *,
    sector: SectorCode,
    title: str,
    summary: str,
    max_keywords: int = MAX_KEYWORD_COUNT,
) -> tuple[str, ...]:
    text = f"{title} {summary}"
    normalized_text = text.casefold()
    keywords: list[str] = []

    for keyword in (*SECTOR_KEYWORDS[sector], *COMMON_KEYWORDS):
        if keyword.casefold() in normalized_text:
            keywords.append(keyword)

    token_counts = Counter(
        token
        for token in _TOKEN_PATTERN.findall(text)
        if token.casefold() not in _STOPWORDS
    )
    for token, _ in token_counts.most_common():
        if not _has_keyword(keywords, token):
            keywords.append(token)
        if len(keywords) >= max_keywords:
            break

    return tuple(keywords[:max_keywords])


def _build_processed_article(
    *,
    sector: SectorCode,
    title: str,
    url: str,
    original_url: str | None,
    summary: str,
    source: str,
    published_at: datetime | None,
) -> ProcessedNewsArticle:
    cleaned_title = clean_news_text(title)
    cleaned_summary = _build_summary(title=cleaned_title, summary=summary)
    return ProcessedNewsArticle(
        sector=sector,
        title=cleaned_title,
        url=url.strip(),
        original_url=original_url.strip() if original_url else None,
        summary=cleaned_summary,
        source=source,
        published_at=published_at,
        keywords=extract_keywords(
            sector=sector,
            title=cleaned_title,
            summary=cleaned_summary,
        ),
    )


def _build_summary(*, title: str, summary: str) -> str:
    cleaned_summary = clean_news_text(summary)
    if not cleaned_summary:
        cleaned_summary = title
    if len(cleaned_summary) <= MAX_SUMMARY_LENGTH:
        return cleaned_summary
    return f"{cleaned_summary[: MAX_SUMMARY_LENGTH - 1].rstrip()}..."


def _deduplicate_processed_articles(
    articles: Iterable[ProcessedNewsArticle],
) -> list[ProcessedNewsArticle]:
    seen_keys: set[str] = set()
    deduplicated_articles: list[ProcessedNewsArticle] = []

    for article in articles:
        article_key = _deduplication_key(article)
        if article_key in seen_keys:
            continue
        seen_keys.add(article_key)
        deduplicated_articles.append(article)

    return deduplicated_articles


def _deduplication_key(article: ProcessedNewsArticle) -> str:
    if article.original_url:
        return article.original_url
    if article.url:
        return article.url
    return article.title.casefold()


def _has_keyword(keywords: Iterable[str], token: str) -> bool:
    normalized_token = token.casefold()
    return any(keyword.casefold() == normalized_token for keyword in keywords)
