from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Protocol

import httpx

from performation_agent.state import SearchQuery, SearchResult
from performation_agent.tools.cache import (
  DEFAULT_SEARCH_CACHE_TTL_SECONDS,
  cache_max_items,
  cache_ttl_seconds,
  get_or_set_cached,
)


TAVILY_SEARCH_URL = "https://api.tavily.com/search"
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_RESULTS_PER_QUERY = 3


class SearchProvider(Protocol):
  def search(self, search_query: SearchQuery, *, max_results: int) -> list[SearchResult]:
    ...


class TavilySearchProvider:
  def __init__(
    self,
    api_key: str,
    *,
    client: httpx.Client | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
  ) -> None:
    self._api_key = api_key
    self._injected_client = client
    self._timeout_seconds = timeout_seconds

  def search(self, search_query: SearchQuery, *, max_results: int) -> list[SearchResult]:
    if self._injected_client is not None:
      response = self._post(self._injected_client, search_query, max_results=max_results)
    else:
      with httpx.Client(timeout=self._timeout_seconds) as client:
        response = self._post(client, search_query, max_results=max_results)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
      return []
    return _normalize_tavily_results(payload, search_query, max_results=max_results)

  def _post(
    self,
    client: httpx.Client,
    search_query: SearchQuery,
    *,
    max_results: int,
  ) -> httpx.Response:
    return client.post(
      TAVILY_SEARCH_URL,
      headers={"Authorization": f"Bearer {self._api_key}"},
      json={
        "query": search_query["query"],
        "search_depth": "basic",
        "topic": "general",
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": False,
        "include_images": False,
      },
    )


class BraveSearchProvider:
  def __init__(
    self,
    api_key: str,
    *,
    client: httpx.Client | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
  ) -> None:
    self._api_key = api_key
    self._injected_client = client
    self._timeout_seconds = timeout_seconds

  def search(self, search_query: SearchQuery, *, max_results: int) -> list[SearchResult]:
    if self._injected_client is not None:
      response = self._get(self._injected_client, search_query, max_results=max_results)
    else:
      with httpx.Client(timeout=self._timeout_seconds) as client:
        response = self._get(client, search_query, max_results=max_results)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
      return []
    return _normalize_brave_results(payload, search_query, max_results=max_results)

  def _get(
    self,
    client: httpx.Client,
    search_query: SearchQuery,
    *,
    max_results: int,
  ) -> httpx.Response:
    return client.get(
      BRAVE_SEARCH_URL,
      headers={
        "Accept": "application/json",
        "X-Subscription-Token": self._api_key,
      },
      params={
        "q": search_query["query"],
        "count": max_results,
        "country": "KR",
        "search_lang": "ko",
        "safesearch": "moderate",
        "extra_snippets": "true",
      },
    )


def search_with_fallback(
  search_queries: list[SearchQuery],
  *,
  provider: SearchProvider | None = None,
  env: Mapping[str, str] | None = None,
) -> list[SearchResult]:
  selected_provider = provider or build_search_provider_from_env(env)
  if selected_provider is None:
    return []

  max_results = _max_results_per_query(env)
  try:
    results = _cached_search_results(
      selected_provider,
      search_queries,
      max_results=max_results,
      env=env,
    )
    return _dedupe_results(results)
  except (httpx.HTTPError, ValueError):
    return []


def build_search_provider_from_env(env: Mapping[str, str] | None = None) -> SearchProvider | None:
  values = env or os.environ
  preferred_provider = values.get("PERFORMATION_SEARCH_PROVIDER", "").casefold()
  tavily_api_key = values.get("TAVILY_API_KEY", "").strip()
  brave_api_key = values.get("BRAVE_SEARCH_API_KEY", "").strip()
  timeout_seconds = _timeout_seconds(values)

  if preferred_provider == "brave" and brave_api_key:
    return BraveSearchProvider(brave_api_key, timeout_seconds=timeout_seconds)
  if preferred_provider == "tavily" and tavily_api_key:
    return TavilySearchProvider(tavily_api_key, timeout_seconds=timeout_seconds)
  if tavily_api_key:
    return TavilySearchProvider(tavily_api_key, timeout_seconds=timeout_seconds)
  if brave_api_key:
    return BraveSearchProvider(brave_api_key, timeout_seconds=timeout_seconds)
  return None


def _timeout_seconds(env: Mapping[str, str]) -> float:
  try:
    return float(env.get("PERFORMATION_SEARCH_TIMEOUT_SECONDS") or str(DEFAULT_TIMEOUT_SECONDS))
  except ValueError:
    return DEFAULT_TIMEOUT_SECONDS


def _max_results_per_query(env: Mapping[str, str] | None) -> int:
  values = env or os.environ
  try:
    configured = int(values.get("PERFORMATION_SEARCH_MAX_RESULTS") or str(DEFAULT_MAX_RESULTS_PER_QUERY))
  except ValueError:
    configured = DEFAULT_MAX_RESULTS_PER_QUERY
  return min(max(configured, 1), 10)


def _cached_search_results(
  provider: SearchProvider,
  search_queries: list[SearchQuery],
  *,
  max_results: int,
  env: Mapping[str, str] | None,
) -> list[SearchResult]:
  provider_key = _provider_cache_key(provider)
  results: list[SearchResult] = []
  for search_query in search_queries:
    key_parts = {
      "provider": provider_key,
      "query": search_query["query"],
      "purpose": search_query["purpose"],
      "max_results": max_results,
    }
    results.extend(
      get_or_set_cached(
        "public_search",
        key_parts,
        ttl_seconds=cache_ttl_seconds(env, "PERFORMATION_SEARCH_CACHE_TTL_SECONDS", DEFAULT_SEARCH_CACHE_TTL_SECONDS),
        max_items=cache_max_items(env),
        factory=lambda search_query=search_query: provider.search(search_query, max_results=max_results),
      )
    )
  return results


def _provider_cache_key(provider: SearchProvider) -> str:
  return f"{type(provider).__module__}.{type(provider).__qualname__}"


def _dedupe_results(results) -> list[SearchResult]:
  deduped: list[SearchResult] = []
  seen_urls: set[str] = set()
  for result in results:
    url = result["url"]
    if url not in seen_urls:
      deduped.append(result)
      seen_urls.add(url)
  return deduped


def _normalize_tavily_results(
  payload: dict,
  search_query: SearchQuery,
  *,
  max_results: int,
) -> list[SearchResult]:
  items = payload.get("results") or []
  if not isinstance(items, list):
    return []
  return [
    {
      "title": _string_value(item.get("title")),
      "url": _string_value(item.get("url")),
      "snippet": _string_value(item.get("content")),
      "query": search_query["query"],
    }
    for item in items[:max_results]
    if isinstance(item, dict) and item.get("title") and item.get("url")
  ]


def _normalize_brave_results(
  payload: dict,
  search_query: SearchQuery,
  *,
  max_results: int,
) -> list[SearchResult]:
  web = payload.get("web") or {}
  if not isinstance(web, dict):
    return []
  items = web.get("results") or []
  if not isinstance(items, list):
    return []
  return [
    {
      "title": _string_value(item.get("title")),
      "url": _string_value(item.get("url")),
      "snippet": _join_snippets(item.get("description"), item.get("extra_snippets")),
      "query": search_query["query"],
    }
    for item in items[:max_results]
    if isinstance(item, dict) and item.get("title") and item.get("url")
  ]


def _join_snippets(description, extra_snippets) -> str:
  snippets = [_string_value(description)]
  if isinstance(extra_snippets, list):
    snippets.extend(_string_value(item) for item in extra_snippets)
  return " ".join(snippet for snippet in snippets if snippet).strip()


def _string_value(value) -> str:
  return value if isinstance(value, str) else ""
