from typing import Any

from app.services.embeddings import DeterministicEmbedder, cosine_similarity


class LocalVectorStore:
    def __init__(self, embedder: DeterministicEmbedder | None = None):
        self.embedder = embedder or DeterministicEmbedder()

    def rank(self, query: str, items: list[dict[str, Any]], text_key: str, top_k: int = 5) -> list[dict[str, Any]]:
        query_vector = self.embedder.embed(query)
        ranked: list[dict[str, Any]] = []
        for item in items:
            item_vector = self.embedder.embed(str(item.get(text_key, "")))
            score = cosine_similarity(query_vector, item_vector)
            if score > 0:
                ranked.append({**item, "score": score})
        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked[:top_k]
