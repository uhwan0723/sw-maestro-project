from __future__ import annotations

from performation_agent.state import GuideDraft, GuideState
from performation_agent.tools.source_classifier import classify_search_result
from performation_domain import ConfidenceLabel


DEFAULT_CHECKLIST = [
  "모바일 티켓 또는 예매 내역 확인",
  "신분증 필요 여부 확인",
  "보조배터리 준비",
  "공연장 도착 추천 시간 확인",
  "물품보관 운영 여부 확인",
  "공연 종료 후 교통 혼잡 가능성 확인",
  "공식 공지에서 최종 변동 사항 확인",
]
MAX_PUBLIC_REVIEW_TIPS = 6
PUBLIC_REVIEW_TIP_RULES = (
  (
    ("스탠딩", "입장 대기", "대기", "입장줄", "입장 줄", "게이트"),
    "후기 참고: 스탠딩/입장 대기는 현장 운영에 따라 달라지므로 도착 전 대기 위치와 입장 순서를 공식 공지에서 다시 확인하기",
  ),
  (
    ("물품보관", "보관소", "락커", "locker", "짐"),
    "후기 참고: 물품보관은 조기 혼잡 가능성이 있으니 짐을 줄이고 운영 여부와 수수료를 먼저 확인하기",
  ),
  (
    ("퇴장", "귀가", "지하철", "셔틀", "택시", "교통"),
    "후기 참고: 공연 종료 직후 역과 택시 승강장이 혼잡할 수 있으니 귀가 동선을 미리 정하기",
  ),
  (
    ("준비물", "보조배터리", "우비", "응원봉", "신분증", "물", "간식"),
    "후기 참고: 보조배터리, 신분증, 예매 내역처럼 현장에서 바로 필요한 물품은 작은 가방에 따로 챙기기",
  ),
)


def build_deterministic_guide_draft(state: GuideState) -> GuideDraft:
  venue = state.get("venue")

  if venue is None:
    return apply_public_review_tips(
      {
        "summary": [
          "현재 MVP는 KSPO DOME, Blue Square, YES24 Live Hall 중심으로 지원합니다.",
          "공연장명, 공연 날짜, 아티스트명 또는 예매처 링크를 추가하면 더 정확히 확인할 수 있습니다.",
        ],
        "checklist": ["공식 예매처 또는 공연 공지에서 공연장 정보를 먼저 확인하기"],
        "transit_and_entry_tips": [],
        "official_check_required": ["공연장명", "공연 날짜", "아티스트명", "예매처 공지"],
      },
      state,
    )

  search_summary = (
    "공개 웹 검색 결과와 로컬 공연장 데이터를 함께 참고했습니다."
    if state.get("search_results")
    else "확인 가능한 공개 웹 검색 결과가 없어 로컬 공연장 데이터 기반으로 안내합니다."
  )
  return apply_public_review_tips(
    {
      "summary": [
        f"{venue.name} 방문 전에는 입장 위치, 도착 시간, 물품보관 운영 여부를 공연별 공지로 다시 확인해야 합니다.",
        search_summary,
      ],
      "checklist": DEFAULT_CHECKLIST,
      "transit_and_entry_tips": [
        *venue.transit_notes,
        *venue.entry_notes,
        *venue.locker_notes,
      ],
      "official_check_required": venue.event_check_items,
    },
    state,
  )


def apply_public_review_tips(draft: GuideDraft, state: GuideState) -> GuideDraft:
  review_tips = build_public_review_tip_items(state)
  existing_tips = draft["transit_and_entry_tips"]
  if not review_tips and not any(_is_review_tip(item) for item in existing_tips):
    return draft
  non_review_tips = [item for item in existing_tips if not _is_review_tip(item)]
  merged_review_tips = _dedupe_review_tips(
    [item for item in existing_tips if _is_review_tip(item)] + review_tips
  )[:MAX_PUBLIC_REVIEW_TIPS]

  return {
    "summary": draft["summary"],
    "checklist": draft["checklist"],
    "transit_and_entry_tips": _dedupe_strings([*non_review_tips, *merged_review_tips]),
    "official_check_required": draft["official_check_required"],
  }


def build_public_review_tip_items(state: GuideState) -> list[str]:
  tips: list[str] = []
  for result in state.get("search_results", []):
    confidence_label, _ = classify_search_result(result)
    if confidence_label != ConfidenceLabel.PUBLIC_REVIEW_REFERENCE:
      continue

    haystack = " ".join((result["title"], result["snippet"], result["query"])).casefold()
    for keywords, tip in PUBLIC_REVIEW_TIP_RULES:
      if any(keyword.casefold() in haystack for keyword in keywords):
        tips.append(tip)

  return _dedupe_strings(tips)[:4]


def _dedupe_strings(items: list[str]) -> list[str]:
  deduped: list[str] = []
  seen: set[str] = set()
  for item in items:
    if item in seen:
      continue
    deduped.append(item)
    seen.add(item)
  return deduped


def _dedupe_review_tips(items: list[str]) -> list[str]:
  deduped: list[str] = []
  seen: set[str] = set()
  for item in items:
    key = _review_tip_key(item)
    if key in seen:
      continue
    deduped.append(item)
    seen.add(key)
  return deduped


def _review_tip_key(item: str) -> str:
  if "물품보관" in item or "락커" in item:
    return "locker"
  if any(term in item for term in ("스탠딩", "입장 대기", "대기 위치", "입장 순서")):
    return "entry"
  if any(term in item for term in ("퇴장", "귀가", "지하철", "셔틀", "택시")):
    return "exit_transit"
  if any(term in item for term in ("보조배터리", "신분증", "예매 내역", "응원봉", "우비")):
    return "preparation"
  return item


def _is_review_tip(item: str) -> bool:
  return item.startswith("후기 참고:")
