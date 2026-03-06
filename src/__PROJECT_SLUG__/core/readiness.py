from __future__ import annotations

from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI

log = structlog.get_logger()

ReadinessCheck = Callable[[FastAPI], Awaitable[None]]
READINESS_CHECKS_STATE_KEY = "readiness_checks"
STARTUP_COMPLETE_STATE_KEY = "startup_complete"


async def _startup_completed_check(app: FastAPI) -> None:
    if not getattr(app.state, STARTUP_COMPLETE_STATE_KEY, False):
        raise RuntimeError("application startup has not completed")


def configure_readiness(app: FastAPI) -> None:
    setattr(app.state, STARTUP_COMPLETE_STATE_KEY, False)
    setattr(app.state, READINESS_CHECKS_STATE_KEY, {})
    register_readiness_check(app, "startup", _startup_completed_check)


def register_readiness_check(app: FastAPI, name: str, check: ReadinessCheck) -> None:
    checks: dict[str, ReadinessCheck] = getattr(app.state, READINESS_CHECKS_STATE_KEY, {})
    setattr(app.state, READINESS_CHECKS_STATE_KEY, checks)
    checks[name] = check


async def run_readiness_checks(app: FastAPI) -> list[str]:
    checks: dict[str, ReadinessCheck] = getattr(app.state, READINESS_CHECKS_STATE_KEY, {})
    failed_checks: list[str] = []

    for name, check in checks.items():
        try:
            await check(app)
        except Exception:
            log.exception("readiness_check_failed", check=name)
            failed_checks.append(name)

    return failed_checks
