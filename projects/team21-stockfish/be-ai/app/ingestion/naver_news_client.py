from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from html import unescape
import re
from typing import Any, Literal

import httpx

from app.core.config import settings
from app.models.enums import SectorCode


NAVER_NEWS_ENDPOINT = "https://openapi.naver.com/v1/search/news.json"
NAVER_NEWS_SOURCE = "naver_news"
NAVER_NEWS_SORTS = {"sim", "date"}

SECTOR_NEWS_QUERIES: Mapping[SectorCode, tuple[str, ...]] = {
    SectorCode.SEMICONDUCTOR: (
        "KOSPI 반도체",
        "삼성전자",
        "SK하이닉스",
    ),
    SectorCode.PHARMACEUTICAL: (
        "KOSPI 제약",
        "KOSPI 바이오",
        "셀트리온",
        "삼성바이오로직스",
    ),
}

_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"\s+")


class NaverNewsClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class NaverNewsArticle:
    sector: SectorCode
    title: str
    link: str
    original_link: str | None
    description: str
    published_at: datetime | None
    source: str = NAVER_NEWS_SOURCE


class NaverNewsClient:
    def __init__(
        self,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        endpoint: str = NAVER_NEWS_ENDPOINT,
        sector_queries: Mapping[SectorCode, Sequence[str]] | None = None,
        timeout: float = 5.0,
    ) -> None:
        self._client_id = client_id or settings.naver_client_id
        self._client_secret = client_secret or settings.naver_client_secret
        self._endpoint = endpoint
        self._sector_queries = sector_queries or SECTOR_NEWS_QUERIES
        self._http_client = http_client or httpx.AsyncClient(timeout=timeout)
        self._owns_http_client = http_client is None

    async def __aenter__(self) -> "NaverNewsClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_http_client:
            await self._http_client.aclose()

    def get_queries_for_sector(self, sector: SectorCode) -> tuple[str, ...]:
        queries = self._sector_queries.get(sector)
        if queries is None:
            raise NaverNewsClientError(f"Unsupported sector: {sector}")
        return tuple(queries)

    def get_query_for_sector(self, sector: SectorCode) -> str:
        return self.get_queries_for_sector(sector)[0]

    async def search_sector_news(
        self,
        sector: SectorCode,
        *,
        display: int,
        start: int = 1,
        sort: Literal["sim", "date"] = "date",
    ) -> list[NaverNewsArticle]:
        articles: list[NaverNewsArticle] = []
        for query in self.get_queries_for_sector(sector):
            articles.extend(
                await self.search_news(
                    sector=sector,
                    query=query,
                    display=display,
                    start=start,
                    sort=sort,
                )
            )
        return _deduplicate_articles(articles)

    async def search_news(
        self,
        *,
        sector: SectorCode,
        query: str,
        display: int,
        start: int = 1,
        sort: Literal["sim", "date"] = "date",
    ) -> list[NaverNewsArticle]:
        client_id, client_secret = self._get_credentials()
        _validate_search_params(query=query, display=display, start=start, sort=sort)

        try:
            response = await self._http_client.get(
                self._endpoint,
                params={
                    "query": query,
                    "display": display,
                    "start": start,
                    "sort": sort,
                },
                headers={
                    "X-Naver-Client-Id": client_id,
                    "X-Naver-Client-Secret": client_secret,
                },
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            raise NaverNewsClientError(
                f"Naver news API returned HTTP {exc.response.status_code}: "
                f"{_read_error_message(exc.response)}"
            ) from exc
        except httpx.HTTPError as exc:
            raise NaverNewsClientError("Failed to call Naver news API") from exc
        except ValueError as exc:
            raise NaverNewsClientError("Naver news API returned invalid JSON") from exc

        if not isinstance(payload, Mapping):
            raise NaverNewsClientError("Naver news API returned invalid payload")

        items = payload.get("items")
        if not isinstance(items, list):
            raise NaverNewsClientError("Naver news API response is missing items")

        return [
            _parse_news_item(sector=sector, item=item)
            for item in items
            if isinstance(item, Mapping)
        ]

    def _get_credentials(self) -> tuple[str, str]:
        if not self._client_id or not self._client_secret:
            raise NaverNewsClientError(
                "NAVER_CLIENT_ID and NAVER_CLIENT_SECRET are required"
            )
        return self._client_id, self._client_secret


def _validate_search_params(
    *,
    query: str,
    display: int,
    start: int,
    sort: str,
) -> None:
    if not query.strip():
        raise NaverNewsClientError("Naver news query must not be empty")
    if not 1 <= display <= 100:
        raise NaverNewsClientError("Naver news display must be between 1 and 100")
    if not 1 <= start <= 1000:
        raise NaverNewsClientError("Naver news start must be between 1 and 1000")
    if sort not in NAVER_NEWS_SORTS:
        raise NaverNewsClientError("Naver news sort must be either sim or date")


def _parse_news_item(
    *,
    sector: SectorCode,
    item: Mapping[str, Any],
) -> NaverNewsArticle:
    link = _read_string(item, "link")
    original_link = _read_optional_string(item, "originallink")
    return NaverNewsArticle(
        sector=sector,
        title=_clean_html_text(_read_string(item, "title")),
        link=link,
        original_link=original_link,
        description=_clean_html_text(_read_string(item, "description")),
        published_at=_parse_pub_date(_read_optional_string(item, "pubDate")),
    )


def _deduplicate_articles(articles: list[NaverNewsArticle]) -> list[NaverNewsArticle]:
    seen_urls: set[str] = set()
    deduplicated_articles: list[NaverNewsArticle] = []
    for article in articles:
        article_key = article.original_link or article.link
        if article_key in seen_urls:
            continue
        seen_urls.add(article_key)
        deduplicated_articles.append(article)
    return deduplicated_articles


def _read_string(item: Mapping[str, Any], key: str) -> str:
    value = item.get(key)
    return value if isinstance(value, str) else ""


def _read_optional_string(item: Mapping[str, Any], key: str) -> str | None:
    value = _read_string(item, key).strip()
    return value or None


def _clean_html_text(value: str) -> str:
    without_tags = _HTML_TAG_PATTERN.sub("", value)
    unescaped = unescape(without_tags)
    return _WHITESPACE_PATTERN.sub(" ", unescaped).strip()


def _parse_pub_date(value: str | None) -> datetime | None:
    if value is None:
        return None

    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None


def _read_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text

    message = payload.get("errorMessage") or payload.get("message")
    return message if isinstance(message, str) else response.text
