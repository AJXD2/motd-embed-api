"""Tests for ThreadSafeTTLCache and get_cached_server_info"""

import threading
import time
from unittest.mock import MagicMock


from motd_embed_api.cache import ThreadSafeTTLCache, get_cached_server_info


def test_cache_miss_calls_fetch(fresh_cache):
    fetch = MagicMock(return_value={"online": True})
    result = get_cached_server_info("mc.example.com", fetch, fresh_cache)
    fetch.assert_called_once_with("mc.example.com")
    assert result == {"online": True}


def test_cache_hit_does_not_call_fetch_again(fresh_cache):
    fetch = MagicMock(return_value={"online": True})
    get_cached_server_info("mc.example.com", fetch, fresh_cache)
    get_cached_server_info("mc.example.com", fetch, fresh_cache)
    fetch.assert_called_once()


def test_cache_size_increments(fresh_cache):
    fetch = MagicMock(return_value={"online": True})
    get_cached_server_info("server1.com", fetch, fresh_cache)
    get_cached_server_info("server2.com", fetch, fresh_cache)
    assert fresh_cache.size() == 2


def test_cache_clear_resets_size(fresh_cache):
    fetch = MagicMock(return_value={"online": True})
    get_cached_server_info("server1.com", fetch, fresh_cache)
    fresh_cache.clear()
    assert fresh_cache.size() == 0


def test_cache_ttl_expiry():
    cache = ThreadSafeTTLCache(maxsize=10, ttl_seconds=1)
    fetch = MagicMock(return_value={"online": True})

    get_cached_server_info("mc.example.com", fetch, cache)
    assert fetch.call_count == 1

    time.sleep(1.1)  # wait for TTL to expire

    get_cached_server_info("mc.example.com", fetch, cache)
    assert fetch.call_count == 2


def test_get_returns_none_for_missing_key(fresh_cache):
    assert fresh_cache.get("nonexistent") is None


def test_set_and_get_roundtrip(fresh_cache):
    fresh_cache.set("key", {"data": 42})
    assert fresh_cache.get("key") == {"data": 42}


def test_concurrent_access_does_not_corrupt():
    """Multiple threads writing distinct keys should all be stored."""
    cache = ThreadSafeTTLCache(maxsize=200, ttl_seconds=30)
    errors = []

    def write(n):
        try:
            cache.set(f"key-{n}", n)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=write, args=(i,)) for i in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert cache.size() == 50
