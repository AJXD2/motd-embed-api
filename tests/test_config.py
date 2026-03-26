"""Tests for Settings validation and configuration"""

import pytest
from pydantic import ValidationError

from motd_embed_api.config import Settings


# ---------------------------------------------------------------------------
# Rate limit format validator
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "30/minute",
        "10/second",
        "1/hour",
        "1000/day",
    ],
)
def test_valid_rate_limit_formats(value):
    s = Settings(rate_limit_embed=value)
    assert s.rate_limit_embed == value


@pytest.mark.parametrize(
    "bad_value",
    [
        "30/min",  # abbreviated period
        "30per/minute",  # extra text
        "/minute",  # missing count
        "30/",  # missing period
        "fast",  # completely wrong
        "30/MINUTE",  # uppercase period
        "0.5/minute",  # non-integer count
    ],
)
def test_invalid_rate_limit_raises(bad_value):
    with pytest.raises(ValidationError):
        Settings(rate_limit_embed=bad_value)


# ---------------------------------------------------------------------------
# allowed_origins property
# ---------------------------------------------------------------------------


def test_allowed_origins_single():
    s = Settings(ALLOWED_ORIGINS="https://example.com")
    assert s.allowed_origins == ["https://example.com"]


def test_allowed_origins_multiple():
    s = Settings(ALLOWED_ORIGINS="https://a.com, https://b.com , https://c.com")
    assert s.allowed_origins == ["https://a.com", "https://b.com", "https://c.com"]


def test_allowed_origins_wildcard():
    s = Settings(ALLOWED_ORIGINS="*")
    assert s.allowed_origins == ["*"]


# ---------------------------------------------------------------------------
# static_dir
# ---------------------------------------------------------------------------


def test_static_dir_defaults_empty():
    s = Settings()
    assert s.static_dir == ""


def test_static_dir_can_be_set():
    s = Settings(static_dir="/custom/path")
    assert s.static_dir == "/custom/path"


# ---------------------------------------------------------------------------
# Defaults sanity check
# ---------------------------------------------------------------------------


def test_default_cache_ttl():
    s = Settings()
    assert s.cache_ttl_seconds == 30


def test_default_server_timeout():
    s = Settings()
    assert s.server_timeout == 5.0


def test_metrics_enabled_by_default():
    s = Settings()
    assert s.metrics_enabled is True
