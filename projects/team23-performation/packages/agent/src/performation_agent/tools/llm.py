from __future__ import annotations

import json
import os
from collections.abc import Mapping
from functools import lru_cache
from hashlib import sha256
from typing import Protocol

import httpx

from performation_agent.state import GuideDraft, GuideState
from performation_agent.tools.cache import (
  DEFAULT_LLM_CACHE_TTL_SECONDS,
  cache_max_items,
  cache_ttl_seconds,
  get_or_set_cached,
)
from performation_agent.tools.guide_draft import build_public_review_tip_items


GEMINI_GENERATE_CONTENT_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"
DEFAULT_LLM_TIMEOUT_SECONDS = 20.0
GUIDE_DRAFT_SCHEMA = {
  "type": "OBJECT",
  "properties": {
    "summary": {"type": "ARRAY", "items": {"type": "STRING"}},
    "checklist": {"type": "ARRAY", "items": {"type": "STRING"}},
    "transit_and_entry_tips": {"type": "ARRAY", "items": {"type": "STRING"}},
    "official_check_required": {"type": "ARRAY", "items": {"type": "STRING"}},
  },
  "required": [
    "summary",
    "checklist",
    "transit_and_entry_tips",
    "official_check_required",
  ],
  "propertyOrdering": [
    "summary",
    "checklist",
    "transit_and_entry_tips",
    "official_check_required",
  ],
}


class GuideDraftProvider(Protocol):
  def generate(self, prompt: str) -> GuideDraft:
    ...


class GeminiGuideDraftProvider:
  def __init__(
    self,
    api_key: str,
    *,
    model: str = DEFAULT_GEMINI_MODEL,
    client: httpx.Client | None = None,
    timeout_seconds: float = DEFAULT_LLM_TIMEOUT_SECONDS,
  ) -> None:
    self._api_key = api_key
    self._model = model
    self._injected_client = client
    self._timeout_seconds = timeout_seconds

  def generate(self, prompt: str) -> GuideDraft:
    if self._injected_client is not None:
      response = self._post(self._injected_client, prompt)
    else:
      with httpx.Client(timeout=self._timeout_seconds) as client:
        response = self._post(client, prompt)
    response.raise_for_status()
    payload = response.json()
    text = _extract_text(payload)
    return _parse_guide_draft(text)

  def _post(self, client: httpx.Client, prompt: str) -> httpx.Response:
    return client.post(
      GEMINI_GENERATE_CONTENT_URL.format(model=self._model),
      headers={
        "Content-Type": "application/json",
        "x-goog-api-key": self._api_key,
      },
      json={
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
          "temperature": 0.2,
          "responseMimeType": "application/json",
          "responseSchema": GUIDE_DRAFT_SCHEMA,
        },
      },
    )


def generate_guide_draft_with_fallback(
  state: GuideState,
  fallback_draft: GuideDraft,
  *,
  provider: GuideDraftProvider | None = None,
  env: Mapping[str, str] | None = None,
) -> tuple[GuideDraft, bool]:
  if provider is not None:
    selected_provider = provider
  elif env is None:
    selected_provider = _cached_provider_from_env()
  else:
    selected_provider = build_guide_draft_provider_from_env(env)
  if selected_provider is None:
    return fallback_draft, False

  prompt = build_guide_prompt(state, fallback_draft)
  try:
    draft = get_or_set_cached(
      "llm_guide_draft",
      _llm_cache_key(selected_provider, prompt),
      ttl_seconds=cache_ttl_seconds(env, "PERFORMATION_LLM_CACHE_TTL_SECONDS", DEFAULT_LLM_CACHE_TTL_SECONDS),
      max_items=cache_max_items(env),
      factory=lambda: selected_provider.generate(prompt),
    )
  except (httpx.HTTPError, ValueError):
    return fallback_draft, False
  return _merge_with_fallback(draft, fallback_draft), True


def build_guide_draft_provider_from_env(env: Mapping[str, str] | None = None) -> GuideDraftProvider | None:
  values = env or os.environ
  provider = values.get("PERFORMATION_LLM_PROVIDER", "gemini").casefold()
  api_key = values.get("GEMINI_API_KEY", "").strip()
  if provider != "gemini" or not api_key:
    return None
  return GeminiGuideDraftProvider(
    api_key,
    model=values.get("PERFORMATION_LLM_MODEL") or DEFAULT_GEMINI_MODEL,
    timeout_seconds=_timeout_seconds(values),
  )


@lru_cache(maxsize=1)
def _cached_provider_from_env() -> GuideDraftProvider | None:
  return build_guide_draft_provider_from_env()


def build_guide_prompt(state: GuideState, fallback_draft: GuideDraft) -> str:
  venue = state.get("venue")
  public_review_results = _public_review_results_for_prompt(state)
  classified_sources = [
    {
      "title": item["source"].title,
      "url": item["source"].url,
      "source_type": item["source"].source_type.value,
      "used_for": item["source"].used_for,
      "reason": item["reason"],
    }
    for item in state.get("classified_sources", [])
  ]
  payload = {
    "input": state.get("query", ""),
    "input_type": state.get("input_type", ""),
    "venue": venue.model_dump(mode="json") if venue is not None else None,
    "event_info": state["event_info"].model_dump(mode="json") if state.get("event_info") is not None else None,
    "classified_sources": classified_sources[:8],
    "public_review_results": public_review_results[:6],
    "public_review_tip_candidates": build_public_review_tip_items(state),
    "fallback_draft": fallback_draft,
  }
  return (
    "너는 공연 관람 준비 가이드 작성자다. "
    "공식 출처와 후기 출처를 구분하고, 공연별로 바뀔 수 있는 내용은 공식 확인 필요 항목에 넣어라. "
    "후기/SNS 기반 팁은 최대 4개만 쓰고 반드시 '후기 참고:'로 시작하며 참고용으로만 표현해라. "
    "제공된 JSON만 근거로 한국어 응답을 만들고, 모르는 내용은 추측하지 마라.\n\n"
    f"{json.dumps(payload, ensure_ascii=False)}"
  )


def _llm_cache_key(provider: GuideDraftProvider, prompt: str) -> dict[str, str]:
  return {
    "provider": f"{type(provider).__module__}.{type(provider).__qualname__}",
    "model": str(getattr(provider, "_model", "")),
    "prompt_sha256": sha256(prompt.encode("utf-8")).hexdigest(),
  }


def _public_review_results_for_prompt(state: GuideState) -> list[dict[str, str]]:
  public_review_sources = {
    item["source"].url
    for item in state.get("classified_sources", [])
    if item["source"].source_type.value == "public_review_reference"
  }
  return [
    {
      "title": result["title"],
      "url": result["url"],
      "snippet": result["snippet"],
      "query": result["query"],
    }
    for result in state.get("search_results", [])
    if result["url"] in public_review_sources
  ]


def _timeout_seconds(env: Mapping[str, str]) -> float:
  try:
    return float(env.get("PERFORMATION_LLM_TIMEOUT_SECONDS") or str(DEFAULT_LLM_TIMEOUT_SECONDS))
  except ValueError:
    return DEFAULT_LLM_TIMEOUT_SECONDS


def _extract_text(payload) -> str:
  if not isinstance(payload, dict):
    raise ValueError("Gemini response must be an object")
  candidates = payload.get("candidates") or []
  if not candidates or not isinstance(candidates[0], dict):
    raise ValueError("Gemini response missing candidates")
  parts = ((candidates[0].get("content") or {}).get("parts") or [])
  if not parts or not isinstance(parts[0], dict):
    raise ValueError("Gemini response missing content parts")
  text = parts[0].get("text")
  if not isinstance(text, str):
    raise ValueError("Gemini response text must be a string")
  return text


def _parse_guide_draft(text: str) -> GuideDraft:
  payload = json.loads(text)
  if not isinstance(payload, dict):
    raise ValueError("Guide draft must be an object")
  return {
    "summary": _string_list(payload.get("summary")),
    "checklist": _string_list(payload.get("checklist")),
    "transit_and_entry_tips": _string_list(payload.get("transit_and_entry_tips")),
    "official_check_required": _string_list(payload.get("official_check_required")),
  }


def _merge_with_fallback(draft: GuideDraft, fallback_draft: GuideDraft) -> GuideDraft:
  return {
    "summary": draft["summary"] or fallback_draft["summary"],
    "checklist": draft["checklist"] or fallback_draft["checklist"],
    "transit_and_entry_tips": draft["transit_and_entry_tips"] or fallback_draft["transit_and_entry_tips"],
    "official_check_required": draft["official_check_required"] or fallback_draft["official_check_required"],
  }


def _string_list(value) -> list[str]:
  if not isinstance(value, list):
    raise ValueError("Guide draft fields must be arrays")
  return [item.strip() for item in value if isinstance(item, str) and item.strip()]
