from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _build_alembic_ini(database_url: str, path: Path) -> Path:
    root = _repo_root()
    ini = f"""
[alembic]
script_location = {root / "alembic"}
prepend_sys_path = .
path_separator = os
sqlalchemy.url = {database_url}
"""
    config_path = path / "alembic.test.ini"
    config_path.write_text(ini.strip() + "\n", encoding="utf-8")
    return config_path


def _to_sync_sqlite_url(async_url: str) -> str:
    return async_url.replace("sqlite+aiosqlite:///", "sqlite:///")


def test_alembic_upgrade_and_downgrade(tmp_path: Path) -> None:
    if shutil.which("alembic") is None:
        pytest.skip("alembic command is not available in this environment")

    db_path = tmp_path / "migration_test.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"
    config_path = _build_alembic_ini(db_url, tmp_path)

    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH", "")
    src_path = str(_repo_root() / "src")
    env["PYTHONPATH"] = f"{src_path}:{pythonpath}" if pythonpath else src_path

    subprocess.run(
        ["alembic", "-c", str(config_path), "upgrade", "head"],
        check=True,
        env=env,
    )

    engine = create_engine(_to_sync_sqlite_url(db_url))
    inspector = inspect(engine)
    assert "items" in inspector.get_table_names()
    engine.dispose()

    subprocess.run(
        ["alembic", "-c", str(config_path), "downgrade", "base"],
        check=True,
        env=env,
    )

    engine = create_engine(_to_sync_sqlite_url(db_url))
    inspector = inspect(engine)
    assert "items" not in inspector.get_table_names()
    engine.dispose()
