"""프롬프트 로더 — manifest.yaml의 active 버전을 읽어 텍스트/JSON 반환."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import yaml

PROMPTS_DIR = Path(__file__).parent


@lru_cache(maxsize=1)
def _manifest() -> dict:
    with (PROMPTS_DIR / "manifest.yaml").open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def active_version(role: str) -> str:
    return _manifest()["active"][role]


@lru_cache(maxsize=8)
def load_text(role: str) -> str:
    """role ∈ {meta, recommend} → system_<role>.<version>.txt 본문."""
    version = active_version(role)
    path = PROMPTS_DIR / f"system_{role}.{version}.txt"
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=4)
def load_json(role: str) -> dict:
    """role ∈ {intent} → <role>s.<version>.json (예: intents.v1.json)."""
    version = active_version(role)
    path = PROMPTS_DIR / f"{role}s.{version}.json"
    return json.loads(path.read_text(encoding="utf-8"))


__all__ = ["active_version", "load_text", "load_json"]
