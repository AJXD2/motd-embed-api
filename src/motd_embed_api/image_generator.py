"""PNG image generation for Minecraft MOTD embeds using Pillow + fonttools"""
import os
import base64
from io import BytesIO
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

# Path to static assets
_STATIC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static"
)

# Layout constants (matching motd-embed.css)
CANVAS_WIDTH = 650
PAD_TOP = 12
PAD_LEFT = 12
PAD_RIGHT = 20
PAD_BOTTOM = 12
ICON_SIZE = 64
ICON_MARGIN_RIGHT = 6
TEXT_X = PAD_LEFT + ICON_SIZE + ICON_MARGIN_RIGHT  # 82
FONT_SIZE = 16
LINE_HEIGHT = 18
NAME_MARGIN_TOP = 1
MOTD_MARGIN_TOP = 6
SHADOW_OFFSET = 2
NAME_COLOR = (170, 170, 170)
NAME_SHADOW = (42, 42, 42)

# Font cache: keyed by ("normal" | "bold", size)
_font_cache: dict = {}


def _load_font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    """Convert a WOFF2 font to in-memory TTF and load it with Pillow."""
    key = (weight, size)
    if key in _font_cache:
        return _font_cache[key]

    from fontTools.ttLib import TTFont

    woff2_map = {
        "normal": "minecraft-normal-0000-07ff-MVYMY4PV.woff2",
        "bold": "minecraft-bold-0000-07ff-RJCHNFH7.woff2",
    }
    path = os.path.join(_STATIC_DIR, woff2_map[weight])
    tt = TTFont(path)
    buf = BytesIO()
    tt.save(buf)
    buf.seek(0)
    font = ImageFont.truetype(buf, size=size)
    _font_cache[key] = font
    return font


# Background tile cache
_bg_tile: Optional[Image.Image] = None


def _get_bg_tile() -> Image.Image:
    global _bg_tile
    if _bg_tile is None:
        path = os.path.join(_STATIC_DIR, "minecraft-background-dark-160x-K223BAAL.png")
        tile = Image.open(path).convert("RGB")
        # CSS background-size: 80px — scale to 80px
        _bg_tile = tile.resize((80, 80), Image.NEAREST)
    return _bg_tile


def _tile_background(canvas: Image.Image) -> None:
    """Tile the Minecraft background texture across the canvas."""
    tile = _get_bg_tile()
    tw, th = tile.size
    for y in range(0, canvas.height, th):
        for x in range(0, canvas.width, tw):
            canvas.paste(tile, (x, y))


def _load_favicon(favicon_b64: Optional[str]) -> Image.Image:
    """Load server favicon from base64 data URI, or fall back to unknown_server.jpg."""
    if favicon_b64 and favicon_b64.startswith("data:image/") and "base64," in favicon_b64:
        try:
            b64_data = favicon_b64.split("base64,", 1)[1]
            img_bytes = base64.b64decode(b64_data)
            img = Image.open(BytesIO(img_bytes)).convert("RGBA")
            return img.resize((ICON_SIZE, ICON_SIZE), Image.NEAREST)
        except Exception:
            pass
    fallback = os.path.join(_STATIC_DIR, "unknown_server.jpg")
    img = Image.open(fallback).convert("RGBA")
    return img.resize((ICON_SIZE, ICON_SIZE), Image.NEAREST)


def _draw_text_shadowed(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    font: ImageFont.FreeTypeFont,
    color: tuple,
    shadow: tuple,
) -> int:
    """Draw text with a 2px drop shadow. Returns the pixel width of the text."""
    draw.text((x + SHADOW_OFFSET, y + SHADOW_OFFSET), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=color)
    bbox = font.getbbox(text)
    return bbox[2] - bbox[0]


def generate_server_image(
    server_name: str,
    motd_segments: list,
    favicon_b64: Optional[str] = None,
) -> bytes:
    """
    Generate a PNG image of the Minecraft server MOTD embed.

    Args:
        server_name: Server IP / name displayed above the MOTD
        motd_segments: Output of parse_motd_to_segments()
        favicon_b64: Base64 data URI of the server favicon (optional)

    Returns:
        Raw PNG bytes
    """
    font_normal = _load_font("normal", FONT_SIZE)
    font_bold = _load_font("bold", FONT_SIZE)

    # --- Calculate canvas height ---
    # Measure server name height
    name_bbox = font_normal.getbbox(server_name or " ")
    name_h = name_bbox[3] - name_bbox[1]

    # Count MOTD lines
    motd_lines = 1
    for seg in motd_segments:
        motd_lines += seg["text"].count("\n")
    motd_h = motd_lines * LINE_HEIGHT

    text_block_h = NAME_MARGIN_TOP + name_h + MOTD_MARGIN_TOP + motd_h
    canvas_h = max(
        PAD_TOP + ICON_SIZE + PAD_BOTTOM,
        PAD_TOP + text_block_h + PAD_BOTTOM,
    )

    # --- Build canvas ---
    canvas = Image.new("RGB", (CANVAS_WIDTH, canvas_h))
    _tile_background(canvas)

    # Paste favicon
    icon = _load_favicon(favicon_b64)
    if icon.mode == "RGBA":
        canvas.paste(icon, (PAD_LEFT, PAD_TOP), mask=icon.split()[3])
    else:
        canvas.paste(icon, (PAD_LEFT, PAD_TOP))

    draw = ImageDraw.Draw(canvas)

    # --- Draw server name ---
    name_y = PAD_TOP + NAME_MARGIN_TOP
    _draw_text_shadowed(draw, TEXT_X, name_y, server_name, font_normal, NAME_COLOR, NAME_SHADOW)

    # --- Draw MOTD segments ---
    motd_y = name_y + name_h + MOTD_MARGIN_TOP
    cursor_x = TEXT_X

    for seg in motd_segments:
        if seg["text"] == "\n":
            cursor_x = TEXT_X
            motd_y += LINE_HEIGHT
            continue

        font = font_bold if seg["bold"] else font_normal
        text = seg["text"]
        color = seg["color"]
        shadow = seg["shadow"]

        # Handle text that may wrap (split on spaces, or just draw and advance)
        w = _draw_text_shadowed(draw, cursor_x, motd_y, text, font, color, shadow)
        cursor_x += w

    # --- Encode to PNG ---
    out = BytesIO()
    canvas.save(out, format="PNG")
    return out.getvalue()
