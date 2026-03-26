"""Request ID, security headers middleware, and structured JSON logging"""

import contextvars
import json
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# ContextVar carries request_id through the entire async call chain
_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=""
)


def get_request_id() -> str:
    return _request_id_var.get("")


class JsonFormatter(logging.Formatter):
    """Structured JSON log formatter that injects the current request ID."""

    def format(self, record: logging.LogRecord) -> str:
        obj: dict = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": _request_id_var.get(""),
        }
        if record.exc_info:
            obj["exc"] = self.formatException(record.exc_info)
        return json.dumps(obj)


def setup_logging(log_level: str = "info") -> None:
    """Configure root logger with JSON output."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=log_level.upper(), handlers=[handler], force=True)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Reads or generates a request ID, records HTTP metrics, and echoes the ID
    in the response via X-Request-ID.
    """

    async def dispatch(self, request: Request, call_next):
        from .metrics import HTTP_REQUEST_DURATION, HTTP_REQUESTS_TOTAL

        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = _request_id_var.set(request_id)
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        endpoint = request.url.path
        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=str(response.status_code),
        ).inc()
        HTTP_REQUEST_DURATION.labels(
            method=request.method,
            endpoint=endpoint,
        ).observe(duration)

        _request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security-related HTTP response headers to every response."""

    _HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "SAMEORIGIN",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "X-XSS-Protection": "1; mode=block",
        "Content-Security-Policy": (
            "default-src 'self'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'none'"
        ),
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for header, value in self._HEADERS.items():
            response.headers[header] = value
        return response
