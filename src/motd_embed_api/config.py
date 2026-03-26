"""Application configuration via pydantic-settings"""

import re
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_RATE_LIMIT_RE = re.compile(r"^\d+/(second|minute|hour|day)$")


class Settings(BaseSettings):
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    log_level: str = "info"

    # CORS — stored raw, parsed via property to strip whitespace
    allowed_origins_raw: str = Field(default="*", alias="ALLOWED_ORIGINS")

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins_raw.split(",") if o.strip()]

    # Cache
    cache_ttl_seconds: int = 30
    cache_maxsize: int = 1000

    # Server querying
    server_timeout: float = 5.0
    server_address_max_length: int = 253

    # Rate limiting (slowapi format: "<count>/<period>")
    rate_limit_embed: str = "30/minute"
    rate_limit_image: str = "10/minute"
    rate_limit_health: str = "60/minute"

    @field_validator("rate_limit_embed", "rate_limit_image", "rate_limit_health")
    @classmethod
    def validate_rate_limit(cls, v: str) -> str:
        if not _RATE_LIMIT_RE.match(v):
            raise ValueError(
                f"Invalid rate limit format {v!r}. Expected '<count>/<period>' "
                "where period is second, minute, hour, or day."
            )
        return v

    # Input limits
    motd_max_length: int = 2048
    favicon_max_bytes: int = 150_000

    # Static files — empty string means auto-detect from package location
    static_dir: str = ""

    # Observability
    metrics_enabled: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
