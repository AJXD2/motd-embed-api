"""Pillow-based PNG image generation for Minecraft server MOTD embeds"""

import base64
import io
import logging
import os
import re
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Allow STATIC_DIR env var override so Docker volume mounts and
# non-standard layouts work without code changes.
_STATIC_DIR = Path(os.environ.get("STATIC_DIR", "")) or (
    Path(__file__).parent.parent.parent / "static"
)
_BG_IMAGE = _STATIC_DIR / "minecraft-background-dark-160x-K223BAAL.png"
_FALLBACK_ICON = _STATIC_DIR / "unknown_server.jpg"
# Optional: place a Minecraft-style TTF at static/Minecraft.ttf for best results.
_MINECRAFT_FONT = _STATIC_DIR / "Minecraft.ttf"

# Canvas dimensions
CANVAS_WIDTH = 500
CANVAS_HEIGHT = 90

# Layout positions
ICON_X, ICON_Y = 12, 13
ICON_SIZE = 64
TEXT_X = 82
NAME_Y = 13
MOTD_Y = 32
LINE_HEIGHT = 18

# Minecraft § color code → RGB
_COLOR_RGB: dict[str, tuple[int, int, int]] = {
    "0": (0, 0, 0),
    "1": (0, 0, 170),
    "2": (0, 170, 0),
    "3": (0, 170, 170),
    "4": (170, 0, 0),
    "5": (170, 0, 170),
    "6": (255, 170, 0),
    "7": (170, 170, 170),
    "8": (85, 85, 85),
    "9": (85, 85, 255),
    "a": (85, 255, 85),
    "b": (85, 255, 255),
    "c": (255, 85, 85),
    "d": (255, 85, 255),
    "e": (255, 255, 85),
    "f": (255, 255, 255),
}
_DEFAULT_COLOR: tuple[int, int, int] = (255, 255, 255)
_NAME_COLOR: tuple[int, int, int] = (170, 170, 170)

_ALLOWED_FAVICON_PREFIXES = (
    "data:image/png",
    "data:image/jpeg",
    "data:image/jpg",
    "data:image/gif",
    "data:image/webp",
)


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load Minecraft TTF if available, fall back to PIL default."""
    try:
        return ImageFont.truetype(str(_MINECRAFT_FONT), size=size)
    except Exception:
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            # Older Pillow: load_default doesn't accept size=
            return ImageFont.load_default()


def _make_background() -> Image.Image:
    """Create a tiled Minecraft background canvas."""
    canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT))
    try:
        tile = Image.open(_BG_IMAGE).convert("RGBA")
        tw, th = tile.size
        for y in range(0, CANVAS_HEIGHT, th):
            for x in range(0, CANVAS_WIDTH, tw):
                canvas.paste(tile, (x, y))
    except Exception:
        logger.debug(
            "Background image unavailable (%s), using solid fallback", _BG_IMAGE
        )
        canvas = Image.new(
            "RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), color=(26, 26, 26, 255)
        )
    return canvas


def _load_icon(favicon: Optional[str], max_bytes: int = 150_000) -> Image.Image:
    """
    Decode a base64 favicon data URI and return a 64×64 RGBA image.
    Falls back to unknown_server.jpg, then a solid grey square, on any error.
    """
    if (
        favicon
        and any(favicon.startswith(p) for p in _ALLOWED_FAVICON_PREFIXES)
        and "base64," in favicon
        and len(favicon) <= max_bytes
    ):
        try:
            _, b64 = favicon.split("base64,", 1)
            data = base64.b64decode(b64, validate=True)
            img = Image.open(io.BytesIO(data)).convert("RGBA")
            return img.resize((ICON_SIZE, ICON_SIZE), Image.NEAREST)
        except Exception as e:
            logger.debug("Failed to decode favicon: %s", e)

    try:
        img = Image.open(_FALLBACK_ICON).convert("RGBA")
        return img.resize((ICON_SIZE, ICON_SIZE), Image.NEAREST)
    except Exception:
        logger.debug("Fallback icon unavailable (%s), using solid grey", _FALLBACK_ICON)
        return Image.new("RGBA", (ICON_SIZE, ICON_SIZE), color=(100, 100, 100, 255))


def _draw_motd(
    draw: ImageDraw.ImageDraw,
    motd_text: str,
    x: int,
    y: int,
    font_size: int = 12,
) -> None:
    """Draw MOTD text respecting § color codes."""
    parts = re.split(r"(§[0-9a-fk-or])", motd_text, flags=re.IGNORECASE)
    font = _get_font(font_size)

    current_color = _DEFAULT_COLOR
    x_cursor = x
    y_cursor = y

    for part in parts:
        if not part:
            continue

        if part.startswith("§") and len(part) == 2:
            code = part[1].lower()
            if code == "r":
                current_color = _DEFAULT_COLOR
            elif code in _COLOR_RGB:
                current_color = _COLOR_RGB[code]
            # Format codes (bold/italic/etc.) are intentionally ignored —
            # Pillow TTF doesn't support per-segment style switching easily.
            continue

        # Split on newlines
        lines = part.split("\n")
        for i, line in enumerate(lines):
            if i > 0:
                x_cursor = x
                y_cursor += LINE_HEIGHT
            if line:
                draw.text((x_cursor, y_cursor), line, fill=current_color, font=font)
                try:
                    bbox = draw.textbbox((x_cursor, y_cursor), line, font=font)
                    x_cursor = bbox[2]
                except AttributeError:
                    # Older Pillow: estimate advance width
                    x_cursor += len(line) * (font_size // 2)


def generate_server_image(
    server_name: str,
    motd_text: str,
    favicon: Optional[str] = None,
    favicon_max_bytes: int = 150_000,
) -> io.BytesIO:
    """
    Render a Minecraft server MOTD as a 500×90 PNG image.

    Args:
        server_name: Server address / display name
        motd_text: Raw MOTD text (may contain § formatting codes)
        favicon: Base64 data URI of the server icon (optional)
        favicon_max_bytes: Maximum allowed favicon size in bytes

    Returns:
        BytesIO buffer positioned at 0, containing PNG data
    """
    canvas = _make_background()
    draw = ImageDraw.Draw(canvas)

    icon = _load_icon(favicon, max_bytes=favicon_max_bytes)
    canvas.paste(icon, (ICON_X, ICON_Y), mask=icon)

    name_font = _get_font(14)
    draw.text((TEXT_X, NAME_Y), server_name, fill=_NAME_COLOR, font=name_font)

    _draw_motd(draw, motd_text, TEXT_X, MOTD_Y, font_size=12)

    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return buf
