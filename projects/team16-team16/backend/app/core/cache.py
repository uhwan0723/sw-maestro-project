from threading import Lock
from typing import Any

from cachetools import TTLCache

from app.core.config import get_settings

_settings = get_settings()
_cache: TTLCache = TTLCache(maxsize=_settings.cache_maxsize, ttl=_settings.cache_ttl)
_lock = Lock()


def get(key: Any) -> Any | None:
    with _lock:
        return _cache.get(key)


def set(key: Any, value: Any) -> None:  # noqa: A001 (의도적으로 set 이름 사용)
    with _lock:
        _cache[key] = value


def clear() -> None:
    """테스트 목적."""
    with _lock:
        _cache.clear()
