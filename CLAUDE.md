# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastAPI-based web service that generates embeddable HTML and PNG images for Minecraft server MOTDs (Message of the Day). The API fetches live server status, parses Minecraft formatting codes, and returns styled HTML embeds or rasterised PNG images.

## Development Commands

**Run the development server:**
```bash
RELOAD=true uv run motd-embed-api
```

**Install dependencies:**
```bash
uv sync
```

**Run tests:**
```bash
uv run pytest
# With coverage
uv run pytest --cov=motd_embed_api
```

**Docker deployment:**
```bash
docker-compose up -d
docker-compose logs -f
```

## Architecture

### Request Flow
1. **Middleware** (`middleware.py`) — RequestID injection, security headers, structured JSON logging
2. **Rate limiter** (`main.py`) — Per-IP limits via slowapi
3. **API Endpoint** (`main.py`) — FastAPI routes; validates input, orchestrates response
4. **Cache Layer** (`cache.py`) — TTL+LRU cache (default 30 s) reduces live queries
5. **Server Status** (`server.py`) — Fetches live Minecraft server data via mcstatus; SSRF-safe
6. **MOTD Parsing** (`motd_parser.py`) — Converts § formatting codes to HTML spans
7. **HTML / Image Generation** (`html_generator.py`, `image_generator.py`) — Renders output

### Key Components

**`config.py`**: Pydantic-settings `Settings` class
- All tunable values live here; loaded once via `get_settings()` (lru_cache)
- Rate limit strings validated at startup: must match `<count>/<period>`
- `STATIC_DIR` env var overrides auto-detected path (useful for Docker volume mounts)

**`main.py`**: FastAPI app
- `lifespan` context validates static directory at startup and clears cache on shutdown
- OpenAPI docs available at `/docs` and `/redoc`
- `/metrics` registered only when `METRICS_ENABLED=true` (default); restrict at ingress in production

**`server.py`**: Minecraft server communication
- `get_server_info(ip, timeout)` — main entry point
- Blocks private/loopback IPs and non-Minecraft ports (SSRF protection)
- Returns dict: `online`, `motd`, `server_name`, `players_online`, `players_max`, `version`, `favicon`
- Default port 25565; supports `host:port` format

**`motd_parser.py`**: Minecraft formatting code parser
- Converts `§` codes (§a, §l, §r, …) to HTML spans with CSS classes
- Color codes reset color but preserve format; §r resets everything
- Handles plain string, dict (`text`/`extra`), and object (`.text`/`.extra`) MOTD formats

**`cache.py`**: Thread-safe TTL+LRU cache
- Lazy singleton via `get_cache()`; respects `CACHE_TTL_SECONDS` / `CACHE_MAXSIZE` settings
- Prometheus hit/miss counters emitted via `metrics.py`

**`html_generator.py`**: Embed HTML construction
- Returns a self-contained HTML document; references `/static` for CSS
- Validates and sanitises server favicon (size cap, base64 check) before embedding
- Falls back to `/static/unknown_server.jpg` if no favicon

**`image_generator.py`**: Pillow PNG renderer
- Renders a 500×90 PNG with tiled Minecraft background, server icon, name, and MOTD
- Optional `static/Minecraft.ttf` for authentic font; falls back to PIL default
- `STATIC_DIR` env var controls asset lookup (same as `config.py`)
- Favicon validated (MIME type + byte budget) before decode; silent fallback on failure

**`middleware.py`**: ASGI middleware stack
- `RequestIDMiddleware` — injects/echoes `X-Request-ID`
- `SecurityHeadersMiddleware` — CSP, HSTS, X-Content-Type-Options, etc.
- `setup_logging()` — structured JSON log formatter attached to root logger

**`metrics.py`**: Prometheus instrumentation
- Counters: `cache_hits_total`, `cache_misses_total`
- Histograms: `http_request_duration_seconds`
- Exposed at `GET /metrics` (plain text Prometheus format)

### Static Assets (`static/`)
- `motd-embed.css` — Minecraft-themed CSS (`mcformat-*` classes)
- `minecraft-background-dark-160x-K223BAAL.png` — repeating background texture
- `unknown_server.jpg` — fallback server icon
- `Minecraft.ttf` *(optional)* — TTF font for the image renderer

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check — `{"status": "ok"}` |
| `GET` | `/v1/server/{ip}/embed` | HTML embed for server MOTD |
| `GET` | `/v1/server/{ip}/image` | 500×90 PNG image of the MOTD |
| `GET` | `/metrics` | Prometheus scrape endpoint (when enabled) |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc UI |

`{ip}` accepts `hostname` or `hostname:port`.

## Configuration

All settings loaded from environment variables (or `.env` file). See `.env.example` for the full list.

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Listen port |
| `RELOAD` | `false` | uvicorn auto-reload (dev only) |
| `LOG_LEVEL` | `info` | debug / info / warning / error / critical |
| `ALLOWED_ORIGINS` | `*` | Comma-separated CORS origins |
| `CACHE_TTL_SECONDS` | `30` | Server info cache lifetime |
| `CACHE_MAXSIZE` | `1000` | Max cached entries |
| `SERVER_TIMEOUT` | `5.0` | Minecraft query timeout (seconds) |
| `RATE_LIMIT_EMBED` | `30/minute` | Rate limit for `/embed` |
| `RATE_LIMIT_IMAGE` | `10/minute` | Rate limit for `/image` |
| `RATE_LIMIT_HEALTH` | `60/minute` | Rate limit for `/health` |
| `MOTD_MAX_LENGTH` | `2048` | Max MOTD character length |
| `FAVICON_MAX_BYTES` | `150000` | Max favicon data URI size |
| `STATIC_DIR` | *(auto)* | Override path to `static/` directory |
| `METRICS_ENABLED` | `true` | Expose `/metrics` endpoint |

**Setup:**
```bash
cp .env.example .env
# edit .env for your environment
```

## Code Patterns

### Error Handling
- `ValueError` → 400 Bad Request
- Unhandled exceptions → 500 Internal Server Error (details logged, not exposed)
- Server offline → 200 with "Server Offline" MOTD (not an error)

### CSS Class Structure
- `mcformat` — base class for all formatted text
- `mcformat-{color}` — color classes (e.g. `mcformat-red`, `mcformat-gold`)
- `mcformat-{format}` — format classes (e.g. `mcformat-bold`, `mcformat-italic`)

## Dependencies

- **fastapi** — web framework
- **uvicorn** — ASGI server
- **mcstatus** — Minecraft server status protocol
- **pydantic-settings** — typed environment config
- **slowapi** — rate limiting
- **cachetools** — TTL+LRU cache
- **pillow** — PNG image generation
- **prometheus-client** — metrics
- **uv** — dependency management (see `pyproject.toml`)
