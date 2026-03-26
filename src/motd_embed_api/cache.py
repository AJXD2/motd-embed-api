"""Caching for server status responses using LRU with TTL"""

from typing import Optional, Dict, Any, Callable
from cachetools import TTLCache
import threading

from .metrics import CACHE_HITS_TOTAL, CACHE_MISSES_TOTAL


class ThreadSafeTTLCache:
    """Thread-safe TTL cache with LRU eviction"""

    def __init__(self, maxsize: int = 1000, ttl_seconds: int = 30):
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl_seconds)
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._cache[key] = value

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._cache)


# Module-level singleton — lazily initialised on first use so config is read
# after .env has been loaded.
_server_cache: Optional[ThreadSafeTTLCache] = None
_cache_lock = threading.Lock()


def get_cache() -> ThreadSafeTTLCache:
    """Return (or create) the module-level cache singleton."""
    global _server_cache
    if _server_cache is None:
        with _cache_lock:
            if _server_cache is None:
                from .config import get_settings

                s = get_settings()
                _server_cache = ThreadSafeTTLCache(
                    maxsize=s.cache_maxsize,
                    ttl_seconds=s.cache_ttl_seconds,
                )
    return _server_cache


def get_cached_server_info(
    ip: str,
    fetch_func: Callable,
    cache: Optional[ThreadSafeTTLCache] = None,
) -> Dict[str, Any]:
    """
    Return server info from cache, or call fetch_func and populate it.

    Args:
        ip: Server address (used as cache key)
        fetch_func: Callable(ip) -> dict invoked on a cache miss
        cache: Cache instance; defaults to the module-level singleton
    """
    if cache is None:
        cache = get_cache()

    cached = cache.get(ip)
    if cached is not None:
        CACHE_HITS_TOTAL.labels(cache="server_info").inc()
        return cached

    CACHE_MISSES_TOTAL.labels(cache="server_info").inc()
    info = fetch_func(ip)
    cache.set(ip, info)
    return info
