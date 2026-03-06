import pytest
from pydantic import ValidationError

from __PROJECT_SLUG__.core.config import Environment, Settings


def test_settings_reject_debug_in_prod() -> None:
    with pytest.raises(ValidationError):
        Settings(environment=Environment.PROD, debug=True)


def test_settings_reject_auto_create_schema_in_prod() -> None:
    with pytest.raises(ValidationError):
        Settings(environment=Environment.PROD, database_auto_create_schema=True)


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
