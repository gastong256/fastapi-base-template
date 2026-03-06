import pytest
from pydantic import ValidationError

from __PROJECT_SLUG__.core.config import Environment, Settings


def test_settings_reject_debug_in_prod() -> None:
    with pytest.raises(ValidationError):
        Settings(environment=Environment.PROD, debug=True)


def test_settings_reject_auto_create_schema_in_prod() -> None:
    with pytest.raises(ValidationError):
        Settings(environment=Environment.PROD, database_auto_create_schema=True)


def test_settings_require_auth_in_prod() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment=Environment.PROD,
            auth_enabled=False,
            database_auto_create_schema=False,
            allowed_hosts=["api.example.com"],
            api_docs_enabled=False,
        )


def test_settings_require_database_backed_auth_in_prod() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment=Environment.PROD,
            auth_enabled=True,
            auth_use_database=False,
            auth_jwt_secret="x" * 40,
            auth_admin_password="secure-password",
            database_auto_create_schema=False,
            allowed_hosts=["api.example.com"],
            api_docs_enabled=False,
        )


def test_settings_reject_wildcard_hosts_in_prod() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment=Environment.PROD,
            auth_enabled=True,
            auth_jwt_secret="x" * 40,
            auth_admin_password="secure-password",
            database_auto_create_schema=False,
            allowed_hosts=["*"],
            api_docs_enabled=False,
        )


def test_settings_require_docs_disabled_in_prod() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment=Environment.PROD,
            auth_enabled=True,
            auth_jwt_secret="x" * 40,
            auth_admin_password="secure-password",
            database_auto_create_schema=False,
            allowed_hosts=["api.example.com"],
            api_docs_enabled=True,
        )


def test_settings_require_long_jwt_secret_when_auth_enabled() -> None:
    with pytest.raises(ValidationError):
        Settings(auth_enabled=True, auth_jwt_secret="short-secret")


def test_settings_parse_csv_list_fields() -> None:
    settings = Settings(
        cors_origins="https://api.example.com,https://admin.example.com",
        allowed_hosts="api.example.com,admin.example.com",
    )

    assert [origin.host for origin in settings.cors_origins] == [
        "api.example.com",
        "admin.example.com",
    ]
    assert settings.allowed_hosts == ["api.example.com", "admin.example.com"]


def test_settings_use_prefixed_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_DEBUG", "true")
    monkeypatch.setenv("DEBUG", "release")

    settings = Settings()

    assert settings.debug is True


def test_settings_reject_invalid_rate_limit_backend() -> None:
    with pytest.raises(ValidationError):
        Settings(rate_limit_backend="invalid")


def test_settings_require_redis_url_when_redis_backend() -> None:
    with pytest.raises(ValidationError):
        Settings(rate_limit_backend="redis", rate_limit_redis_url="  ")


def test_settings_reject_non_positive_rate_limit_memory_max_keys() -> None:
    with pytest.raises(ValidationError):
        Settings(rate_limit_memory_max_keys=0)


def test_settings_reject_invalid_runtime_concurrency_values() -> None:
    with pytest.raises(ValidationError):
        Settings(web_concurrency=0)

    with pytest.raises(ValidationError):
        Settings(keepalive_timeout=0)

    with pytest.raises(ValidationError):
        Settings(backlog=0)

    with pytest.raises(ValidationError):
        Settings(limit_concurrency=-1)


def test_settings_require_forwarded_allow_ips_non_empty() -> None:
    with pytest.raises(ValidationError):
        Settings(forwarded_allow_ips="   ")


def test_settings_require_metrics_path_starting_with_slash() -> None:
    with pytest.raises(ValidationError):
        Settings(metrics_path="metrics")


def test_settings_require_positive_timeout_and_body_limit() -> None:
    with pytest.raises(ValidationError):
        Settings(request_timeout_seconds=0)

    with pytest.raises(ValidationError):
        Settings(request_body_max_bytes=0)


def test_settings_require_valid_docs_paths_when_docs_enabled() -> None:
    with pytest.raises(ValidationError):
        Settings(api_docs_enabled=True, api_docs_url="docs")

    with pytest.raises(ValidationError):
        Settings(api_docs_enabled=True, api_redoc_url="redoc")

    with pytest.raises(ValidationError):
        Settings(api_docs_enabled=True, api_openapi_url="openapi.json")


def test_settings_require_valid_gzip_values() -> None:
    with pytest.raises(ValidationError):
        Settings(gzip_minimum_size=0)

    with pytest.raises(ValidationError):
        Settings(gzip_compress_level=0)

    with pytest.raises(ValidationError):
        Settings(gzip_compress_level=10)
