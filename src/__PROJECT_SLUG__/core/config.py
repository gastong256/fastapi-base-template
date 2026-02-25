from enum import StrEnum
from functools import lru_cache

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
    )

    # Application
    app_name: str = "__PROJECT_NAME__"
    description: str = "__DESCRIPTION__"
    version: str = "0.1.0"
    environment: Environment = Environment.LOCAL
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # OpenTelemetry
    otel_enabled: bool = False
    otel_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "__SERVICE_NAME__"


@lru_cache
def get_settings() -> Settings:
    return Settings()
