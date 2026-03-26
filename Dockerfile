# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — builder: install Python deps with uv into a venv
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Pin uv to a specific release for reproducible builds
COPY --from=ghcr.io/astral-sh/uv:0.6 /uv /usr/local/bin/uv

WORKDIR /app

# Install build tools needed to compile C extensions (e.g. brotli)
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy dependency manifests first so Docker can cache this layer
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Install production dependencies into .venv; --frozen ensures lockfile is honoured
RUN uv sync --frozen --no-dev

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — runtime: lean image with only what's needed to run
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim

# Patch OS packages for known CVEs
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends libjpeg62-turbo zlib1g libfreetype6 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Run as a non-root user (uid 1000)
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /app/static && \
    chown -R appuser:appuser /app

WORKDIR /app

# Pull in the pre-built venv from the builder stage
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copy application source and static assets
COPY --chown=appuser:appuser src/     /app/src/
COPY --chown=appuser:appuser static/  /app/static/
COPY --chown=appuser:appuser pyproject.toml /app/

# ── Environment ──────────────────────────────────────────────────────────────
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Runtime defaults — all overridable at container start via -e / env_file
    PORT=8000 \
    HOST=0.0.0.0 \
    RELOAD=false \
    LOG_LEVEL=info \
    STATIC_DIR=/app/static

# OCI image labels (populated by docker/metadata-action in CI; hardcoded here
# as sensible defaults for local builds)
LABEL org.opencontainers.image.title="Minecraft MOTD Embed API" \
      org.opencontainers.image.description="Generates embeddable HTML and PNG images for Minecraft server MOTDs" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/ajxd2/motd-embed-api"

USER appuser

EXPOSE 8000

# ── Health check ──────────────────────────────────────────────────────────────
# start-period gives Pillow/uvicorn time to warm up before the first probe.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c \
        "import urllib.request, os; \
         urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\", 8000)}/health')" \
    || exit 1

# ── Entrypoint ────────────────────────────────────────────────────────────────
CMD ["python", "-m", "uvicorn", "motd_embed_api.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--forwarded-allow-ips", "*", "--proxy-headers"]
