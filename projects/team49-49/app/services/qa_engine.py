import json
from typing import Any

import httpx

from app.repositories.sqlite import SQLiteRepository

INSUFFICIENT_CONTEXT_MESSAGE = "현재까지 저장된 팀 컨텍스트에서는 관련된 논의나 근거를 찾을 수 없습니다."

_UPSTAGE_BASE_URL = "https://api.upstage.ai/v1"
_UPSTAGE_MODEL = "solar-pro2"

_SYSTEM_PROMPT = """\
당신은 팀의 기획 컨텍스트를 기반으로 질문에 답하는 QA 어시스턴트입니다.

## 컨텍스트 구조

컨텍스트는 아래 세 섹션으로 구성됩니다:

- **Knowledge Cards**: 질문과 의미적으로 가장 유사한 카드 (1차 근거)
- **Chunks**: 질문과 의미적으로 유사한 원문 텍스트 청크
- **Relations & Connected Cards**: Knowledge Cards에서 뻗어나온 관계 엣지와, 그 끝에 연결된 인접 카드(Neighbor Card)가 함께 묶여 있습니다.
  형식 예시:
  [Relation #5] Card #3 --supports--> Card #7
    근거: ...
    신뢰도: 0.85
    ↳ [Neighbor Card #7] 제목
       타입: ...
       요약: ...

## 추론 규칙

1. **Knowledge Cards를 1차 근거로 삼으세요.** 답변의 핵심은 반드시 Knowledge Cards와 Chunks에서 출발해야 합니다.

2. **Relations & Connected Cards는 relation_type과 신뢰도를 기준으로 활용하세요.**
   각 블록은 "어떤 카드가 어떤 관계로 연결되어 있고, 그 끝에 어떤 카드가 있는지"를 한 번에 알려줍니다.
   - 신뢰도가 높을수록 해당 Neighbor Card를 보조 근거로 적극 활용하세요.
   - relation_type이 대립 계열(contradicts, conflicts 등)이면 상충되는 시각이 존재함을 답변에 명시하세요.
   - 신뢰도가 낮은(0.5 미만) 관계의 Neighbor Card는 불확실한 배경 정보로만 처리하세요.

3. **Neighbor Card는 단독 근거가 될 수 없습니다.** 반드시 연결된 Relation의 맥락 안에서만 보조 근거로 사용하세요.

4. 컨텍스트에 없는 내용은 추측하지 마세요.

5. 반드시 아래 JSON 형식으로만 응답하세요:

{
  "answer": "한국어로 작성된 답변",
  "cited_card_ids": [1, 2],
  "cited_chunk_ids": [3]
}
"""


def _build_user_prompt(question: str, context_str: str) -> str:
    return f"""## 질문
{question}

## 팀 컨텍스트
{context_str}

위 컨텍스트를 바탕으로 질문에 답하고, 참조한 카드/청크 ID를 JSON으로 반환하세요."""


class LocalQAEngine:
    """qa_assistant 그래프의 비즈니스 로직을 로컬에서 실행하는 엔진."""

    def __init__(self, repository: SQLiteRepository, upstage_api_key: str = ""):
        self.repository = repository
        self.upstage_api_key = upstage_api_key

    def format_context(
        self,
        cards: list[dict[str, Any]],
        chunks: list[dict[str, Any]],
        relations: list[dict[str, Any]],
        neighbor_cards: list[dict[str, Any]],
    ) -> str:
        card_blocks = []
        for card in cards:
            card_blocks.append(
                f"[Card #{card['id']}] {card.get('title', '')}\n"
                f"타입: {card.get('card_type', '')}\n"
                f"요약: {card.get('summary', '')}\n"
                f"근거: {card.get('evidence_quote', '')}"
            )

        chunk_blocks = [
            f"[Chunk #{chunk['id']}] {(chunk.get('content') or '')[:400]}"
            for chunk in chunks
        ]

        neighbor_map = {card["id"]: card for card in neighbor_cards}
        primary_ids = {card["id"] for card in cards}

        relation_blocks = []
        for r in relations:
            src, tgt = r["source_card_id"], r["target_card_id"]
            neighbor_id = tgt if src in primary_ids else src
            neighbor = neighbor_map.get(neighbor_id)

            block = (
                f"[Relation #{r['id']}] Card #{src} --{r['relation_type']}--> Card #{tgt}\n"
                f"  근거: {r.get('reason', '')}\n"
                f"  신뢰도: {r.get('confidence', '')}"
            )
            if neighbor:
                block += (
                    f"\n  ↳ [Neighbor Card #{neighbor['id']}] {neighbor.get('title', '')}\n"
                    f"     타입: {neighbor.get('card_type', '')}\n"
                    f"     요약: {neighbor.get('summary', '')}"
                )
            relation_blocks.append(block)

        sections = []
        if card_blocks:
            sections.append("### Knowledge Cards\n" + "\n\n".join(card_blocks))
        if chunk_blocks:
            sections.append("### Chunks\n" + "\n\n".join(chunk_blocks))
        if relation_blocks:
            sections.append("### Relations & Connected Cards\n" + "\n\n".join(relation_blocks))

        return "\n\n".join(sections)

    def generate_answer(
        self,
        question: str,
        context_str: str,
        *,
        system_prompt: str = "",
        model: str = _UPSTAGE_MODEL,
        temperature: float = 0.2,
        max_tokens: int = 900,
    ) -> dict[str, Any]:
        if not self.upstage_api_key:
            return {
                "answer": "UPSTAGE_API_KEY가 설정되지 않았습니다.",
                "cited_card_ids": [],
                "cited_chunk_ids": [],
            }

        try:
            response = httpx.post(
                f"{_UPSTAGE_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.upstage_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model or _UPSTAGE_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt.strip() or _SYSTEM_PROMPT},
                        {"role": "user", "content": _build_user_prompt(question, context_str)},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "response_format": {"type": "json_object"},
                },
                timeout=30.0,
            )
            response.raise_for_status()
            parsed = json.loads(response.json()["choices"][0]["message"]["content"].strip())
            return {
                "answer": str(parsed.get("answer", "")),
                "cited_card_ids": [int(x) for x in parsed.get("cited_card_ids", []) if str(x).isdigit()],
                "cited_chunk_ids": [int(x) for x in parsed.get("cited_chunk_ids", []) if str(x).isdigit()],
            }
        except Exception:
            return {
                "answer": "Upstage API 호출에 실패했습니다. API 키와 네트워크 상태를 확인해 주세요.",
                "cited_card_ids": [],
                "cited_chunk_ids": [],
            }

    def generate_extractive_answer(
        self,
        question: str,
        cards: list[dict[str, Any]],
        chunks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not cards and not chunks:
            return {
                "answer": INSUFFICIENT_CONTEXT_MESSAGE,
                "cited_card_ids": [],
                "cited_chunk_ids": [],
            }

        lines = ["저장된 컨텍스트 기준으로 확인된 핵심 근거입니다."]
        for card in cards[:3]:
            title = card.get("title") or f"Card #{card['id']}"
            summary = card.get("summary") or card.get("evidence_quote") or ""
            lines.append(f"- {title}: {summary}")

        if not cards:
            for chunk in chunks[:3]:
                quote = (chunk.get("content") or "").strip()
                lines.append(f"- Chunk #{chunk['id']}: {quote[:240]}")

        lines.append(f"\n질문: {question}")
        return {
            "answer": "\n".join(lines),
            "cited_card_ids": [int(card["id"]) for card in cards],
            "cited_chunk_ids": [int(chunk["id"]) for chunk in chunks],
        }

    def assess_confidence(
        self,
        cards: list[dict[str, Any]],
        cited_card_ids: list[int],
    ) -> tuple[str, list[str]]:
        if len(cited_card_ids) >= 2:
            confidence = "high"
        elif len(cited_card_ids) == 1:
            confidence = "medium"
        else:
            confidence = "low"

        cited_set = set(cited_card_ids)
        missing_evidence = [
            card.get("title", f"Card #{card['id']}")
            for card in cards
            if card.get("id") not in cited_set
        ]
        return confidence, missing_evidence

    def card_evidence(self, card: dict[str, Any]) -> dict[str, Any]:
        document = self.repository.get_raw_document(card["source_document_id"])
        return {
            "card_id": card["id"],
            "title": card["title"],
            "source_document": document["filename"],
            "evidence_quote": card["evidence_quote"],
        }

    def chunk_evidence(self, chunk: dict[str, Any]) -> dict[str, Any]:
        document = self.repository.get_raw_document(chunk["document_id"])
        return {
            "chunk_id": chunk["id"],
            "source_document": document["filename"],
            "quote": chunk["content"],
        }

    @staticmethod
    def relation_evidence(relation: dict[str, Any]) -> dict[str, Any]:
        return {
            "relation_id": relation["id"],
            "source_card_id": relation["source_card_id"],
            "target_card_id": relation["target_card_id"],
            "relation_type": relation["relation_type"],
            "reason": relation["reason"],
            "confidence": relation["confidence"],
        }
