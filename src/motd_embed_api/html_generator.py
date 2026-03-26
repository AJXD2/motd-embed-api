"""HTML generation for Minecraft MOTD embeds"""

import base64
import logging
from typing import Optional

from .metrics import FAVICON_REJECTIONS_TOTAL

logger = logging.getLogger(__name__)


def validate_favicon(favicon: str, max_bytes: int = 150_000) -> bool:
    """
    Validate that a favicon is a safe data URI with valid base64 content.

    Args:
        favicon: Base64 favicon data URI
        max_bytes: Maximum allowed byte length of the full data URI string

    Returns:
        True if valid and safe, False otherwise
    """
    if not favicon:
        return False

    if not favicon.startswith("data:"):
        logger.warning("Favicon does not start with data: URI scheme")
        FAVICON_REJECTIONS_TOTAL.inc()
        return False

    allowed_types = [
        "data:image/png",
        "data:image/jpeg",
        "data:image/jpg",
        "data:image/gif",
        "data:image/webp",
    ]

    if not any(favicon.startswith(t) for t in allowed_types):
        logger.warning("Favicon is not an allowed image type")
        FAVICON_REJECTIONS_TOTAL.inc()
        return False

    if "base64," not in favicon:
        logger.warning("Favicon does not contain base64 marker")
        FAVICON_REJECTIONS_TOTAL.inc()
        return False

    if len(favicon) > max_bytes:
        logger.warning("Favicon exceeds maximum size")
        FAVICON_REJECTIONS_TOTAL.inc()
        return False

    # Verify the base64 payload is actually valid
    try:
        _, b64_data = favicon.split("base64,", 1)
        base64.b64decode(b64_data, validate=True)
    except Exception:
        logger.warning("Favicon contains invalid base64 data")
        FAVICON_REJECTIONS_TOTAL.inc()
        return False

    return True


def generate_embed_html(
    server_name: str,
    motd_html: str,
    favicon: Optional[str] = None,
    base_url: str = "/static",
    favicon_max_bytes: int = 150_000,
) -> str:
    """
    Generate HTML embed for Minecraft server MOTD.

    Args:
        server_name: Name of the server
        motd_html: Parsed MOTD HTML with formatting
        favicon: Base64 encoded favicon (optional)
        base_url: Base URL for static assets
        favicon_max_bytes: Maximum favicon size in bytes

    Returns:
        Complete HTML document string
    """
    if favicon and validate_favicon(favicon, max_bytes=favicon_max_bytes):
        icon_src = favicon
    else:
        if favicon:
            logger.warning("Invalid or unsafe favicon rejected, using fallback")
        icon_src = f"{base_url}/unknown_server.jpg"

    safe_server_name = (
        server_name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_server_name} - MOTD</title>
    <link rel="stylesheet" href="{base_url}/motd-embed.css">
    <style>
        * {{
            box-sizing: border-box;
        }}
        html, body {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
        }}
        body {{
            display: block;
            background-image: url({base_url}/minecraft-background-dark-160x-K223BAAL.png);
            background-repeat: repeat;
            background-size: 80px;
            image-rendering: pixelated;
        }}
    </style>
</head>
<body>
    <div class="editor-container">
        <div class="editor-inner mcformat-background mcformat-motd">
            <div class="server-icon">
                <img width="64" height="64" src="{icon_src}" alt="Minecraft server icon" style="width: 64px; height: 64px; display: block;">
            </div>
            <div class="text">
                <div class="name">{safe_server_name}</div>
                <div class="editor">
                    <div class="mcformat-editor">
                        <div class="mcformat-output mcformat-code-hidden">
                            <span class="mcformat-wrapper">
                                {motd_html if motd_html else '<span class="mcformat mcformat-reset">No MOTD</span>'}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""

    return html
