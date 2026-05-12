import math
import re
from collections import Counter


def tokenize(text: str) -> list[str]:
    lowered = text.lower()
    tokens = re.findall(r"[a-z0-9][a-z0-9_-]*|[가-힣]{2,}", lowered)
    grams: list[str] = []
    korean_text = "".join(re.findall(r"[가-힣]+", lowered))
    for size in (2, 3):
        grams.extend(korean_text[index : index + size] for index in range(max(0, len(korean_text) - size + 1)))
    return tokens + grams


class DeterministicEmbedder:
    def embed(self, text: str) -> dict[str, float]:
        counts = Counter(tokenize(text))
        return {token: float(count) for token, count in counts.items()}


def cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    shared = set(left) & set(right)
    dot = sum(left[token] * right[token] for token in shared)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)
