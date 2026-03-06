from enum import StrEnum
from functools import lru_cache
from typing import Annotated

from pydantic import AnyHttpUrl, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Environment(StrEnum):
    LOCAL = "local"
    TEST = "test"
    PROD = "prod"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="APP_",
    )

    # Application
    app_name: str = "__PROJECT_NAME__"
    description: str = "__DESCRIPTION__"
    version: str = "0.1.0"
    environment: Environment = Environment.LOCAL
    debug: bool = False
    log_level: str = "INFO"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: Annotated[list[AnyHttpUrl], NoDecode] = Field(default_factory=list)
    allowed_hosts: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["*"])
    trust_x_forwarded_for: bool = False

    # OpenTelemetry
    otel_enabled: bool = False
    otel_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "__SERVICE_NAME__"

    # Database
    database_url: str = "sqlite+aiosqlite:///./app.db"
    database_echo: bool = False
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout: int = 30
    database_pool_recycle: int = 1800
    database_connect_on_startup: bool = False
    database_auto_create_schema: bool = True

    # Authentication / Authorization
    auth_enabled: bool = False
    auth_jwt_secret: str = "change-me-please-use-a-long-random-secret"
    auth_jwt_algorithm: str = "HS256"
    auth_access_token_expire_minutes: int = 30
    auth_issuer: str = "__SERVICE_NAME__"
    auth_audience: str = "__SERVICE_NAME__-clients"
    auth_admin_username: str = "admin"
    auth_admin_password: str = "change-me"
    auth_admin_scopes: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["items:read", "items:write"],
    )

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_backend: str = "memory"
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    rate_limit_fail_open: bool = True
    rate_limit_redis_url: str = "redis://localhost:6379/0"
    rate_limit_redis_prefix: str = "__SERVICE_NAME__"
    rate_limit_exempt_paths: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["/health", "/ready", "/api/docs", "/api/redoc", "/api/openapi.json"],
    )

    # Security headers
    security_headers_enabled: bool = True
    security_csp: str = "default-src 'self'; frame-ancestors 'none'; base-uri 'self'"
    security_hsts_enabled: bool = False
    security_hsts_seconds: int = 31536000

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        if normalized not in allowed:
            raise ValueError(f"log_level must be one of: {', '.join(sorted(allowed))}")
        return normalized

    @field_validator(
        "cors_origins",
        "allowed_hosts",
        "auth_admin_scopes",
        "rate_limit_exempt_paths",
        mode="before",
    )
    @classmethod
    def parse_csv_settings(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def validate_environment_constraints(self) -> "Settings":
        if self.environment == Environment.PROD and self.debug:
            raise ValueError("debug must be false when environment=prod")
        if self.environment == Environment.PROD and self.database_auto_create_schema:
            raise ValueError("database_auto_create_schema must be false when environment=prod")
        if self.environment == Environment.PROD and self.allowed_hosts == ["*"]:
            raise ValueError("allowed_hosts cannot be '*' when environment=prod")
        if self.environment == Environment.PROD and not self.auth_enabled:
            raise ValueError("auth_enabled must be true when environment=prod")

        if self.database_pool_size < 1:
            raise ValueError("database_pool_size must be >= 1")
        if self.database_max_overflow < 0:
            raise ValueError("database_max_overflow must be >= 0")
        if self.database_pool_timeout < 1:
            raise ValueError("database_pool_timeout must be >= 1")
        if self.database_pool_recycle < 1:
            raise ValueError("database_pool_recycle must be >= 1")
        if self.rate_limit_requests < 1:
            raise ValueError("rate_limit_requests must be >= 1")
        if self.rate_limit_window_seconds < 1:
            raise ValueError("rate_limit_window_seconds must be >= 1")
        if self.rate_limit_backend not in {"memory", "redis"}:
            raise ValueError("rate_limit_backend must be one of: memory, redis")
        if self.rate_limit_backend == "redis" and not self.rate_limit_redis_url.strip():
            raise ValueError("rate_limit_redis_url cannot be empty when rate_limit_backend=redis")
        if not self.rate_limit_redis_prefix.strip():
            raise ValueError("rate_limit_redis_prefix cannot be empty")
        if self.auth_access_token_expire_minutes < 1:
            raise ValueError("auth_access_token_expire_minutes must be >= 1")
        if self.auth_enabled and len(self.auth_jwt_secret) < 32:
            raise ValueError("auth_jwt_secret must be at least 32 characters when auth_enabled=true")
        if self.environment == Environment.PROD and self.auth_admin_password == "change-me":
            raise ValueError("auth_admin_password must be changed in production")
        if self.security_hsts_enabled and self.security_hsts_seconds < 1:
            raise ValueError("security_hsts_seconds must be >= 1 when HSTS is enabled")
        if not self.auth_admin_scopes:
            raise ValueError("auth_admin_scopes cannot be empty")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
