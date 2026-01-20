from fastapi import FastAPI, HTTPException, Path, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
import logging
from .server import get_server_info
from .motd_parser import parse_motd
from .html_generator import generate_embed_html
from .cache import get_cached_server_info

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Minecraft MOTD Embed API", version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration from environment
# Note: For production, set ALLOWED_ORIGINS to specific domains
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,  # Changed from True for security with wildcard origins
    allow_methods=["GET"],  # Only allow GET requests
    allow_headers=["*"],
)

# Mount static files
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}


@app.get("/v1/server/{ip}/embed", response_class=HTMLResponse)
@limiter.limit("30/minute")  # 30 requests per minute per IP
async def get_server_embed(
    request: Request,
    ip: str = Path(..., description="Server IP address (can include port as ip:port)")
):
    """
    Get HTML embed for Minecraft server MOTD.
    
    Args:
        ip: Server address (host or host:port)
        
    Returns:
        HTML response with formatted MOTD embed
    """
    try:
        # Fetch server information (with caching)
        server_info = get_cached_server_info(ip, get_server_info)

        # Parse MOTD
        motd_html = parse_motd(server_info["motd"])

        # Generate HTML embed
        server_name = ip
        html = generate_embed_html(
            server_name=server_name,
            motd_html=motd_html,
            favicon=server_info.get("favicon"),
        )

        return HTMLResponse(content=html)

    except ValueError as e:
        logger.warning(f"Invalid request for server {ip}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing request for server {ip}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/v1/server/{ip}/image")
async def get_server_image(
    ip: str = Path(..., description="Server IP address (can include port as ip:port)")
):
    """
    Placeholder endpoint for future image generation.
    
    Args:
        ip: Server address (host or host:port)
        
    Returns:
        JSON response indicating feature not yet implemented
    """
    return {
        "status": "not_implemented",
        "message": "Image generation endpoint coming soon",
        "server": ip
    }


def main() -> None:
    """Entry point for running the application"""
    import uvicorn

    # Get configuration from environment variables
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() in ("true", "1", "yes")
    log_level = os.getenv("LOG_LEVEL", "info").lower()

    logger.info(f"Starting server on {host}:{port} (reload={reload})")

    uvicorn.run(
        "motd_embed_api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level
    )
