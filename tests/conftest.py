"""Shared pytest fixtures"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from motd_embed_api.cache import ThreadSafeTTLCache
from motd_embed_api.config import Settings


# ---------------------------------------------------------------------------
# Settings override — short TTL for cache tests, metrics disabled to reduce
# Prometheus registry collisions between test runs.
# ---------------------------------------------------------------------------

TEST_SETTINGS = Settings(
    allowed_origins_raw="*",
    cache_ttl_seconds=1,
    cache_maxsize=100,
    server_timeout=5.0,
    metrics_enabled=False,
)


@pytest.fixture(autouse=True)
def override_settings(monkeypatch):
    """Replace get_settings() with test settings for every test."""
    monkeypatch.setattr("motd_embed_api.config.get_settings", lambda: TEST_SETTINGS)
    # Also patch where it's imported directly
    for module in [
        "motd_embed_api.main",
        "motd_embed_api.cache",
        "motd_embed_api.server",
    ]:
        try:
            monkeypatch.setattr(f"{module}.get_settings", lambda: TEST_SETTINGS)
        except AttributeError:
            pass
    yield


@pytest.fixture
def fresh_cache():
    """Return a fresh TTL cache with a 1-second TTL."""
    return ThreadSafeTTLCache(maxsize=100, ttl_seconds=1)


# ---------------------------------------------------------------------------
# Server info fixtures
# ---------------------------------------------------------------------------

ONLINE_SERVER_INFO = {
    "online": True,
    "motd": "§aWelcome §lto §cmy §rserver",
    "server_name": "TestServer 1.20",
    "players_online": 5,
    "players_max": 20,
    "version": "1.20.1",
    "favicon": None,
}

OFFLINE_SERVER_INFO = {
    "online": False,
    "motd": "Server Offline",
    "server_name": "mc.example.com",
    "players_online": 0,
    "players_max": 0,
    "version": "Unknown",
    "favicon": None,
}


@pytest.fixture
def online_server():
    return ONLINE_SERVER_INFO.copy()


@pytest.fixture
def offline_server():
    return OFFLINE_SERVER_INFO.copy()


# ---------------------------------------------------------------------------
# HTTP client for endpoint tests
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client():
    """Async HTTP client that talks directly to the FastAPI app."""
    from motd_embed_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
