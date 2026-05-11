"""Small logging helpers for request-flow observability."""

from __future__ import annotations

import time
from typing import Any


def elapsed_ms(started_at: float) -> int:
    return int((time.perf_counter() - started_at) * 1000)


def preview(value: Any, *, limit: int = 80) -> str:
    text = " ".join(str(value).split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "..."
