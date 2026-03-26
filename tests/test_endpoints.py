"""Integration tests for FastAPI endpoints"""

import pytest
from unittest.mock import patch

pytestmark = pytest.mark.asyncio


ONLINE_SERVER_INFO = {
    "online": True,
    "motd": "§aWelcome to the server",
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


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


async def test_health_returns_200(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_health_has_request_id_header(client):
    response = await client.get("/health")
    assert "x-request-id" in response.headers


async def test_health_echoes_provided_request_id(client):
    response = await client.get("/health", headers={"X-Request-ID": "test-id-123"})
    assert response.headers["x-request-id"] == "test-id-123"


async def test_health_generates_unique_ids(client):
    r1 = await client.get("/health")
    r2 = await client.get("/health")
    assert r1.headers["x-request-id"] != r2.headers["x-request-id"]


async def test_health_has_security_headers(client):
    response = await client.get("/health")
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert "x-frame-options" in response.headers
    assert "content-security-policy" in response.headers


# ---------------------------------------------------------------------------
# Embed endpoint
# ---------------------------------------------------------------------------


async def test_embed_returns_html(client):
    with patch(
        "motd_embed_api.main.get_cached_server_info", return_value=ONLINE_SERVER_INFO
    ):
        response = await client.get("/v1/server/mc.example.com/embed")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


async def test_embed_html_contains_motd(client):
    with patch(
        "motd_embed_api.main.get_cached_server_info", return_value=ONLINE_SERVER_INFO
    ):
        response = await client.get("/v1/server/mc.example.com/embed")
    assert b"mcformat" in response.content


async def test_embed_returns_400_for_private_ip(client):
    response = await client.get("/v1/server/127.0.0.1/embed")
    assert response.status_code == 400


async def test_embed_returns_400_for_blocked_port(client):
    response = await client.get("/v1/server/mc.example.com:22/embed")
    assert response.status_code == 400


async def test_embed_offline_server_returns_200(client):
    with patch(
        "motd_embed_api.main.get_cached_server_info", return_value=OFFLINE_SERVER_INFO
    ):
        response = await client.get("/v1/server/mc.example.com/embed")
    assert response.status_code == 200


async def test_embed_has_security_headers(client):
    with patch(
        "motd_embed_api.main.get_cached_server_info", return_value=ONLINE_SERVER_INFO
    ):
        response = await client.get("/v1/server/mc.example.com/embed")
    assert response.headers.get("x-content-type-options") == "nosniff"


# ---------------------------------------------------------------------------
# Image endpoint
# ---------------------------------------------------------------------------


async def test_image_returns_png(client):
    with patch(
        "motd_embed_api.main.get_cached_server_info", return_value=ONLINE_SERVER_INFO
    ):
        response = await client.get("/v1/server/mc.example.com/image")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


async def test_image_body_is_valid_png(client):
    from PIL import Image
    import io

    with patch(
        "motd_embed_api.main.get_cached_server_info", return_value=ONLINE_SERVER_INFO
    ):
        response = await client.get("/v1/server/mc.example.com/image")
    img = Image.open(io.BytesIO(response.content))
    assert img.format == "PNG"
    assert img.size == (500, 90)


async def test_image_no_longer_returns_501(client):
    with patch(
        "motd_embed_api.main.get_cached_server_info", return_value=ONLINE_SERVER_INFO
    ):
        response = await client.get("/v1/server/mc.example.com/image")
    assert response.status_code != 501


async def test_image_returns_400_for_private_ip(client):
    response = await client.get("/v1/server/192.168.1.1/image")
    assert response.status_code == 400


async def test_image_has_security_headers(client):
    with patch(
        "motd_embed_api.main.get_cached_server_info", return_value=ONLINE_SERVER_INFO
    ):
        response = await client.get("/v1/server/mc.example.com/image")
    assert "x-content-type-options" in response.headers
