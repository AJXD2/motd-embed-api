"""HTML generation for Minecraft MOTD embeds"""
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def validate_favicon(favicon: str) -> bool:
    """
    Validate that a favicon is a safe data URI.

    Args:
        favicon: Base64 favicon data URI

    Returns:
        True if valid and safe, False otherwise
    """
    if not favicon:
        return False

    # Must be a data URI
    if not favicon.startswith("data:"):
        logger.warning(f"Favicon does not start with data: URI scheme")
        return False

    # Must be an image type
    allowed_types = [
        "data:image/png",
        "data:image/jpeg",
        "data:image/jpg",
        "data:image/gif",
        "data:image/webp",
    ]

    if not any(favicon.startswith(allowed_type) for allowed_type in allowed_types):
        logger.warning(f"Favicon is not an allowed image type")
        return False

    # Should contain base64 marker
    if "base64," not in favicon:
        logger.warning(f"Favicon does not contain base64 marker")
        return False

    # Basic length check (prevent DoS via huge images)
    # Minecraft favicons are typically small (64x64 PNG ~5-20KB base64)
    # Allow up to 100KB base64 to be safe
    if len(favicon) > 150000:  # ~100KB base64
        logger.warning(f"Favicon exceeds maximum size")
        return False

    return True


def generate_embed_html(
    server_name: str,
    motd_html: str,
    favicon: Optional[str] = None,
    base_url: str = "/static"
) -> str:
    """
    Generate HTML embed for Minecraft server MOTD.
    
    Args:
        server_name: Name of the server
        motd_html: Parsed MOTD HTML with formatting
        favicon: Base64 encoded favicon (optional)
        base_url: Base URL for static assets
        
    Returns:
        Complete HTML document string
    """
    # Determine icon source
    if favicon and validate_favicon(favicon):
        # Use validated data URI for server favicon
        icon_src = favicon
    else:
        # Use fallback icon if no favicon or validation failed
        if favicon and not validate_favicon(favicon):
            logger.warning(f"Invalid or unsafe favicon rejected, using fallback")
        icon_src = f"{base_url}/unknown_server.jpg"
    
    # Escape server name for HTML
    safe_server_name = (
        server_name.replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
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
