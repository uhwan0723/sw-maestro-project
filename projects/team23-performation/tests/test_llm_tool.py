import json

import httpx

from performation_agent.tools.cache import clear_agent_caches
from performation_agent.tools.guide_draft import build_deterministic_guide_draft
from performation_agent.tools.llm import (
  DEFAULT_GEMINI_MODEL,
  GEMINI_GENERATE_CONTENT_URL,
  GeminiGuideDraftProvider,
  build_guide_draft_provider_from_env,
  build_guide_prompt,
  generate_guide_draft_with_fallback,
)
from performation_domain import ConfidenceLabel, Source, VenueInfo


FALLBACK_DRAFT = {
  "summary": ["fallback summary"],
  "checklist": ["fallback checklist"],
  "transit_and_entry_tips": ["fallback tip"],
  "official_check_required": ["fallback official check"],
}


def test_build_guide_draft_provider_requires_gemini_key(monkeypatch) -> None:
  monkeypatch.delenv("GEMINI_API_KEY", raising=False)

  assert build_guide_draft_provider_from_env() is None


def test_build_guide_draft_provider_uses_gemini_env() -> None:
  provider = build_guide_draft_provider_from_env(
    {
      "PERFORMATION_LLM_PROVIDER": "gemini",
      "PERFORMATION_LLM_MODEL": "gemini-test",
      "GEMINI_API_KEY": "gemini-key",
    }
  )

  assert isinstance(provider, GeminiGuideDraftProvider)


def test_gemini_provider_normalizes_structured_response() -> None:
  def handler(request: httpx.Request) -> httpx.Response:
    assert str(request.url) == GEMINI_GENERATE_CONTENT_URL.format(model=DEFAULT_GEMINI_MODEL)
    assert request.headers["x-goog-api-key"] == "gemini-test-key"
    body = json.loads(request.content)
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    assert body["generationConfig"]["responseSchema"]["type"] == "OBJECT"
    assert "공연 관람 준비 가이드" in body["contents"][0]["parts"][0]["text"]
    return httpx.Response(
      200,
      json={
        "candidates": [
          {
            "content": {
              "parts": [
                {
                  "text": json.dumps(
                    {
                      "summary": ["AI 요약"],
                      "checklist": ["AI 체크리스트"],
                      "transit_and_entry_tips": ["AI 교통 팁"],
                      "official_check_required": ["AI 공식 확인"],
                    },
                    ensure_ascii=False,
                  )
                }
              ]
            }
          }
        ]
      },
    )

  with httpx.Client(transport=httpx.MockTransport(handler)) as client:
    provider = GeminiGuideDraftProvider("gemini-test-key", client=client)
    draft = provider.generate("공연 관람 준비 가이드")

  assert draft == {
    "summary": ["AI 요약"],
    "checklist": ["AI 체크리스트"],
    "transit_and_entry_tips": ["AI 교통 팁"],
    "official_check_required": ["AI 공식 확인"],
  }


def test_generate_guide_draft_uses_provider_output() -> None:
  class FakeProvider:
    def generate(self, prompt: str):
      assert "fallback summary" in prompt
      return {
        "summary": ["AI 요약"],
        "checklist": ["AI 체크리스트"],
        "transit_and_entry_tips": ["AI 팁"],
        "official_check_required": ["AI 공식 확인"],
      }

  draft, llm_used = generate_guide_draft_with_fallback(
    {"query": "KSPO DOME 준비물", "input_type": "venue_with_detail_question"},
    FALLBACK_DRAFT,
    provider=FakeProvider(),
  )

  assert llm_used is True
  assert draft["summary"] == ["AI 요약"]
  assert draft["checklist"] == ["AI 체크리스트"]


def test_generate_guide_draft_caches_provider_output() -> None:
  clear_agent_caches()

  class CountingProvider:
    def __init__(self) -> None:
      self.calls = 0

    def generate(self, prompt: str):
      self.calls += 1
      return {
        "summary": [f"AI 요약 {self.calls}"],
        "checklist": ["AI 체크리스트"],
        "transit_and_entry_tips": ["AI 팁"],
        "official_check_required": ["AI 공식 확인"],
      }

  provider = CountingProvider()
  env = {"PERFORMATION_LLM_CACHE_TTL_SECONDS": "60"}
  state = {"query": "KSPO DOME 준비물", "input_type": "venue_with_detail_question"}

  first, first_used = generate_guide_draft_with_fallback(state, FALLBACK_DRAFT, provider=provider, env=env)
  second, second_used = generate_guide_draft_with_fallback(state, FALLBACK_DRAFT, provider=provider, env=env)

  assert first_used is True
  assert second_used is True
  assert first == second
  assert provider.calls == 1


def test_generate_guide_draft_keeps_fallback_on_provider_error() -> None:
  class FailingProvider:
    def generate(self, prompt: str):
      raise httpx.TimeoutException("timeout")

  draft, llm_used = generate_guide_draft_with_fallback(
    {"query": "KSPO DOME 준비물"},
    FALLBACK_DRAFT,
    provider=FailingProvider(),
  )

  assert llm_used is False
  assert draft == FALLBACK_DRAFT


def test_build_guide_prompt_includes_sources_but_not_secrets() -> None:
  prompt = build_guide_prompt(
    {
      "query": "KSPO DOME 준비물",
      "input_type": "venue_with_detail_question",
      "classified_sources": [],
    },
    FALLBACK_DRAFT,
  )

  assert "GEMINI_API_KEY" not in prompt
  assert "KSPO DOME 준비물" in prompt
  assert "fallback summary" in prompt
  assert "후기/SNS 기반 팁은 최대 4개" in prompt


def test_build_guide_prompt_includes_public_review_tip_candidates() -> None:
  prompt = build_guide_prompt(
    {
      "query": "KSPO DOME 스탠딩",
      "input_type": "venue_with_detail_question",
      "classified_sources": [
        {
          "source": Source(
            title="KSPO DOME 스탠딩 후기",
            url="https://example.tistory.com/kspo-standing",
            source_type=ConfidenceLabel.PUBLIC_REVIEW_REFERENCE,
            used_for=["KSPO DOME 입장 대기 스탠딩 후기"],
          ),
          "reason": "블로그/후기 성격의 공개 정보입니다.",
        }
      ],
      "search_results": [
        {
          "title": "KSPO DOME 스탠딩 후기",
          "url": "https://example.tistory.com/kspo-standing",
          "snippet": "스탠딩 입장 대기 꿀팁",
          "query": "KSPO DOME 입장 대기 스탠딩 후기",
        }
      ],
    },
    FALLBACK_DRAFT,
  )

  assert "public_review_results" in prompt
  assert "public_review_tip_candidates" in prompt
  assert "후기 참고: 스탠딩/입장 대기" in prompt


def test_deterministic_draft_reflects_search_availability() -> None:
  draft = build_deterministic_guide_draft(
    {
      "query": "KSPO DOME 준비물",
      "venue": VenueInfo(
        name="KSPO DOME",
        transit_notes=["5호선 올림픽공원역 이용"],
        entry_notes=["공연별 입장 위치 확인"],
        locker_notes=["물품보관 운영 여부 확인"],
        event_check_items=["공연별 입장 시간 확인"],
      ),
      "search_results": [
        {
          "title": "검색 결과",
          "url": "https://example.com",
          "snippet": "검색 결과 내용",
          "query": "KSPO DOME 준비물",
        }
      ],
    }
  )

  assert "공개 웹 검색 결과" in draft["summary"][1]


def test_deterministic_draft_uses_neutral_message_without_search_results() -> None:
  draft = build_deterministic_guide_draft(
    {
      "query": "KSPO DOME 준비물",
      "venue": VenueInfo(name="KSPO DOME"),
      "search_results": [],
    }
  )

  assert "확인 가능한 공개 웹 검색 결과가 없어" in draft["summary"][1]
