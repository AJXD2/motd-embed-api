"""FastAPI application entry point"""

import logging
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path

from fastapi import FastAPI, HTTPException, Path as FPath, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .cache import get_cache, get_cached_server_info
from .config import get_settings
from .html_generator import generate_embed_html
from .image_generator import generate_server_image
from .metrics import CONTENT_TYPE_LATEST, generate_metrics_response
from .middleware import RequestIDMiddleware, SecurityHeadersMiddleware, setup_logging
from .motd_parser import parse_motd
from .server import get_server_info

settings = get_settings()

# Structured JSON logging — must be set up before any loggers are created
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

# Resolve static directory (env override → auto-detect from package location)
_static_dir = (
    Path(settings.static_dir)
    if settings.static_dir
    else Path(__file__).parent.parent.parent / "static"
)

# Pre-built partial — captures server_timeout at startup, not per-request
_fetch_server_info = partial(get_server_info, timeout=settings.server_timeout)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup validation and graceful shutdown."""
    # --- startup ---
    logger.info(
        "Starting motd-embed-api on %s:%d  log_level=%s  metrics=%s",
        settings.host,
        settings.port,
        settings.log_level,
        settings.metrics_enabled,
    )
    if not _static_dir.exists():
        logger.warning(
            "Static directory not found: %s — CSS/fonts/images will be unavailable. "
            "Set STATIC_DIR env var to override.",
            _static_dir,
        )
    else:
        logger.info("Static files served from %s", _static_dir)

    yield

    # --- shutdown ---
    from .cache import _server_cache  # noqa: PLC0415

    if _server_cache is not None:
        _server_cache.clear()
    logger.info("motd-embed-api shutdown complete")


# Rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Minecraft MOTD Embed API",
    version="0.1.0",
    description=(
        "Generates embeddable HTML and PNG images for Minecraft server MOTDs. "
        "Fetches live server status via the Minecraft status protocol, parses "
        "§ formatting codes, and returns styled HTML or PNG responses suitable "
        "for embedding in websites."
    ),
    contact={"name": "Anthony Kovach", "email": "aj@ajxd2.dev"},
    license_info={"name": "MIT"},
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware — last added is outermost (first to run on request)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Static files
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")


@app.get("/health", summary="Health check")
@limiter.limit(settings.rate_limit_health)
async def health(request: Request):
    """Returns 200 OK when the service is ready to accept requests."""
    return {"status": "ok"}


@app.get(
    "/v1/server/{ip}/embed",
    response_class=HTMLResponse,
    summary="Server MOTD embed (HTML)",
    responses={
        200: {"description": "HTML embed document"},
        400: {"description": "Invalid or blocked server address"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(settings.rate_limit_embed)
async def get_server_embed(
    request: Request,
    ip: str = FPath(..., description="Server address — `hostname` or `hostname:port`"),
):
    """
    Return a self-contained HTML document that renders the server's MOTD with
    Minecraft-style formatting. Suitable for use in an `<iframe>`.
    """
    try:
        server_info = get_cached_server_info(ip, _fetch_server_info, get_cache())
        motd_html = parse_motd(server_info["motd"], max_length=settings.motd_max_length)
        html = generate_embed_html(
            server_name=ip,
            motd_html=motd_html,
            favicon=server_info.get("favicon"),
            favicon_max_bytes=settings.favicon_max_bytes,
        )
        return HTMLResponse(content=html)
    except ValueError as e:
        logger.warning("Invalid request for server %s: %s", ip, e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error processing embed for %s: %s", ip, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    "/v1/server/{ip}/image",
    summary="Server MOTD embed (PNG)",
    responses={
        200: {
            "content": {"image/png": {}},
            "description": "PNG image of the MOTD embed",
        },
        400: {"description": "Invalid or blocked server address"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(settings.rate_limit_image)
async def get_server_image(
    request: Request,
    ip: str = FPath(..., description="Server address — `hostname` or `hostname:port`"),
):
    """
    Return a 500×90 PNG image rendering the server's MOTD with Minecraft
    colour codes and the server icon.
    """
    try:
        server_info = get_cached_server_info(ip, _fetch_server_info, get_cache())
        buf = generate_server_image(
            server_name=ip,
            motd_text=server_info["motd"],
            favicon=server_info.get("favicon"),
            favicon_max_bytes=settings.favicon_max_bytes,
        )
        return StreamingResponse(buf, media_type="image/png")
    except ValueError as e:
        logger.warning("Invalid request for server %s: %s", ip, e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error processing image for %s: %s", ip, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


if settings.metrics_enabled:

    @app.get(
        "/metrics",
        include_in_schema=False,
        summary="Prometheus metrics",
    )
    async def metrics():
        """
        Prometheus text-format metrics scrape endpoint.
        Restrict access at the network/ingress layer in production.
        """
        return Response(generate_metrics_response(), media_type=CONTENT_TYPE_LATEST)


def main() -> None:
    """Entry point for running the application"""
    import uvicorn

    uvicorn.run(
        "motd_embed_api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level,
    )
