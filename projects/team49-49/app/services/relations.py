import json
from typing import Any

from app.core.config import get_settings
from app.models.schemas import RELATION_TYPES
from app.repositories.sqlite import SQLiteRepository
from app.services.embeddings import DeterministicEmbedder, cosine_similarity
from app.services.llm import LLMClient, build_llm_client


class CandidateRelationDetector:
    def __init__(self, embedder: DeterministicEmbedder | None = None, llm_client: LLMClient | None = None):
        self.embedder = embedder or DeterministicEmbedder()
        try:
            self.llm_client = llm_client or build_llm_client(get_settings())
        except Exception:
            self.llm_client = None

    def detect(self, new_card: dict[str, Any], existing_cards: list[dict[str, Any]], top_k: int = 5) -> list[dict[str, Any]]:
        relations: list[dict[str, Any]] = []
        new_text = self._card_text(new_card)
        new_vector = self.embedder.embed(new_text)

        candidate_scores = []

        for existing in existing_cards:
            if existing["id"] == new_card["id"]:
                continue
            existing_text = self._card_text(existing)
            score = cosine_similarity(new_vector, self.embedder.embed(existing_text))
            if self._normalized(new_card["title"]) == self._normalized(existing["title"]):
                relations.append(
                    {
                        "source_card_id": new_card["id"],
                        "target_card_id": existing["id"],
                        "relation_type": "duplicates",
                        "reason": "제목이 동일해 중복으로 판단됨",
                        "confidence": "high",
                    }
                )
            else:
                candidate_scores.append((score, existing))

        candidate_scores.sort(key=lambda x: x[0], reverse=True)
        candidates_to_eval = [item[1] for item in candidate_scores[:top_k]]

        if not candidates_to_eval:
            return relations

        if self.llm_client and hasattr(self.llm_client, "complete"):
            llm_relations = self._evaluate_with_llm(new_card, candidates_to_eval)
            if llm_relations is not None:
                relations.extend(llm_relations)
                return relations

        for existing in candidates_to_eval:
            relations.append(
                {
                    "source_card_id": new_card["id"],
                    "target_card_id": existing["id"],
                    "relation_type": "related_to",
                    "reason": "키워드와 내용 유사도가 높아 관련으로 판단됨",
                    "confidence": "medium",
                }
            )
        return relations

    def _evaluate_with_llm(self, new_card: dict[str, Any], candidates: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
        system_prompt = (
            "You are an AI assistant that determines the relationship between knowledge cards.\n"
            "Given a NEW card and a list of EXISTING cards, you must classify the relationship between the NEW card and each EXISTING card.\n"
            "The allowed relation types are: 'supports', 'contradicts', 'duplicates', 'related_to', 'derived_from', or 'none'.\n"
            "- 'supports': The existing card provides evidence or basis for the new card.\n"
            "- 'contradicts': The existing card conflicts with or refutes the new card.\n"
            "- 'duplicates': The cards represent the same exact information.\n"
            "- 'derived_from': The new card is a logical continuation or derived conclusion from the existing card.\n"
            "- 'related_to': The cards are related but don't fit the above categories.\n"
            "- 'none': The cards are not meaningfully related.\n\n"
            "You MUST respond ONLY with a valid JSON array of objects. Each object must have:\n"
            '- "target_card_id" (integer)\n'
            '- "relation_type" (string: one of the allowed types)\n'
            '- "reason" (string: 두 카드의 핵심 키워드를 포함하여 구체적인 논리적 연결성이나 인과관계를 설명하는 한국어 문장. 예: "기존 카드의 A에 대해 신규 카드가 B라는 논리적 근거를 제공하므로 뒷받침함")\n'
            '- "confidence" (string: 두 카드의 내용이 직접적으로 일치하거나 논리적 결함이 없으면 "high", 문맥상 유추가 필요하다면 "medium", 간접적인 연관성만 있다면 "low"를 부여하세요)\n\n'
            "Omit any existing cards where the relation_type is 'none'."
        )

        candidates_json = [{"id": c["id"], "title": c["title"], "summary": c["summary"], "type": c.get("card_type")} for c in candidates]
        new_card_info = {"id": new_card["id"], "title": new_card["title"], "summary": new_card["summary"], "type": new_card.get("card_type")}

        user_prompt = (
            f"NEW CARD:\n{json.dumps(new_card_info, ensure_ascii=False, indent=2)}\n\n"
            f"EXISTING CARDS:\n{json.dumps(candidates_json, ensure_ascii=False, indent=2)}\n"
        )

        try:
            response_text = self.llm_client.complete(system_prompt, user_prompt)
            if not response_text:
                return None

            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            parsed = json.loads(response_text.strip())
            if not isinstance(parsed, list):
                return None

            valid_relations = []
            allowed_types = {"supports", "contradicts", "duplicates", "related_to", "derived_from"}

            for item in parsed:
                rel_type = item.get("relation_type")
                if rel_type in allowed_types:
                    valid_relations.append({
                        "source_card_id": new_card["id"],
                        "target_card_id": item["target_card_id"],
                        "relation_type": rel_type,
                        "reason": item.get("reason", "연관성이 확인됨"),
                        "confidence": item.get("confidence", "medium"),
                    })
            return valid_relations
        except Exception:
            return None

    @staticmethod
    def _card_text(card: dict[str, Any]) -> str:
        keywords = " ".join(card.get("keywords", []))
        tags = " ".join(card.get("tags", []))
        return f"{card.get('title', '')} {card.get('summary', '')} {keywords} {tags}"

    @staticmethod
    def _normalized(text: str) -> str:
        return "".join(text.lower().split()).strip(".。!?！？")


class RelationLinkingService:
    def __init__(
        self,
        repository: SQLiteRepository,
        detector: CandidateRelationDetector | None = None,
    ):
        self.repository = repository
        self.detector = detector or CandidateRelationDetector()

    def link_new_card(self, workspace_id: int, new_card: dict[str, Any], existing_cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
        existing_keys = self.existing_relation_keys(workspace_id)
        return self.link_new_card_with_keys(workspace_id, new_card, existing_cards, existing_keys)

    def link_new_card_with_keys(
        self,
        workspace_id: int,
        new_card: dict[str, Any],
        existing_cards: list[dict[str, Any]],
        existing_keys: set[tuple[int, int, str]],
    ) -> list[dict[str, Any]]:
        relations: list[dict[str, Any]] = []
        for candidate in self.detector.detect(new_card, existing_cards):
            relation_type = candidate.get("relation_type")
            if relation_type not in RELATION_TYPES:
                continue
            key = self._relation_key(candidate["source_card_id"], candidate["target_card_id"], relation_type)
            if key in existing_keys:
                continue
            relation = self.repository.create_relation(workspace_id=workspace_id, **candidate)
            relations.append(relation)
            existing_keys.add(key)
        return relations

    def existing_relation_keys(self, workspace_id: int) -> set[tuple[int, int, str]]:
        return {
            self._relation_key(relation["source_card_id"], relation["target_card_id"], relation["relation_type"])
            for relation in self.repository.list_relations(workspace_id)
        }

    @staticmethod
    def _relation_key(source_card_id: int, target_card_id: int, relation_type: str) -> tuple[int, int, str]:
        if relation_type in {"duplicates", "related_to"}:
            left, right = sorted((source_card_id, target_card_id))
            return left, right, relation_type
        return source_card_id, target_card_id, relation_type
