"""화이트리스트 웹페이지 fetch + 본문 추출 도구.

이 도구는 검색으로 찾은 URL의 실제 본문을 읽어 `PageContent`로 반환한다.
Live Research에서 source-backed fact를 만들려면 snippet보다 page text가
강한 근거이므로, search 이후에는 가능한 한 fetch_page를 거친다.

보안/정책:
- `is_allowed_url()`로 도메인 whitelist와 robots.txt를 모두 검사한다.
- JS rendering은 하지 않는다. MVP에서는 정적 HTML/텍스트만 대상으로 한다.
"""

from __future__ import annotations

from html import unescape
from html.parser import HTMLParser

import httpx

from app.research.state import PageContent
from app.research.whitelist import is_allowed_url

from .base import USER_AGENT, ResearchToolError


MAX_HTML_CHARS = 2_000_000
MAX_TEXT_CHARS = 8_000


class _PageTextParser(HTMLParser):
    """HTML에서 title, published_at, 읽을 만한 text만 추출하는 parser."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str | None = None
        self.published_at: str | None = None
        self._title_parts: list[str] = []
        self._text_parts: list[str] = []
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr = {k.lower(): v or "" for k, v in attrs}
        if tag in {"script", "style", "noscript", "svg"}:
            # 스크립트/스타일은 본문 근거가 아니므로 skip depth로 완전히 제외한다.
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            self._capture_meta(attr)
        elif tag in {"p", "br", "li", "section", "article", "h1", "h2", "h3", "tr"}:
            # 주요 block 태그는 줄바꿈을 넣어 문장 분리 품질을 높인다.
            self._text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False
            title = " ".join(" ".join(self._title_parts).split())
            if title:
                self.title = title
        elif tag in {"p", "li", "section", "article", "h1", "h2", "h3", "tr"}:
            self._text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            self._title_parts.append(data)
            return
        cleaned = " ".join(data.split())
        if cleaned:
            self._text_parts.append(cleaned)
            self._text_parts.append(" ")

    def _capture_meta(self, attrs: dict[str, str]) -> None:
        """OG/meta 태그에서 제목과 게시 시각 후보를 가져온다."""
        key = (
            attrs.get("property")
            or attrs.get("name")
            or attrs.get("itemprop")
            or ""
        ).lower()
        content = attrs.get("content", "").strip()
        if not content:
            return
        if key in {
            "article:published_time",
            "date",
            "datepublished",
            "publishdate",
            "pubdate",
        } and self.published_at is None:
            self.published_at = content
        elif key in {"og:title", "twitter:title"} and self.title is None:
            self.title = content

    @property
    def text(self) -> str:
        lines = [
            " ".join(line.split())
            for line in "".join(self._text_parts).splitlines()
        ]
        return "\n".join(line for line in lines if line)


def _extract_text(html: str) -> tuple[str | None, str | None, str]:
    """HTML을 PageContent에 필요한 최소 필드로 압축한다."""
    parser = _PageTextParser()
    parser.feed(html[:MAX_HTML_CHARS])
    return parser.title, parser.published_at, unescape(parser.text)[:MAX_TEXT_CHARS]


async def fetch_page(url: str) -> PageContent:
    """whitelist URL을 가져와 JS 렌더링 없이 읽을 수 있는 텍스트를 추출한다."""
    if not await is_allowed_url(url, check_robots=True):
        raise ResearchToolError(f"url_not_allowed_or_robots_blocked: {url}")

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=8.0,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html, text/plain;q=0.9"},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if "text/plain" in content_type:
        # robots.txt나 일부 문서는 plain text로 내려올 수 있다.
        title = None
        published_at = None
        text = response.text[:MAX_TEXT_CHARS]
    else:
        title, published_at, text = _extract_text(response.text)

    if not text.strip():
        # 빈 본문은 downstream fact 추출에 도움이 되지 않으므로 실패로 처리한다.
        raise ResearchToolError(f"empty_page_text: {url}")

    return PageContent(
        url=str(response.url),
        title=title,
        text=text,
        published_at=published_at,
    )
