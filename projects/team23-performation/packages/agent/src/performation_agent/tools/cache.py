from __future__ import annotations

import copy
import json
import os
from collections.abc import Callable, Mapping
from threading import RLock
from time import monotonic
from typing import Any, TypeVar


DEFAULT_CACHE_MAX_ITEMS = 256
DEFAULT_SEARCH_CACHE_TTL_SECONDS = 60 * 60
DEFAULT_KOPIS_CACHE_TTL_SECONDS = 6 * 60 * 60
DEFAULT_LLM_CACHE_TTL_SECONDS = 60 * 60
_CACHE_MISS = object()
_T = TypeVar("_T")
_CACHES: dict[str, TTLCache] = {}
_CACHES_LOCK = RLock()
_KEY_LOCKS: dict[tuple[str, str], RLock] = {}
_KEY_LOCKS_LOCK = RLock()


class TTLCache:
  def __init__(
    self,
    *,
    max_items: int = DEFAULT_CACHE_MAX_ITEMS,
    timer: Callable[[], float] = monotonic,
  ) -> None:
    self._max_items = max(max_items, 1)
    self._timer = timer
    self._items: dict[str, tuple[float, Any]] = {}
    self._lock = RLock()

  def get(self, key: str) -> Any:
    with self._lock:
      now = self._timer()
      item = self._items.get(key)
      if item is None:
        return _CACHE_MISS
      expires_at, value = item
      if expires_at <= now:
        del self._items[key]
        return _CACHE_MISS
      return copy.deepcopy(value)

  def set(self, key: str, value: Any, *, ttl_seconds: float) -> None:
    if ttl_seconds <= 0:
      return
    with self._lock:
      self._delete_expired()
      self._items[key] = (self._timer() + ttl_seconds, copy.deepcopy(value))
      self._evict_next_expiring()

  def clear(self) -> None:
    with self._lock:
      self._items.clear()

  def _delete_expired(self) -> None:
    now = self._timer()
    expired_keys = [key for key, (expires_at, _) in self._items.items() if expires_at <= now]
    for key in expired_keys:
      del self._items[key]

  def _evict_next_expiring(self) -> None:
    while len(self._items) > self._max_items:
      next_expiry_key = min(self._items, key=lambda key: self._items[key][0])
      del self._items[next_expiry_key]


def get_or_set_cached(
  namespace: str,
  key_parts: Any,
  *,
  ttl_seconds: float,
  max_items: int,
  factory: Callable[[], _T],
) -> _T:
  if ttl_seconds <= 0:
    return factory()

  cache = _cache(namespace, max_items=max_items)
  key = cache_key(key_parts)
  cached_value = cache.get(key)
  if cached_value is not _CACHE_MISS:
    return cached_value

  with _key_lock(namespace, key):
    cached_value = cache.get(key)
    if cached_value is not _CACHE_MISS:
      return cached_value

    value = factory()
    cache.set(key, value, ttl_seconds=ttl_seconds)
    return value


def cache_key(parts: Any) -> str:
  return json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str)


def cache_enabled(env: Mapping[str, str] | None = None) -> bool:
  values = env or os.environ
  raw_value = values.get("PERFORMATION_CACHE_ENABLED", "true").strip().casefold()
  return raw_value not in {"0", "false", "no", "off"}


def cache_max_items(env: Mapping[str, str] | None = None) -> int:
  values = env or os.environ
  try:
    return max(int(values.get("PERFORMATION_CACHE_MAX_ITEMS") or str(DEFAULT_CACHE_MAX_ITEMS)), 1)
  except ValueError:
    return DEFAULT_CACHE_MAX_ITEMS


def cache_ttl_seconds(
  env: Mapping[str, str] | None,
  key: str,
  default_seconds: float,
) -> float:
  if not cache_enabled(env):
    return 0
  values = env or os.environ
  try:
    return max(float(values.get(key) or values.get("PERFORMATION_CACHE_TTL_SECONDS") or str(default_seconds)), 0)
  except ValueError:
    return default_seconds


def clear_agent_caches() -> None:
  with _CACHES_LOCK:
    for cache in _CACHES.values():
      cache.clear()
  with _KEY_LOCKS_LOCK:
    _KEY_LOCKS.clear()


def _cache(namespace: str, *, max_items: int) -> TTLCache:
  with _CACHES_LOCK:
    cache = _CACHES.get(namespace)
    if cache is None or cache._max_items != max_items:
      cache = TTLCache(max_items=max_items)
      _CACHES[namespace] = cache
    return cache


def _key_lock(namespace: str, key: str) -> RLock:
  with _KEY_LOCKS_LOCK:
    lock = _KEY_LOCKS.get((namespace, key))
    if lock is None:
      lock = RLock()
      _KEY_LOCKS[(namespace, key)] = lock
    return lock
