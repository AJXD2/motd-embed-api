"""Tests for HTML generation and favicon validation"""

import base64


from motd_embed_api.html_generator import generate_embed_html, validate_favicon

# A minimal 1×1 transparent PNG encoded as a valid data URI
_1X1_PNG_B64 = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


# --- validate_favicon ---


def test_valid_png_favicon_passes():
    assert validate_favicon(_1X1_PNG_B64) is True


def test_empty_string_fails():
    assert validate_favicon("") is False


def test_non_data_uri_fails():
    assert validate_favicon("https://example.com/icon.png") is False


def test_html_mime_type_rejected():
    payload = base64.b64encode(b"<html></html>").decode()
    assert validate_favicon(f"data:text/html;base64,{payload}") is False


def test_missing_base64_marker_fails():
    assert validate_favicon("data:image/png,notbase64") is False


def test_invalid_base64_payload_fails():
    assert validate_favicon("data:image/png;base64,!!!invalid!!!") is False


def test_oversized_favicon_fails():
    # Build a favicon that exceeds max_bytes
    payload = "A" * 200_000
    favicon = f"data:image/png;base64,{payload}"
    assert validate_favicon(favicon, max_bytes=150_000) is False


def test_custom_max_bytes_respected():
    # Same valid favicon but with a tiny max_bytes
    assert validate_favicon(_1X1_PNG_B64, max_bytes=10) is False


def test_jpeg_favicon_accepted():
    # Encode some bytes as jpeg data URI (content doesn't matter for format check)
    payload = base64.b64encode(b"\xff\xd8\xff").decode()
    favicon = f"data:image/jpeg;base64,{payload}"
    assert validate_favicon(favicon) is True


# --- generate_embed_html ---


def test_html_contains_server_name():
    html = generate_embed_html("mc.example.com", "<span>MOTD</span>")
    assert "mc.example.com" in html


def test_server_name_xss_escaped():
    html = generate_embed_html("<script>alert(1)</script>", "motd")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_html_uses_fallback_icon_when_no_favicon():
    html = generate_embed_html("mc.example.com", "motd", favicon=None)
    assert "unknown_server.jpg" in html


def test_html_uses_favicon_when_valid():
    html = generate_embed_html("mc.example.com", "motd", favicon=_1X1_PNG_B64)
    assert "data:image/png" in html
    assert "unknown_server.jpg" not in html


def test_html_falls_back_on_invalid_favicon():
    html = generate_embed_html(
        "mc.example.com", "motd", favicon="data:text/html;base64,bad"
    )
    assert "unknown_server.jpg" in html


def test_html_contains_motd():
    html = generate_embed_html("mc.example.com", "<span>Welcome!</span>")
    assert "Welcome!" in html


def test_html_empty_motd_shows_no_motd():
    html = generate_embed_html("mc.example.com", "")
    assert "No MOTD" in html


def test_html_is_valid_doctype():
    html = generate_embed_html("mc.example.com", "motd")
    assert html.strip().startswith("<!DOCTYPE html>")
