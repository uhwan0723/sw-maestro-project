"""Live Research의 외부 URL 접근 정책.

이 모듈은 외부 페이지를 읽기 전에 반드시 거쳐야 하는 안전장치다.

검사 순서:
1. scheme이 http/https인지 확인한다.
2. 도메인이 whitelist.yaml의 allowed_domains에 포함되는지 확인한다.
3. login/admin/api 같은 금지 path 조각이 있는지 확인한다.
4. fetch_page 단계에서는 robots.txt까지 확인한다.
"""

from __future__ import annotations

import os
import time
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
import yaml
from pydantic import BaseModel, Field

from app.schemas.shared import SourceKind

from .tools.base import USER_AGENT


class ResearchWhitelist(BaseModel):
    """whitelist.yaml의 구조를 검증하는 모델."""

    allowed_domains: list[str] = Field(default_factory=list)
    allowed_youtube_channels: list[str] = Field(default_factory=list)
    forbidden_keywords_in_url: list[str] = Field(default_factory=list)


_ROBOTS_CACHE: dict[str, tuple[float, RobotFileParser | None]] = {}
_ROBOTS_TTL_S = 24 * 60 * 60


def _default_path() -> Path:
    """기본 whitelist.yaml 위치."""
    return Path(__file__).with_name("whitelist.yaml")


@lru_cache(maxsize=4)
def load_whitelist(path: str | None = None) -> ResearchWhitelist:
    """whitelist.yaml을 읽고 Pydantic 모델로 검증한다.

    파일은 요청마다 다시 읽지 않도록 lru_cache를 사용한다. 테스트나 운영에서
    다른 파일을 쓰고 싶으면 `RESEARCH_WHITELIST_PATH`를 지정할 수 있다.
    """
    cfg_path = Path(path or os.getenv("RESEARCH_WHITELIST_PATH") or _default_path())
    if not cfg_path.exists():
        return ResearchWhitelist()
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    return ResearchWhitelist.model_validate(data)


def _normalize_domain(domain: str) -> str:
    """www.와 대소문자 차이를 제거해 도메인 비교를 안정화한다."""
    domain = domain.lower().strip().rstrip(".")
    return domain[4:] if domain.startswith("www.") else domain


def domain_from_url(url: str) -> str:
    """URL에서 비교 가능한 domain만 추출한다."""
    return _normalize_domain(urlparse(url).netloc.split("@")[-1].split(":")[0])


def is_allowed_domain(domain: str) -> bool:
    """도메인이 whitelist에 직접 포함되거나 하위 도메인인지 확인한다."""
    normalized = _normalize_domain(domain)
    for allowed in load_whitelist().allowed_domains:
        allowed_norm = _normalize_domain(allowed)
        if normalized == allowed_norm or normalized.endswith(f".{allowed_norm}"):
            return True
    return False


def is_forbidden_url(url: str) -> bool:
    """로그인/API/admin 같은 fetch 금지 URL 패턴을 차단한다."""
    lowered = url.lower()
    return any(
        keyword.lower() in lowered
        for keyword in load_whitelist().forbidden_keywords_in_url
    )


def is_allowed_url_by_whitelist(url: str) -> bool:
    """robots.txt를 제외한 빠른 whitelist 검사."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    if not parsed.netloc:
        return False
    return is_allowed_domain(parsed.netloc) and not is_forbidden_url(url)


def is_allowed_youtube_channel(channel_id: str | None) -> bool:
    """유튜브 채널 whitelist 검사.

    allowed_youtube_channels가 비어 있으면 MVP 개발 편의를 위해 모든 채널을
    허용한다. 운영에서 제한하려면 yaml에 채널 ID를 명시하면 된다.
    """
    allowed = load_whitelist().allowed_youtube_channels
    if not allowed:
        return True
    return bool(channel_id and channel_id in allowed)


async def _get_cached_robots(domain: str) -> RobotFileParser | None:
    """도메인별 robots.txt parser를 24시간 캐시한다."""
    now = time.time()
    cached = _ROBOTS_CACHE.get(domain)
    if cached and cached[0] > now:
        return cached[1]

    parser = await _fetch_robots(domain)
    _ROBOTS_CACHE[domain] = (now + _ROBOTS_TTL_S, parser)
    return parser


async def _fetch_robots(domain: str) -> RobotFileParser | None:
    """robots.txt를 가져와 RobotFileParser로 변환한다."""
    robots_url = f"https://{domain}/robots.txt"
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=5.0,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            response = await client.get(robots_url)
    except httpx.HTTPError:
        return None

    if response.status_code == 404:
        # robots.txt가 없으면 표준상 명시적 disallow가 없는 것으로 처리한다.
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse([])
        return parser
    if response.status_code >= 400:
        return None

    parser = RobotFileParser()
    parser.set_url(robots_url)
    parser.parse(response.text.splitlines())
    return parser


async def is_allowed_url(url: str, *, check_robots: bool = True) -> bool:
    """최종 URL 허용 여부.

    `web_search`는 빠른 필터링을 위해 whitelist만 보고, 실제 본문을 읽는
    `fetch_page`는 robots.txt까지 확인한다.
    """
    if not is_allowed_url_by_whitelist(url):
        return False
    if not check_robots:
        return True

    domain = domain_from_url(url)
    parser = await _get_cached_robots(domain)
    if parser is None:
        # robots.txt를 가져오지 못했을 때 기본은 차단이다. 운영 정책상 허용하려면
        # RESEARCH_ALLOW_ON_ROBOTS_ERROR=true로 명시해야 한다.
        return os.getenv("RESEARCH_ALLOW_ON_ROBOTS_ERROR", "false").lower() == "true"
    return parser.can_fetch(USER_AGENT, url)


def source_kind_for_url(url: str) -> SourceKind:
    """URL 도메인을 응답 Source의 source_kind로 분류한다."""
    domain = domain_from_url(url)
    if "leagueoflegends.com" in domain:
        return "patch_note_official"
    if domain in {"lolchess.gg", "tactics.tools", "metatft.com"}:
        return "meta_site"
    return "community_post"
