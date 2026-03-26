"""Tests for Pillow-based PNG image generation"""

import io

from PIL import Image

from motd_embed_api.image_generator import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    generate_server_image,
)

# A minimal 1×1 transparent PNG encoded as a data URI
_1X1_PNG_B64 = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def _open_image(buf: io.BytesIO) -> Image.Image:
    buf.seek(0)
    return Image.open(buf)


def test_returns_bytes_io():
    result = generate_server_image("mc.example.com", "Hello World")
    assert isinstance(result, io.BytesIO)


def test_output_is_valid_image():
    buf = generate_server_image("mc.example.com", "Hello World")
    img = _open_image(buf)
    assert img is not None


def test_output_format_is_png():
    buf = generate_server_image("mc.example.com", "Hello World")
    img = _open_image(buf)
    assert img.format == "PNG"


def test_output_dimensions():
    buf = generate_server_image("mc.example.com", "Hello World")
    img = _open_image(buf)
    assert img.size == (CANVAS_WIDTH, CANVAS_HEIGHT)


def test_works_without_favicon():
    buf = generate_server_image("mc.example.com", "Hello World", favicon=None)
    img = _open_image(buf)
    assert img.size == (CANVAS_WIDTH, CANVAS_HEIGHT)


def test_works_with_valid_favicon():
    buf = generate_server_image("mc.example.com", "Hello World", favicon=_1X1_PNG_B64)
    img = _open_image(buf)
    assert img.size == (CANVAS_WIDTH, CANVAS_HEIGHT)


def test_works_with_invalid_favicon_falls_back():
    buf = generate_server_image(
        "mc.example.com",
        "Hello World",
        favicon="data:image/png;base64,BAD!!!",
        favicon_max_bytes=150_000,
    )
    img = _open_image(buf)
    assert img.size == (CANVAS_WIDTH, CANVAS_HEIGHT)


def test_motd_with_color_codes_does_not_crash():
    buf = generate_server_image(
        "mc.example.com",
        "§aGreen §lBold §rReset Normal",
    )
    img = _open_image(buf)
    assert img.size == (CANVAS_WIDTH, CANVAS_HEIGHT)


def test_motd_with_newline_does_not_crash():
    buf = generate_server_image("mc.example.com", "Line 1\nLine 2")
    img = _open_image(buf)
    assert img.size == (CANVAS_WIDTH, CANVAS_HEIGHT)


def test_buffer_is_seeked_to_start():
    buf = generate_server_image("mc.example.com", "test")
    assert buf.tell() == 0


def test_favicon_rejected_when_exceeds_max_bytes():
    # Favicon that exceeds the limit should fall back gracefully (no exception)
    buf = generate_server_image(
        "mc.example.com",
        "Hello",
        favicon=_1X1_PNG_B64,
        favicon_max_bytes=10,  # tiny limit — valid URI but exceeds budget
    )
    img = _open_image(buf)
    assert img.size == (CANVAS_WIDTH, CANVAS_HEIGHT)


def test_favicon_rejected_for_disallowed_mime_type():
    # data:text/html; is not an allowed image type
    bad = "data:text/html;base64,PHNjcmlwdD4="
    buf = generate_server_image("mc.example.com", "Hello", favicon=bad)
    img = _open_image(buf)
    assert img.size == (CANVAS_WIDTH, CANVAS_HEIGHT)
