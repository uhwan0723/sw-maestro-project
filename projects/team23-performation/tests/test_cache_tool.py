from threading import Barrier, Event, Lock, Thread

from performation_agent.tools.cache import (
  TTLCache,
  cache_ttl_seconds,
  clear_agent_caches,
  get_or_set_cached,
)


def test_ttl_cache_returns_deep_copies_and_expires() -> None:
  now = 100.0

  def timer() -> float:
    return now

  cache = TTLCache(max_items=2, timer=timer)
  value = [{"title": "원본"}]
  cache.set("key", value, ttl_seconds=10)
  cached_value = cache.get("key")
  cached_value[0]["title"] = "변경"

  assert cache.get("key") == [{"title": "원본"}]

  now = 111.0
  assert cache.get("key") != [{"title": "원본"}]


def test_get_or_set_cached_calls_factory_once() -> None:
  clear_agent_caches()
  calls = 0

  def factory():
    nonlocal calls
    calls += 1
    return {"value": calls}

  first = get_or_set_cached("test-cache", {"query": "워터밤"}, ttl_seconds=60, max_items=10, factory=factory)
  second = get_or_set_cached("test-cache", {"query": "워터밤"}, ttl_seconds=60, max_items=10, factory=factory)

  assert first == {"value": 1}
  assert second == {"value": 1}
  assert calls == 1


def test_get_or_set_cached_serializes_concurrent_factory_calls() -> None:
  clear_agent_caches()
  calls = 0
  calls_lock = Lock()
  start = Barrier(2)
  factory_entered = Event()
  allow_factory_finish = Event()
  results = []
  errors = []

  def factory():
    nonlocal calls
    with calls_lock:
      calls += 1
      value = calls
    factory_entered.set()
    if not allow_factory_finish.wait(timeout=2):
      raise AssertionError("factory was not released")
    return {"value": value}

  def worker() -> None:
    try:
      start.wait(timeout=2)
      result = get_or_set_cached(
        "concurrent-cache",
        "same-key",
        ttl_seconds=60,
        max_items=10,
        factory=factory,
      )
      results.append(result)
    except Exception as exc:  # pragma: no cover - propagated through assertions below
      errors.append(exc)

  threads = [Thread(target=worker), Thread(target=worker)]
  for thread in threads:
    thread.start()

  assert factory_entered.wait(timeout=2)
  allow_factory_finish.set()

  for thread in threads:
    thread.join(timeout=2)

  assert errors == []
  assert calls == 1
  assert results == [{"value": 1}, {"value": 1}]


def test_cache_ttl_seconds_can_disable_cache() -> None:
  assert cache_ttl_seconds({"PERFORMATION_CACHE_ENABLED": "false"}, "PERFORMATION_SEARCH_CACHE_TTL_SECONDS", 60) == 0
  assert cache_ttl_seconds({"PERFORMATION_SEARCH_CACHE_TTL_SECONDS": "0"}, "PERFORMATION_SEARCH_CACHE_TTL_SECONDS", 60) == 0
