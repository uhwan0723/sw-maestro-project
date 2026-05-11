"""Manual CLI for testing DeckGuru Live Research locally.

Usage examples:
  python scripts/manual_live_research.py
  python scripts/manual_live_research.py "latest TFT patch notes"
  python scripts/manual_live_research.py --search-only "site:teamfighttactics.leagueoflegends.com TFT patch notes"

This script is intentionally small and dependency-free. It lets you type a
query directly instead of editing a long PowerShell one-liner every time.
"""

from __future__ import annotations

import argparse
import asyncio
import os
from typing import Any

from langchain_upstage import ChatUpstage
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from app.research.api import run_live_research
from app.research.tools.web_search import web_search

# Load backend/.env so manual local tests use the same API keys as the app.
# The key value is never printed; we only show whether Solar is enabled.
load_dotenv()


class ManualAnswer(BaseModel):
    """Solar가 검색 결과를 바탕으로 만든 수동 테스트용 답변."""

    # 실제 API 응답 모델에는 없는 필드다. 이 스크립트에서 사람이 눈으로 확인하기
    # 좋게 Solar 합성 답변을 별도 구조로 묶기 위해서만 사용한다.
    answer: str = Field(max_length=1500)
    source_urls: list[str] = Field(default_factory=list, max_length=5)
    caveats: list[str] = Field(default_factory=list, max_length=3)


GENERIC_META_FACT_PATTERNS = (
    # 이런 문구는 "사이트 소개"에 가깝고, 특정 메타 덱을 추천할 근거가 아니다.
    # Solar가 이런 일반 문구만 보고 덱 이름을 지어내지 않도록 사전에 걸러낸다.
    "전적 검색 사이트",
    "추천 정보를 시즌 별로 확인",
    "browse data on every tft comp",
    "discover data on tft comps",
    "discover the best tft team compositions",
    "stats, analytics, match history",
    "tools you need to master",
)


def _parse_args() -> argparse.Namespace:
    """수동 테스트에서 사용할 CLI 옵션을 정의한다."""
    parser = argparse.ArgumentParser(description="Manual Live Research tester")
    parser.add_argument(
        "query",
        nargs="?",
        help="Search query or user question. If omitted, the script prompts for it.",
    )
    parser.add_argument(
        "--patch-version",
        default=os.getenv("LIVE_RESEARCH_PATCH_VERSION", "current"),
        help="Patch version to pass into Live Research. Default: env LIVE_RESEARCH_PATCH_VERSION or current.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=3,
        help="Maximum ReAct steps for full Live Research mode.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=35.0,
        help="Timeout seconds for full Live Research mode.",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Search result count for search-only mode.",
    )
    parser.add_argument(
        "--search-only",
        action="store_true",
        help="Only run DuckDuckGo whitelist search and print URLs.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full ResearchResult JSON in full mode.",
    )
    parser.add_argument(
        "--no-answer",
        action="store_true",
        help="Do not ask Solar to synthesize a final answer from the research facts.",
    )
    parser.add_argument(
        "--answer-timeout",
        type=float,
        default=45.0,
        help="Timeout seconds for Solar answer synthesis in manual mode.",
    )
    parser.add_argument(
        "--allow-on-robots-error",
        action="store_true",
        help="Allow page fetch when robots.txt cannot be loaded. Useful for local testing.",
    )
    return parser.parse_args()


def _query_from_args(args: argparse.Namespace) -> str:
    """인자로 받은 query가 없으면 터미널에서 직접 입력받는다."""
    query = args.query or input("Query: ").strip()
    if not query:
        raise SystemExit("Query is required.")
    return query


def _keywords(query: str) -> list[str]:
    # The Strategy Agent normally supplies extracted keywords. For manual tests
    # we use the first few tokens as a simple approximation.
    return query.split()[:5]


def _print_search_results(results: list[Any]) -> None:
    """--search-only 모드에서 whitelisted 검색 결과만 보기 좋게 출력한다."""
    if not results:
        print("No whitelisted search results.")
        return
    for index, item in enumerate(results, 1):
        print(f"{index}. {item.title}")
        print(f"   URL: {item.url}")
        if item.snippet:
            print(f"   Snippet: {item.snippet[:240]}")


def _research_payload(query: str, result: Any) -> str:
    """Solar 답변 합성에 넘길 Live Research 결과 JSON을 만든다.

    수동 확인용 prompt라서 전체 payload를 무제한으로 넣지 않고 12000자로 자른다.
    실제 API 경로에서는 이 함수가 호출되지 않는다.
    """
    return result.model_dump_json(indent=2)[:12000] + f"\n\nUser question: {query}"


def _source_urls(result: Any) -> list[str]:
    """답변 하단에 노출할 상위 source URL만 추린다."""
    return [str(source.url) for source in result.sources[:5]]


def _looks_generic_meta_fact(text: str) -> bool:
    """fact 문장이 특정 덱 근거가 아니라 사이트 소개 문구인지 판별한다."""
    lowered = text.lower()
    return any(pattern in lowered for pattern in GENERIC_META_FACT_PATTERNS)


def _has_specific_deck_evidence(result: Any) -> bool:
    """Solar가 덱 이름을 말해도 되는 수준의 구체 evidence가 있는지 확인한다."""
    for fact in result.web_facts:
        text = fact.text.strip()
        if not text or _looks_generic_meta_fact(text):
            continue
        lowered = text.lower()
        # 덱/조합/comp 같은 단어가 실제 fact에 있어야 "추천 답변"의 최소 근거로 본다.
        if any(token in lowered for token in ("deck", "comp", "덱", "조합", "빌드")):
            return True
    return False


def _insufficient_answer(query: str, result: Any) -> ManualAnswer:
    """구체 덱 evidence가 없을 때 Solar 호출 대신 반환하는 안전 답변."""
    source_urls = _source_urls(result)
    sources = "\n".join(f"- {url}" for url in source_urls) or "- (출처 없음)"
    return ManualAnswer(
        answer=(
            "현재 검색 결과에서 실제 덱 이름과 승률/순위 같은 구체 근거를 추출하지 "
            "못했습니다. 그래서 특정 덱을 '가장 좋다'고 단정하면 근거 없는 답변이 "
            "됩니다.\n\n"
            "확인된 것은 메타 덱/조합을 확인할 수 있는 출처 페이지입니다. 아래 "
            "페이지에서 현재 패치의 메타 덱 목록을 확인한 뒤, 해당 덱 이름을 다시 "
            "질문하면 더 정확하게 요약할 수 있습니다.\n"
            f"{sources}"
        ),
        source_urls=source_urls,
        caveats=[
            "검색된 페이지가 JavaScript 렌더링 기반이라 본문에서 덱 이름을 직접 추출하지 못했습니다.",
            "근거 없는 덱 이름 생성을 막기 위해 구체 추천을 보류했습니다.",
        ],
    )


def _message_content_text(content: Any) -> str:
    """LangChain message content가 문자열/블록 배열 중 무엇이든 문자열로 정규화한다."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    return str(content)


async def _synthesize_answer(query: str, result: Any, *, timeout_s: float) -> ManualAnswer | None:
    """검색/fact 결과를 Solar에 넣어 사용자가 읽을 최종 답변을 만든다."""
    api_key = os.getenv("UPSTAGE_API_KEY")
    if not api_key:
        # API 키가 없으면 Live Research 자체는 fallback으로 돌 수 있지만,
        # 수동 스크립트의 Solar Answer 섹션은 생략한다.
        return None
    if not result.web_facts and not result.sources:
        return None
    if not _has_specific_deck_evidence(result):
        # 근거가 약할 때 Solar에 넘기면 그럴듯한 덱 이름을 만들 가능성이 있으므로
        # LLM 호출 전 deterministic guard에서 멈춘다.
        return _insufficient_answer(query, result)

    system = """You are DeckGuru, a TFT coach.
Use only the provided live research facts and sources.
Answer the user's question directly in Korean.
If the facts do not contain exact deck names, say that the current live facts are insufficient
and recommend checking the strongest source pages instead of inventing deck names.
Include source URLs inline when you rely on them."""
    chat = ChatUpstage(
        model=os.getenv("UPSTAGE_MODEL_RESEARCH", "solar-mini"),
        api_key=api_key,
        temperature=0.0,
    )
    try:
        # 이 Solar 호출은 "수동 테스트 편의 기능"이다. 실제 backend API 응답은
        # ResearchResult만 반환하고, 최종 추천 문장은 Strategy Agent가 만든다.
        response = await asyncio.wait_for(
            chat.ainvoke(
                [
                    SystemMessage(content=system),
                    HumanMessage(content=_research_payload(query, result)),
                ]
            ),
            timeout=timeout_s,
        )
        return ManualAnswer(
            answer=_message_content_text(response.content).strip()[:1500],
            source_urls=_source_urls(result),
        )
    except Exception:
        return None


def _print_answer(answer: ManualAnswer | None) -> None:
    """수동 Solar 답변을 터미널에 출력한다."""
    if answer is None:
        return

    print("Solar Answer:")
    print(answer.answer)
    if answer.caveats:
        print()
        print("Caveats:")
        for caveat in answer.caveats:
            print(f"- {caveat}")
    if answer.source_urls:
        print()
        print("Answer Sources:")
        for index, url in enumerate(answer.source_urls, 1):
            print(f"{index}. {url}")
    print()


def _print_research_summary(result: Any) -> None:
    """ResearchResult의 핵심 필드를 사람이 확인하기 쉽게 요약 출력한다."""
    print(f"Solar: {'enabled' if os.getenv('UPSTAGE_API_KEY') else 'disabled'}")
    print(f"Steps: {result.research_steps}")
    print(f"Truncated: {result.truncated}")
    print(f"Domains: {', '.join(result.domains_visited) or '(none)'}")
    print(f"Warnings: {', '.join(result.warnings) or '(none)'}")
    print()

    if not result.web_facts:
        print("No facts extracted.")
    else:
        print("Facts:")
        for index, fact in enumerate(result.web_facts, 1):
            print(f"{index}. {fact.text}")
            print(f"   Source: {fact.source_url}")
            print(f"   Confidence: {fact.extraction_confidence}")

    if result.sources:
        print()
        print("Sources:")
        for index, source in enumerate(result.sources, 1):
            print(f"{index}. {source.title} | {source.url}")


async def _main() -> None:
    """CLI entrypoint.

    기본 full mode는 `run_live_research()`를 그대로 호출한다. `--search-only`는
    검색 whitelist가 제대로 동작하는지 빠르게 확인하기 위한 별도 경로다.
    """
    args = _parse_args()
    query = _query_from_args(args)

    # 수동 스크립트는 기능 확인 목적이므로 환경변수와 무관하게 Live Research를 켠다.
    os.environ["LIVE_RESEARCH_ENABLED"] = "true"
    if args.allow_on_robots_error:
        # 일부 로컬 네트워크 환경에서는 robots.txt fetch가 막힐 수 있다.
        # 이 옵션은 수동 테스트 편의용이며 운영 기본값은 차단이다.
        os.environ["RESEARCH_ALLOW_ON_ROBOTS_ERROR"] = "true"

    if args.search_only:
        print("Solar: not used in --search-only mode")
        results = await web_search(query, k=args.k)
        _print_search_results(results)
        return

    result = await run_live_research(
        "manual-live-research",
        question=query,
        extracted_keywords=_keywords(query),
        patch_version=args.patch_version,
        max_steps=args.max_steps,
        timeout_s=args.timeout,
    )

    if args.json:
        print(result.model_dump_json(indent=2))
    else:
        if not args.no_answer:
            answer = await _synthesize_answer(
                query,
                result,
                timeout_s=args.answer_timeout,
            )
            _print_answer(answer)
        _print_research_summary(result)


if __name__ == "__main__":
    asyncio.run(_main())
