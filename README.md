# Minecraft MOTD Embed API

A production-ready FastAPI service that generates embeddable **HTML** and **PNG images** for Minecraft server MOTDs.
It fetches live server status via the Minecraft status protocol, parses `§` formatting codes, and serves styled responses suitable for embedding on any website.

[![CI](https://github.com/ajxd2/motd-embed-api/actions/workflows/ci.yml/badge.svg)](https://github.com/ajxd2/motd-embed-api/actions/workflows/ci.yml)
[![Image](https://ghcr.io/ajxd2/motd-embed-api)](https://github.com/ajxd2/motd-embed-api/pkgs/container/motd-embed-api)

---

## Features

| | |
|---|---|
| 🎨 **HTML embed** | Self-contained `<iframe>`-ready document with Minecraft-style colours & formatting |
| 🖼️ **PNG image** | 500×90 rasterised image with server icon, name, and MOTD |
| ⚡ **TTL cache** | 30-second per-IP cache — one live query per server per period |
| 🛡️ **SSRF-safe** | Private/loopback IPs and non-Minecraft ports are blocked |
| 📊 **Prometheus** | `/metrics` exposes cache hits, misses, and request latency |
| 🔒 **Security headers** | CSP, HSTS, X-Frame-Options, X-Content-Type-Options on every response |
| 🐳 **Docker-first** | Multi-stage image (~200 MB), runs as non-root, read-only FS |

---

## Quick start

### Pull from GHCR (recommended)

```bash
docker run -d \
  --name motd-embed-api \
  -p 8000:8000 \
  ghcr.io/ajxd2/motd-embed-api:latest
```

Then open:

```
http://localhost:8000/v1/server/mc.hypixel.net/embed
http://localhost:8000/v1/server/mc.hypixel.net/image
http://localhost:8000/health
http://localhost:8000/docs
```

### Docker Compose

```bash
# 1. Copy the example env file and edit it
cp .env.example .env

# 2. Start the service (pulls image from GHCR)
docker compose up -d

# 3. Tail logs
docker compose logs -f

# 4. Stop
docker compose down
```

> **Local build instead of pulling?**
> ```bash
> docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build
> ```

---

## API reference

Interactive docs are available at `/docs` (Swagger UI) and `/redoc`.

### `GET /v1/server/{ip}/embed`

Returns a self-contained HTML document rendering the server MOTD with Minecraft colour codes.
Suitable for use in an `<iframe>`.

```bash
curl http://localhost:8000/v1/server/mc.hypixel.net/embed
curl http://localhost:8000/v1/server/play.example.com:25565/embed
```

| Status | Meaning |
|--------|---------|
| `200` | HTML embed (server may be offline — that's still a 200) |
| `400` | Invalid address, private IP, or blocked port |
| `429` | Rate limit exceeded |

### `GET /v1/server/{ip}/image`

Returns a 500×90 PNG image of the MOTD embed.

```bash
curl -o motd.png http://localhost:8000/v1/server/mc.hypixel.net/image
```

### `GET /health`

```json
{"status": "ok"}
```

### `GET /metrics`

Prometheus text-format scrape endpoint.
Enabled by default — **restrict access at your ingress/network layer in production** (no built-in auth).

---

## Configuration

All settings are loaded from environment variables or a `.env` file.

```bash
cp .env.example .env
$EDITOR .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Listen port |
| `RELOAD` | `false` | uvicorn auto-reload — **dev only** |
| `LOG_LEVEL` | `info` | `debug` / `info` / `warning` / `error` / `critical` |
| `ALLOWED_ORIGINS` | `*` | Comma-separated CORS origins. Set to your domain(s) in production |
| `CACHE_TTL_SECONDS` | `30` | How long server info is cached |
| `CACHE_MAXSIZE` | `1000` | Maximum number of cached entries (LRU eviction) |
| `SERVER_TIMEOUT` | `5.0` | Minecraft query timeout in seconds |
| `RATE_LIMIT_EMBED` | `30/minute` | Per-IP rate limit for `/embed` |
| `RATE_LIMIT_IMAGE` | `10/minute` | Per-IP rate limit for `/image` |
| `RATE_LIMIT_HEALTH` | `60/minute` | Per-IP rate limit for `/health` |
| `MOTD_MAX_LENGTH` | `2048` | Maximum MOTD character length |
| `FAVICON_MAX_BYTES` | `150000` | Maximum favicon data URI size in bytes |
| `STATIC_DIR` | *(auto)* | Override path to `static/` assets — set automatically to `/app/static` in Docker |
| `METRICS_ENABLED` | `true` | Expose `/metrics` endpoint |

Rate limit strings must follow the format `<count>/<period>` where period is `second`, `minute`, `hour`, or `day`.
Invalid values cause the application to fail at startup.

---

## Production checklist

- [ ] Set `ALLOWED_ORIGINS` to your specific domain(s)
- [ ] Set `RELOAD=false`
- [ ] Confirm `LOG_LEVEL=info` (or `warning`)
- [ ] Restrict `/metrics` at your reverse proxy / firewall
- [ ] Put a TLS-terminating reverse proxy (nginx / Traefik / Caddy) in front
- [ ] Set up log aggregation (Loki, ELK, CloudWatch…)

---

## Reverse proxy

### nginx

```nginx
upstream motd_api {
    server 127.0.0.1:8000;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate     /etc/ssl/certs/api.example.com.crt;
    ssl_certificate_key /etc/ssl/private/api.example.com.key;

    location / {
        proxy_pass http://motd_api;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 10s;
        proxy_read_timeout    30s;
    }

    # Cache static assets at the edge
    location /static/ {
        proxy_pass http://motd_api/static/;
        add_header Cache-Control "public, max-age=86400";
    }

    # Block external access to metrics
    location /metrics {
        deny all;
    }
}
```

### Traefik (Docker labels)

Add to the `api` service in `docker-compose.yml`:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.motd-api.rule=Host(`api.example.com`)"
  - "traefik.http.routers.motd-api.entrypoints=websecure"
  - "traefik.http.routers.motd-api.tls.certresolver=letsencrypt"
  - "traefik.http.services.motd-api.loadbalancer.server.port=8000"
  # Block /metrics from the outside
  - "traefik.http.middlewares.strip-metrics.redirectregex.regex=^.*/metrics$$"
  - "traefik.http.middlewares.strip-metrics.redirectregex.replacement=/"
  - "traefik.http.routers.motd-api.middlewares=strip-metrics"
```

---

## Local development

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies (including dev)
uv sync

# Run with auto-reload
RELOAD=true uv run motd-embed-api

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=motd_embed_api --cov-report=term-missing

# Lint & format
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

### Project layout

```
motd-embed-api/
├── .github/
│   └── workflows/
│       └── ci.yml              # Test → lint → build & push to GHCR
├── src/
│   └── motd_embed_api/
│       ├── config.py           # Pydantic-settings (all env vars)
│       ├── main.py             # FastAPI app, lifespan, routes
│       ├── server.py           # Minecraft status queries (SSRF-safe)
│       ├── motd_parser.py      # § code → HTML spans
│       ├── html_generator.py   # Self-contained HTML embed
│       ├── image_generator.py  # 500×90 PNG renderer (Pillow)
│       ├── cache.py            # Thread-safe TTL+LRU cache
│       ├── metrics.py          # Prometheus counters & histograms
│       └── middleware.py       # RequestID, security headers, JSON logging
├── static/
│   ├── motd-embed.css
│   ├── minecraft-background-dark-160x-K223BAAL.png
│   ├── unknown_server.jpg
│   └── Minecraft.ttf           # optional — place here for authentic font
├── tests/                      # 111 pytest tests
├── Dockerfile                  # Multi-stage, non-root, read-only FS
├── docker-compose.yml          # Pulls from GHCR
├── docker-compose.build.yml    # Override for local builds
├── pyproject.toml
└── .env.example
```

---

## CI / CD

The GitHub Actions workflow at `.github/workflows/ci.yml` runs on every push and pull request:

1. **Test** — runs the full pytest suite on Python 3.12 and 3.13
2. **Lint** — ruff check + ruff format
3. **Publish** — builds a multi-arch (`linux/amd64`, `linux/arm64`) image and pushes to GHCR

Image tags produced:

| Trigger | Tags |
|---------|------|
| Push to `main` | `latest`, `main`, `sha-<short>` |
| Tag `v1.2.3` | `1.2.3`, `1.2`, `sha-<short>` |

Pull a specific version:

```bash
docker pull ghcr.io/ajxd2/motd-embed-api:1.2.3
docker pull ghcr.io/ajxd2/motd-embed-api:sha-a1b2c3d
```

---

## Troubleshooting

**Container won't start**
```bash
docker compose logs api
# Common causes: port 8000 in use, invalid RATE_LIMIT_* format, missing static dir
```

**CORS errors in the browser**
Make sure `ALLOWED_ORIGINS` matches your domain exactly — including the protocol (`https://`) and no trailing slash.

**Slow responses**
- Check if the target Minecraft server is reachable
- Increase `SERVER_TIMEOUT` if the server is slow to respond
- Cache hits should be near-instant; check `/metrics` for `cache_hits_total` vs `cache_misses_total`

**`/metrics` returns 404**
Set `METRICS_ENABLED=true` in your environment (it is `true` by default).

---

## License

MIT — see [LICENSE](LICENSE).
