"""Prometheus metrics registry"""

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

__all__ = [
    "HTTP_REQUESTS_TOTAL",
    "HTTP_REQUEST_DURATION",
    "CACHE_HITS_TOTAL",
    "CACHE_MISSES_TOTAL",
    "SERVER_QUERIES_TOTAL",
    "SERVER_QUERY_DURATION",
    "FAVICON_REJECTIONS_TOTAL",
    "generate_metrics_response",
    "CONTENT_TYPE_LATEST",
]

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5],
)

CACHE_HITS_TOTAL = Counter(
    "cache_hits_total",
    "Total cache hits",
    ["cache"],
)

CACHE_MISSES_TOTAL = Counter(
    "cache_misses_total",
    "Total cache misses",
    ["cache"],
)

SERVER_QUERIES_TOTAL = Counter(
    "server_queries_total",
    "Total Minecraft server queries",
    ["result"],
)

SERVER_QUERY_DURATION = Histogram(
    "server_query_duration_seconds",
    "Minecraft server query duration in seconds",
    buckets=[0.1, 0.25, 0.5, 1, 2.5, 5, 10],
)

FAVICON_REJECTIONS_TOTAL = Counter(
    "favicon_rejections_total",
    "Total favicon validation rejections",
)


def generate_metrics_response() -> bytes:
    return generate_latest()
