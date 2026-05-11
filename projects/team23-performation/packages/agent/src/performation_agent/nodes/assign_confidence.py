from __future__ import annotations

from performation_agent.state import GuideState


def assign_confidence(state: GuideState) -> GuideState:
  if state.get("event_candidates") and state.get("venue") is None:
    confidence_notes = [
      "공연 후보가 확인되어 단일 공연장으로 단정하지 않았습니다.",
      "후보별 출처와 최신 공식 공지를 확인한 뒤 하나를 선택해야 합니다.",
    ]
  elif state.get("venue") is None:
    confidence_notes = ["지원 범위 밖이거나 입력이 모호하여 로컬 공연장 데이터와 매칭하지 못했습니다."]
  else:
    confidence_notes = [
      "공식 또는 안정적인 공연장 기본 정보와 공연별 변동 가능성이 큰 정보를 분리했습니다.",
    ]
    if state.get("venue_inference_source") == "public_search":
      confidence_notes.append("공연명 입력은 공개 검색 결과에서 단일 MVP 공연장 후보가 확인되어 연결했습니다.")
    if state.get("llm_used"):
      confidence_notes.append("Gemini LLM이 검색/공연장 데이터를 바탕으로 요약과 체크리스트 초안을 생성했습니다.")
    else:
      confidence_notes.append("LLM API 키가 없거나 호출에 실패하면 deterministic fallback 문구를 사용합니다.")

  return {"confidence_notes": confidence_notes}
