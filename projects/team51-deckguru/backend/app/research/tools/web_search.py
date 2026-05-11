"""DuckDuckGo HTML 검색 도구.

Live Research의 첫 단계는 보통 검색이다. 여기서는 DuckDuckGo HTML 결과를
파싱하고, `whitelist.py`의 도메인 정책을 통과한 URL만 `SearchResult`로
반환한다.

주의:
- 검색 결과 HTML 구조는 외부 서비스에 의존하므로 언제든 바뀔 수 있다.
- 실패하면 예외를 밖으로 던지지 않고 빈 목록을 반환해 graph가 다른 fallback을
  시도할 수 있게 한다.
"""

from __future__ import annotations

import asyncio
from html.parser import HTMLParser
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import httpx

from app.research.state import SearchResult
from app.research.whitelist import is_allowed_url_by_whitelist

from .base import USER_AGENT


_SEARCH_SEMAPHORE = asyncio.Semaphore(3)


class _DuckDuckGoParser(HTMLParser):
    """DuckDuckGo HTML result page에서 title/url/snippet만 추출하는 최소 parser."""

    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._current_link: dict[str, str] | None = None
        self._current_snippet: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k: v or "" for k, v in attrs}
        classes = attr.get("class", "")
        if tag == "a" and "result__a" in classes:
            # 검색 결과의 제목 링크. URL은 DuckDuckGo redirect URL일 수 있어
            # `_decode_ddg_url()`에서 원본 URL로 풀어낸다.
            self._current_link = {"title": "", "url": attr.get("href", "")}
        elif "result__snippet" in classes:
            self._current_snippet = []

    def handle_data(self, data: str) -> None:
        if self._current_link is not None:
            self._current_link["title"] += data
        if self._current_snippet is not None:
            self._current_snippet.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_link is not None:
            title = " ".join(self._current_link["title"].split())
            url = _decode_ddg_url(self._current_link["url"])
            if title and url:
                self.results.append({"title": title, "url": url, "snippet": ""})
            self._current_link = None
        elif self._current_snippet is not None and tag in {"a", "div"}:
            snippet = " ".join(" ".join(self._current_snippet).split())
            if snippet and self.results and not self.results[-1].get("snippet"):
                self.results[-1]["snippet"] = snippet
            self._current_snippet = None


def _decode_ddg_url(raw: str) -> str:
    """DuckDuckGo redirect URL이면 실제 목적지 URL을 꺼낸다."""
    if raw.startswith("//"):
        raw = "https:" + raw
    parsed = urlparse(raw)
    if "duckduckgo.com" in parsed.netloc:
        uddg = parse_qs(parsed.query).get("uddg")
        if uddg:
            return unquote(uddg[0])
    return raw


def _filter_results(raw: list[dict[str, str | None]], *, k: int) -> list[SearchResult]:
    """raw parser 결과에서 whitelist/중복/개수 제한을 적용한다."""
    results: list[SearchResult] = []
    seen: set[str] = set()
    for item in raw:
        url = str(item.get("url") or "")
        if not url or url in seen or not is_allowed_url_by_whitelist(url):
            continue
        title = str(item.get("title") or urlparse(url).netloc or "Untitled").strip()
        snippet = str(item.get("snippet") or item.get("content") or "").strip()
        published_at = item.get("published_at") or item.get("published_date")
        results.append(
            SearchResult(
                title=title,
                url=url,
                snippet=snippet[:1000],
                published_at=str(published_at) if published_at else None,
            )
        )
        seen.add(url)
        if len(results) >= k:
            break
    return results


async def _duckduckgo_search(query: str, *, k: int) -> list[SearchResult]:
    """DuckDuckGo HTML endpoint를 호출하고 SearchResult 목록으로 변환한다."""
    url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=5.0,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    parser = _DuckDuckGoParser()
    parser.feed(response.text)
    return _filter_results(parser.results, k=k)


async def web_search(query: str, *, k: int = 5) -> list[SearchResult]:
    """웹 검색을 실행하고 whitelist를 통과한 결과만 반환한다."""
    async with _SEARCH_SEMAPHORE:
        try:
            return await _duckduckgo_search(query, k=k)
        except (httpx.HTTPError, ValueError):
            # 검색 실패는 Live Research 전체 실패가 아니므로 빈 결과로 degrade한다.
            return []
