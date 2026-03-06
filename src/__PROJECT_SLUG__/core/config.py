from enum import StrEnum
from functools import lru_cache

from pydantic import AnyHttpUrl, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    cors_origins: list[AnyHttpUrl] = Field(default_factory=list)
    allowed_hosts: list[str] = Field(default_factory=lambda: ["*"])

    # OpenTelemetry
    otel_enabled: bool = False
    otel_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "__SERVICE_NAME__"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        if normalized not in allowed:
            raise ValueError(f"log_level must be one of: {', '.join(sorted(allowed))}")
        return normalized

    @field_validator("cors_origins", "allowed_hosts", mode="before")
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
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
