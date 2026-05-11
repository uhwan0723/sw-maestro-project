"""전예준 영역 — 뉴스 모듈.

이 파일은 BE 코어가 정의한 시그니처와 스텁만 들어 있다. 예준은 본문을
NewsAPI(또는 네이버 뉴스 검색 API) 호출 + 중복 제거 + LLM 한 줄 요약으로 교체한다.

규칙:
- 반환 타입은 반드시 `list[NewsResult]`(`app.schemas.news`).
- 실패 시 `NewsError`(`app.core.errors`)를 raise. HTTPException 던지지 말 것.
- LLM 한 줄 요약이 필요하면 `app.core.llm.get_llm()`을 import해서 사용.
"""
from datetime import UTC, datetime

from app.core.config import get_settings
from app.core.errors import NewsError, LLMError
from app.core.llm import get_llm
from app.schemas.news import NewsItem, NewsResult

import html
import re
from email.utils import parsedate_to_datetime
from typing import Any
import httpx
import asyncio

NAVER_NEWS_ENDPOINT = "https://openapi.naver.com/v1/search/news.json"
HTTP_TIMEOUT = 5.0

_TAG_RE = re.compile(r"<[^>]+>")
_HANGUL_RE = re.compile(r"[가-힣]")

_SUMMARY_SYSTEM_PROMPT = (
    "너는 뉴스 한 줄 요약 도우미다. "
    "사용자가 제공한 뉴스의 제목과 본문 일부를 보고 한국어로 한 문장 요약을 만들어라.\n"
    "규칙:\n"
    "- 한 문장, 60자 이내.\n"
    "- 사실만 전달하고 정치적 평가나 추측은 하지 않는다.\n"
    "- 따옴표나 이모지를 쓰지 않는다.\n"
    "- 요약 본문만 출력한다. 머리말이나 부연 설명을 붙이지 않는다."
)

# --- 응답 정리 헬퍼 ------------------------------------------------------------

def _clean_html(text: str) -> str:
    """네이버 응답의 <b> 태그와 HTML 엔티티(&quot; 등)를 제거한다."""
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    return text.strip()


def _parse_pubdate(raw: str) -> datetime:
    """네이버 pubDate(RFC 822) → timezone-aware datetime."""
    try:
        return parsedate_to_datetime(raw)
    except (TypeError, ValueError) as exc:
        raise NewsError(f"발행일 파싱 실패: {raw!r}") from exc


def _to_news_item(raw: dict[str, Any], summary: str) -> NewsItem:
    """네이버 응답 item 1개 + 미리 만든 summary → NewsItem."""
    try:
        title = _clean_html(raw["title"])
        url = raw.get("originallink") or raw["link"]
        published_at = _parse_pubdate(raw["pubDate"])
    except KeyError as exc:
        raise NewsError(f"네이버 응답에 필수 필드 누락: {exc}") from exc

    return NewsItem(
        title=title,
        summary=summary,
        url=url,
        published_at=published_at,
    )

def _title_tokens(title: str) -> set[str]:
    """제목을 비교용 단어 집합으로 분해. 1글자 토큰은 버림."""
    cleaned = re.sub(r"[^\w가-힣]+", " ", title.lower())
    return {tok for tok in cleaned.split() if len(tok) >= 2}

def _is_similar(a: set[str], b: set[str], threshold: float = 0.3) -> bool:
    """Jaccard 유사도가 threshold 이상이면 True."""
    if not a or not b:
        return False
    return len(a & b) / len(a | b) >= threshold

def _is_korean_article(title: str, description: str = "", min_ratio: float = 0.2) -> bool:
    """제목+본문에서 한글 비율이 min_ratio 이상이면 한국어 기사로 판단."""
    text = f"{title} {description}"
    if not text.strip():
        return False
    hangul_count = len(_HANGUL_RE.findall(text))
    # 공백 제외한 전체 글자 수 기준
    total = len(re.sub(r"\s", "", text))
    if total == 0:
        return False
    return (hangul_count / total) >= min_ratio

def _dedupe_raw_items(raw_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """제목 유사도 기준으로 중복 제거. 입력 순서 유지."""
    seen_token_sets: list[set[str]] = []
    result: list[dict[str, Any]] = []

    for item in raw_items:
        title = _clean_html(item.get("title", ""))
        tokens = _title_tokens(title)

        if not tokens:
            continue
        if any(_is_similar(tokens, seen) for seen in seen_token_sets):
            continue

        seen_token_sets.append(tokens)
        result.append(item)

    return result

async def _build_news_result(
    http_client: httpx.AsyncClient,
    llm_client: "LLMClient",
    category: str,
    limit: int,
) -> NewsResult | None:
    """카테고리 하나 처리: API 호출 → 중복 제거 → LLM 요약 → NewsItem 변환."""
    display = min(limit * 3, 30)
    raw_items = await _fetch_naver_news(http_client, category, display)

    korean_items = [
        item for item in raw_items
        if _is_korean_article(
            _clean_html(item.get("title", "")),
            _clean_html(item.get("description", "")),
        )
    ]

    deduped = _dedupe_raw_items(korean_items)[:limit]
    if not deduped:
        return None

    # 요약 입력 준비 (제목/본문 정리는 여기서)
    titles = [_clean_html(raw["title"]) for raw in deduped]
    descriptions = [_clean_html(raw.get("description", "")) for raw in deduped]

    # 한 카테고리 내 요약은 병렬로
    summary_tasks = [
        _summarize_item(llm_client, t, d)
        for t, d in zip(titles, descriptions, strict=True)
    ]
    summaries = await asyncio.gather(*summary_tasks)

    items: list[NewsItem] = []
    for raw, summary in zip(deduped, summaries, strict=True):
        try:
            items.append(_to_news_item(raw, summary))
        except NewsError:
            continue  # 개별 아이템 실패는 스킵

    if not items:
        return None
    return NewsResult(category=category, items=items)

async def _summarize_item(client: "LLMClient", title: str, description: str) -> str:
    """제목과 본문 일부를 받아 한 줄 요약 생성. 실패 시 description으로 폴백."""
    user_prompt = f"제목: {title}\n본문: {description}"
    try:
        summary = await client.generate_text(
            system=_SUMMARY_SYSTEM_PROMPT,
            user=user_prompt,
            temperature=0.2,
            max_tokens=120,
        )
    except LLMError:
        # 폴백: description의 첫 문장 정도만 잘라서 사용
        return _fallback_summary(description)

    summary = summary.strip().strip('"').strip("'")
    return summary or _fallback_summary(description)


def _fallback_summary(description: str) -> str:
    """LLM 실패 시 description에서 첫 문장 추출."""
    if not description:
        return ""
    # 첫 마침표/줄바꿈 기준으로 자르고, 너무 길면 잘라냄
    first = re.split(r"[.。\n]", description, maxsplit=1)[0].strip()
    return first[:80] + ("…" if len(first) > 80 else "")


# --- 외부 API 호출 -------------------------------------------------------------


async def _fetch_naver_news(
    client: httpx.AsyncClient,
    query: str,
    display: int,
) -> list[dict[str, Any]]:
    """네이버 뉴스 검색 API를 호출하고 items 리스트를 반환한다."""
    params = {"query": query, "display": display, "sort": "sim"}

    try:
        resp = await client.get(NAVER_NEWS_ENDPOINT, params=params)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        raise NewsError(f"네이버 뉴스 API 호출 실패({query}): {exc}") from exc
    except ValueError as exc:
        raise NewsError(f"네이버 뉴스 API 응답 파싱 실패({query}): {exc}") from exc

    items = data.get("items")
    if not isinstance(items, list):
        raise NewsError(f"네이버 뉴스 API 응답 형식 이상({query})")
    return items


async def fetch_news(categories: list[str], limit: int = 5) -> list[NewsResult]:
    if not categories:
        raise NewsError("categories가 비어 있음")

    settings = get_settings()
    client_id = settings.naver_client_id
    client_secret = settings.naver_client_secret
    if not client_id or not client_secret:
        raise NewsError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 미설정")

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }

    try:
        llm_client = get_llm()
    except LLMError as exc:
        raise NewsError(f"LLM 클라이언트 초기화 실패: {exc}") from exc

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, headers=headers) as http_client:
        tasks = [
            _build_news_result(http_client, llm_client, cat, limit)
            for cat in categories
        ]
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)

    results: list[NewsResult] = []
    errors: list[str] = []
    for category, outcome in zip(categories, outcomes, strict=True):
        if isinstance(outcome, NewsError):
            errors.append(f"{category}: {outcome}")
        elif isinstance(outcome, Exception):
            # 예상 못한 예외 — 일단 기록하고 넘김
            errors.append(f"{category}: {type(outcome).__name__}: {outcome}")
        elif outcome is not None:
            results.append(outcome)

    if not results:
        detail = " / ".join(errors) if errors else "모든 카테고리 결과 없음"
        raise NewsError(f"뉴스 결과 없음: {detail}")

    return results


def _stub_news(categories: list[str], limit: int = 5) -> list[NewsResult]:
    """개발/테스트용 더미 데이터. 예준 모듈 완성 전 BE 검증에만 사용."""
    now = datetime.now(UTC)
    return [
        NewsResult(
            category=category,
            items=[
                NewsItem(
                    title=f"[{category}] 더미 헤드라인 {i + 1}",
                    summary=f"{category} 관련 한 줄 요약 {i + 1}",
                    url=f"https://example.com/{category.lower()}/{i + 1}",
                    published_at=now,
                )
                for i in range(min(3, limit))
            ],
        )
        for category in categories
    ]


from dotenv import load_dotenv

async def main():
    results = await fetch_news(["IT", "경제", "사회"], limit=5)
    for r in results:
        print(f"\n=== {r.category} ===")
        for item in r.items:
            print(f"제목 : {item.title}")
            print(f"요약 : {item.summary}")
            print(f"원문 기사 : {item.url}")
            print(f"발행 시각 : {item.published_at}")


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())

