"""Structured logging with secret redaction (Constitution II, FR-042)."""

from __future__ import annotations

import logging
import sys

import structlog

from app.security import redact_obj

_secrets: list[str] = []


def set_secrets(values: list[str]) -> None:
    _secrets.clear()
    _secrets.extend(v for v in values if v)


def _redact(_logger, _method, event_dict):
    return redact_obj(event_dict, _secrets)


def configure_logging(level: str = "INFO", secrets: list[str] | None = None) -> None:
    set_secrets(secrets or [])
    logging.basicConfig(format="%(message)s", stream=sys.stderr, level=getattr(logging, level.upper(), 20))
    # httpx logs full URLs at INFO; keep them quiet (URLs never contain secrets, but be conservative).
    logging.getLogger("httpx").setLevel(logging.WARNING)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _redact,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper(), 20)),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str = "aps"):
    return structlog.get_logger(name)
