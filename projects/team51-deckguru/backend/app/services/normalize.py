import hashlib
import re
import unicodedata


def normalize_question(q: str) -> str:
    q = unicodedata.normalize("NFC", q).lower()
    q = re.sub(r"\s+", " ", q).strip()
    q = re.sub(r"[?!~.…]+$", "", q).strip()
    return q


def cache_key(tier: str, play_style: str, question: str, patch: str) -> str:
    norm = normalize_question(question)
    raw = f"{tier}|{play_style}|{norm}|{patch}"
    return hashlib.sha256(raw.encode()).hexdigest()
