"""Test and explicit demo RAG fixtures."""

from __future__ import annotations

from app.schemas.shared import IndexName, RagChunk


class InMemoryStubRagService:
    """Small deterministic data set for Strategy Agent tests and demos."""

    def __init__(self) -> None:
        self._whitelist: dict[str, set[str]] = {
            "units": {
                "정밀의 사도",
                "기계 학자",
                "사이버시티 챔피언",
                "어둠의 화신",
                "9코스트 정밀",
                "광신도",
                "라이트브링어",
                "강철의 수호자",
                "드림리프 마법사",
            },
            "items": {
                "구인수의 격노검",
                "거인 학살자",
                "최후의 속삭임",
                "푸른 파수꾼",
                "정의의 손",
                "굳건한 심장",
                "용의 발톱",
                "자드자의 심장",
                "곡궁",
                "BF대검",
                "쇠사슬 조끼",
            },
            "traits": {"정밀", "기계 학자", "사이버시티", "어둠", "광신도"},
            "augments": {"내일의 정밀", "광신도의 광기", "리롤의 정석"},
        }

        self._chunks: dict[IndexName, list[RagChunk]] = {
            "units": [
                RagChunk(
                    id="u_jeongmil_14.9",
                    index="units",
                    text="정밀의 사도: 4코스트 DPS, 정밀 시너지 핵심.",
                    metadata={"name": "정밀의 사도", "cost": 4, "patch_version": "14.9"},
                    score=0.85,
                ),
                RagChunk(
                    id="u_gigye_14.9",
                    index="units",
                    text="기계 학자: 3코스트 캐스터, 마나 시너지.",
                    metadata={"name": "기계 학자", "cost": 3, "patch_version": "14.9"},
                    score=0.78,
                ),
            ],
            "items": [
                RagChunk(
                    id="i_guinsu_14.9",
                    index="items",
                    text="구인수의 격노검: AD 캐리에 핵심.",
                    metadata={"name": "구인수의 격노검", "patch_version": "14.9"},
                    score=0.82,
                ),
            ],
            "deck_templates": [
                RagChunk(
                    id="d_jeongmil_reroll_14.9",
                    index="deck_templates",
                    text=(
                        "정밀 리롤 덱: 정밀의 사도를 메인 캐리로, "
                        "기계 학자 + 광신도 시너지. 초중반 안정적, 8레벨 도달 후 9코 보강."
                    ),
                    metadata={
                        "name": "정밀 리롤",
                        "core_units": ["정밀의 사도", "기계 학자", "광신도", "라이트브링어"],
                        "key_items": ["구인수의 격노검", "최후의 속삭임", "정의의 손"],
                        "difficulty": "easy",
                        "preferred_styles": ["stable_top4", "easy_beginner"],
                        "patch_version": "14.9",
                    },
                    score=0.88,
                ),
                RagChunk(
                    id="d_cyber_14.9",
                    index="deck_templates",
                    text=(
                        "사이버시티 9코 덱: 사이버시티 챔피언 6단계 + 9코스트 정밀. "
                        "고점 1등형, 어그로 운영."
                    ),
                    metadata={
                        "name": "사이버시티 9코",
                        "core_units": ["사이버시티 챔피언", "9코스트 정밀", "어둠의 화신"],
                        "key_items": ["구인수의 격노검", "거인 학살자", "최후의 속삭임"],
                        "difficulty": "hard",
                        "preferred_styles": ["high_risk_first"],
                        "patch_version": "14.9",
                    },
                    score=0.81,
                ),
            ],
            "playbook": [
                RagChunk(
                    id="pb_economy_early",
                    index="playbook",
                    text="2-1 50골드 경제 빌드, 3-2 4레벨 도달 후 안정화.",
                    metadata={"topic": "economy", "phase": "early", "patch_version": "all"},
                    score=0.7,
                ),
            ],
            "patch_summary": [
                RagChunk(
                    id="ps_14.9_1",
                    index="patch_summary",
                    text="14.9 패치: 정밀 시너지 버프, 사이버시티 챔피언 너프.",
                    metadata={
                        "patch_version": "14.9",
                        "change_type": "buff",
                        "target_kind": "trait",
                        "target_name": "정밀",
                    },
                    score=0.9,
                ),
            ],
            "traits": [],
            "augments": [],
            "glossary": [],
        }

    def search(
        self,
        index: IndexName,
        query: str,
        *,
        k: int,
        patch_version: str,
        where: dict | None = None,
    ) -> list[RagChunk]:
        del query, where
        chunks = [
            chunk
            for chunk in self._chunks.get(index, [])
            if chunk.metadata.get("patch_version", patch_version) in {patch_version, "all"}
        ]
        return chunks[:k]

    def multi_search(
        self,
        plan: list[tuple[IndexName, str, int]],
        *,
        patch_version: str,
    ) -> list[RagChunk]:
        out: list[RagChunk] = []
        for index, query, k in plan:
            out.extend(self.search(index, query, k=k, patch_version=patch_version))
        return out

    def get_whitelist(self, patch_version: str) -> dict[str, set[str]]:
        del patch_version
        return {key: set(values) for key, values in self._whitelist.items()}


__all__ = ["InMemoryStubRagService"]
