# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastAPI-based web service that generates embeddable HTML for Minecraft server MOTDs (Message of the Day). The API fetches live server status, parses Minecraft formatting codes, and generates styled HTML embeds.

## Development Commands

**Run the development server:**
```bash
# With auto-reload for development
RELOAD=true uv run motd-embed-api

# Or directly with uv
uv run motd-embed-api
```

**Install dependencies:**
```bash
uv sync
```

**Run with uvicorn directly:**
```bash
uv run uvicorn motd_embed_api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Docker deployment:**
```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build manually
docker build -t motd-embed-api .
docker run -p 8000:8000 motd-embed-api

# View logs
docker-compose logs -f
```

## Architecture

### Request Flow
1. **API Endpoint** (`main.py`) - FastAPI routes receive embed requests
2. **Cache Layer** (`cache.py`) - 30-second in-memory cache reduces server queries
3. **Server Status** (`server.py`) - Fetches live Minecraft server data via mcstatus library
4. **MOTD Parsing** (`motd_parser.py`) - Converts § formatting codes to HTML/CSS
5. **HTML Generation** (`html_generator.py`) - Combines parsed data into embeddable HTML

### Key Components

**`server.py`**: Minecraft server communication
- `get_server_info(ip)` - Main entry point for server data
- Returns dict with: online status, MOTD text, players, version, favicon
- Handles multiple MOTD formats (string, dict with 'text'/'extra', objects with attributes)
- Default port: 25565, supports `host:port` format

**`motd_parser.py`**: Minecraft formatting code parser
- Converts `§` codes (§a, §l, §r, etc.) to HTML spans with CSS classes
- Color codes (0-9, a-f) reset previous colors but preserve formatting
- Format codes (k, l, m, n, o) are additive
- §r resets all formatting
- Handles both legacy § codes and JSON text components

**`cache.py`**: Simple TTL-based caching
- Global `_server_cache` instance with 30-second TTL
- `get_cached_server_info(ip, fetch_func)` wraps server fetching
- Reduces load on Minecraft servers for repeated requests

**`html_generator.py`**: Embed HTML construction
- Creates complete HTML document with inline styles
- References `/static` for CSS and background images
- Falls back to default icon if server provides no favicon
- Uses data URI for server-provided favicons (base64)

### Static Assets
The `static/` directory contains:
- `motd-embed.css` - Minecraft-themed styling (mcformat classes)
- `minecraft-background-dark-160x-K223BAAL.png` - Repeating background texture
- `unknown_server.jpg` - Fallback server icon

### API Endpoints

**`GET /v1/server/{ip}/embed`**
- Returns HTML embed for server MOTD
- `{ip}` can be `hostname` or `hostname:port`
- Response: HTML with embedded styles and server status
- Uses caching to avoid rate-limiting

**`GET /v1/server/{ip}/image`**
- Placeholder for future image generation endpoint
- Currently returns JSON with "not_implemented" status

**`GET /health`**
- Health check endpoint
- Returns `{"status": "ok"}`

## Code Patterns

### Error Handling
- `ValueError` for invalid input (400 response)
- Generic exceptions caught as 500 errors
- Server offline returns valid response with "Server Offline" MOTD

### MOTD Format Detection
The parser handles three common MOTD formats from mcstatus:
1. Plain string: `"Welcome to my server"`
2. Dict with text/extra: `{"text": "Welcome", "extra": [...]}`
3. Object with attributes: Object with `.text` and `.extra` properties

### CSS Class Structure
- `mcformat` - Base class for all formatted text
- `mcformat-{color}` - Color classes (e.g., `mcformat-red`, `mcformat-blue`)
- `mcformat-{format}` - Format classes (e.g., `mcformat-bold`, `mcformat-italic`)
- `mcformat-code` - Displays § codes themselves
- `mcformat-code-hidden` - Parent class to hide codes (used in output)

## Dependencies

- **fastapi** - Web framework
- **uvicorn** - ASGI server
- **mcstatus** - Minecraft server status protocol
- **jinja2** - Template engine (FastAPI dependency)
- Uses **uv** for dependency management (see pyproject.toml)

## Configuration

Configuration via environment variables (see `.env.example`):

**Server Configuration:**
- `HOST` - Host to bind to (default: `0.0.0.0`)
- `PORT` - Server port (default: `8000`)
- `RELOAD` - Enable auto-reload for development (default: `false`)
- `LOG_LEVEL` - Logging level: debug, info, warning, error, critical (default: `info`)

**CORS Configuration:**
- `ALLOWED_ORIGINS` - Comma-separated allowed origins (default: `*`)
  - For production, set to specific domains: `https://example.com,https://app.example.com`
  - Using `*` with credentials is a security risk (now disabled)

**Hardcoded values:**
- Cache TTL: 30 seconds (in `cache.py`)
- Minecraft server timeout: 5 seconds (in `server.py`)
- Static files path: `{project_root}/static/`

**Environment file:**
```bash
cp .env.example .env
# Edit .env with your production settings
```
