"""Chroma metadata filter helpers for RAG search."""

from __future__ import annotations

import re
from typing import Any

PATCH_FAMILY_RE = re.compile(r"^(\d+\.\d+)([a-z])?$", flags=re.IGNORECASE)


def patch_family_versions(patch_version: str) -> list[str]:
    """Return accepted versions for a patch family, including `all` fallback."""
    match = PATCH_FAMILY_RE.match(patch_version)
    if not match:
        return [patch_version, "all"]

    base = match.group(1)
    versions = [base, *(f"{base}{chr(code)}" for code in range(ord("a"), ord("z") + 1))]
    return [*versions, "all"]


def patch_where(patch_version: str) -> dict[str, Any]:
    return {"patch_version": {"$in": patch_family_versions(patch_version)}}


def merge_where(base: dict[str, Any] | None, patch_filter: dict[str, Any]) -> dict[str, Any]:
    if not base:
        return patch_filter
    return {"$and": [base, patch_filter]}


__all__ = ["patch_family_versions", "patch_where", "merge_where"]
