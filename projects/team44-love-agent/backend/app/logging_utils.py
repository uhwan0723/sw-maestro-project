from __future__ import annotations

import hashlib
import os


def _is_debug_pii_enabled() -> bool:
    return os.getenv("LOG_DEBUG_PII", "").strip().lower() in {"1", "true", "yes", "on"}


def hash_user_question(text: str) -> str:
    """Stable short hash for log correlation without exposing the original text."""

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"sha256:{digest[:16]}"


def redact_for_log(text: str | None, *, max_len: int = 120) -> str:
    """Truncate text for operational logs unless LOG_DEBUG_PII is enabled.

    Operational logs must never contain LLM raw excerpts or user-question text in full.
    Debug mode (LOG_DEBUG_PII=1) preserves the original string for local debugging.
    """

    if text is None:
        return ""
    if _is_debug_pii_enabled():
        return text
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    return f"{truncated}... [+{len(text) - max_len} chars redacted]"


def include_traceback_in_logs() -> bool:
    """Whether to attach full traceback (exc_info) to operational logs."""

    return _is_debug_pii_enabled()
