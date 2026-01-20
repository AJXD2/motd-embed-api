"""Caching for server status responses using LRU with TTL"""
from typing import Optional, Dict, Any, Callable
from cachetools import TTLCache
import threading


class ThreadSafeTTLCache:
    """Thread-safe TTL cache with LRU eviction"""

    def __init__(self, maxsize: int = 1000, ttl_seconds: int = 30):
        """
        Initialize cache.

        Args:
            maxsize: Maximum number of entries in cache
            ttl_seconds: Time to live for cache entries in seconds
        """
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl_seconds)
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            self._cache[key] = value

    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """Get current cache size"""
        with self._lock:
            return len(self._cache)


# Global cache instance
# Max 1000 servers, 30 second TTL
_server_cache = ThreadSafeTTLCache(maxsize=1000, ttl_seconds=30)


def get_cached_server_info(ip: str, fetch_func: Callable) -> Dict[str, Any]:
    """
    Get server info with caching.

    Args:
        ip: Server address
        fetch_func: Function to fetch server info if not cached

    Returns:
        Server info dictionary
    """
    cached = _server_cache.get(ip)
    if cached is not None:
        return cached

    info = fetch_func(ip)
    _server_cache.set(ip, info)
    return info
