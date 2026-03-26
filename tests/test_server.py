"""Tests for server address validation and status fetching"""

import socket
from unittest.mock import MagicMock, patch

import pytest

from motd_embed_api.server import (
    fetch_server_status,
    get_server_info,
    is_private_ip,
    parse_server_address,
    validate_server_address,
)


# --- is_private_ip ---


def test_loopback_is_private():
    assert is_private_ip("127.0.0.1") is True


def test_rfc1918_is_private():
    assert is_private_ip("192.168.1.1") is True
    assert is_private_ip("10.0.0.1") is True
    assert is_private_ip("172.16.0.1") is True


def test_public_ip_is_not_private():
    # 8.8.8.8 is a well-known public IP
    assert is_private_ip("8.8.8.8") is False


def test_unresolvable_hostname_raises():
    with pytest.raises(ValueError, match="Cannot resolve"):
        is_private_ip("this.hostname.does.not.exist.invalid")


# --- validate_server_address ---


def test_blocked_port_raises():
    with pytest.raises(ValueError, match="not allowed"):
        validate_server_address("mc.example.com", 22)


def test_http_port_blocked():
    with pytest.raises(ValueError):
        validate_server_address("mc.example.com", 80)


def test_private_ip_blocked():
    with pytest.raises(ValueError, match="private"):
        validate_server_address("127.0.0.1", 25565)


def test_valid_public_address_passes():
    # Should not raise; 8.8.8.8:25565 is public and port not blocked
    validate_server_address("8.8.8.8", 25565)


def test_invalid_port_range():
    with pytest.raises(ValueError, match="Port must be between"):
        validate_server_address("mc.example.com", 0)
    with pytest.raises(ValueError, match="Port must be between"):
        validate_server_address("mc.example.com", 99999)


# --- parse_server_address ---


def test_parse_host_only_defaults_to_25565():
    with patch("motd_embed_api.server.validate_server_address"):
        host, port = parse_server_address("mc.example.com")
    assert host == "mc.example.com"
    assert port == 25565


def test_parse_host_colon_port():
    with patch("motd_embed_api.server.validate_server_address"):
        host, port = parse_server_address("mc.example.com:19132")
    assert host == "mc.example.com"
    assert port == 19132


def test_parse_invalid_port_string():
    with pytest.raises(ValueError, match="Invalid port"):
        parse_server_address("mc.example.com:notaport")


def test_parse_address_too_long():
    long_host = "a" * 300
    with pytest.raises(ValueError, match="too long"):
        parse_server_address(long_host, max_address_length=253)


def test_parse_private_ip_raises():
    with pytest.raises(ValueError):
        parse_server_address("127.0.0.1")


# --- fetch_server_status ---


def test_fetch_returns_none_on_connection_refused():
    with patch(
        "motd_embed_api.server.parse_server_address",
        return_value=("mc.example.com", 25565),
    ):
        with patch("motd_embed_api.server.JavaServer") as MockServer:
            MockServer.return_value.status.side_effect = ConnectionRefusedError
            result = fetch_server_status("mc.example.com")
    assert result is None


def test_fetch_returns_none_on_timeout():
    with patch(
        "motd_embed_api.server.parse_server_address",
        return_value=("mc.example.com", 25565),
    ):
        with patch("motd_embed_api.server.JavaServer") as MockServer:
            MockServer.return_value.status.side_effect = socket.timeout
            result = fetch_server_status("mc.example.com")
    assert result is None


def test_fetch_propagates_value_error_from_validation():
    with patch(
        "motd_embed_api.server.parse_server_address", side_effect=ValueError("bad")
    ):
        with pytest.raises(ValueError, match="bad"):
            fetch_server_status("127.0.0.1")


def test_fetch_passes_timeout_to_java_server():
    with patch(
        "motd_embed_api.server.parse_server_address",
        return_value=("mc.example.com", 25565),
    ):
        with patch("motd_embed_api.server.JavaServer") as MockServer:
            mock_status = MagicMock()
            mock_status.description = "A server"
            MockServer.return_value.status.return_value = mock_status
            fetch_server_status("mc.example.com", timeout=3.0)
    MockServer.assert_called_once_with("mc.example.com", 25565, timeout=3.0)


# --- get_server_info ---


def test_get_server_info_returns_offline_on_none():
    with patch("motd_embed_api.server.fetch_server_status", return_value=None):
        info = get_server_info("mc.example.com")
    assert info["online"] is False
    assert info["motd"] == "Server Offline"


def test_get_server_info_string_motd():
    mock_status = MagicMock()
    mock_status.description = "Hello World"
    mock_status.version.name = "1.20.1"
    mock_status.players.online = 3
    mock_status.players.max = 10
    mock_status.icon = None

    with patch("motd_embed_api.server.fetch_server_status", return_value=mock_status):
        info = get_server_info("mc.example.com")

    assert info["online"] is True
    assert info["motd"] == "Hello World"
    assert info["players_online"] == 3
