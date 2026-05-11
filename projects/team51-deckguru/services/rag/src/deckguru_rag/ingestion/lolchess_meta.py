import html
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from urllib.request import Request, urlopen


LOLCHESS_META_URL = "https://lolchess.gg/meta?hl=ko"
LOLCHESS_DECKS_URL = "https://lolchess.gg/decks?hl=ko"

LolchessMetaSource = Literal["meta", "decks"]


@dataclass(frozen=True)
class LolchessPageDocument:
    source: LolchessMetaSource
    url: str
    fetched_at: str
    next_data: dict[str, Any]

    @classmethod
    def create(
        cls,
        *,
        source: LolchessMetaSource,
        url: str,
        next_data: dict[str, Any],
    ) -> "LolchessPageDocument":
        return cls(
            source=source,
            url=url,
            fetched_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
            next_data=next_data,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def fetch_lolchess_meta_pages(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    documents = [
        _fetch_page(source="meta", url=LOLCHESS_META_URL),
        _fetch_page(source="decks", url=LOLCHESS_DECKS_URL),
    ]

    written: list[Path] = []
    for document in documents:
        path = output_dir / f"lolchess_{document.source}.json"
        path.write_text(
            json.dumps(document.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        written.append(path)
    return written


def _fetch_page(*, source: LolchessMetaSource, url: str) -> LolchessPageDocument:
    raw_html = _fetch_text(url)
    next_data = _extract_next_data(raw_html)
    return LolchessPageDocument.create(source=source, url=url, next_data=next_data)


def _fetch_text(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "DeckGuruRAG/0.1 (+https://github.com/asm-17th-ai51/deckguru)",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        },
    )
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def _extract_next_data(raw_html: str) -> dict[str, Any]:
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        raw_html,
    )
    if not match:
        raise ValueError("Could not find __NEXT_DATA__ script in Lolchess page.")
    return json.loads(html.unescape(match.group(1)))
