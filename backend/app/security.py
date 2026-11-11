"""URL allowlisting and secret redaction helpers (FR-041, FR-042)."""

from __future__ import annotations

import re
from collections.abc import Iterable
from urllib.parse import urlsplit

AOC_ORIGIN = "https://adventofcode.com"
AOC_HOST = "adventofcode.com"

# Hosts the backend may call for models and sandbox execution.
SERVICE_HOST_SUFFIXES = (
    ".openai.azure.com",
    ".services.ai.azure.com",
    ".cognitiveservices.azure.com",
    ".dynamicsessions.io",
)

REDACTED = "***REDACTED***"


class DisallowedURLError(ValueError):
    pass


def validate_service_url(url: str) -> str:
    """Only https URLs on allowlisted Azure host suffixes are accepted."""
    parts = urlsplit(url)
    if parts.scheme != "https":
        raise DisallowedURLError(f"service URL must use https: {url!r}")
    host = (parts.hostname or "").lower()
    if not any(host.endswith(sfx) for sfx in SERVICE_HOST_SUFFIXES):
        raise DisallowedURLError(f"service host not allowlisted: {host!r}")
    if parts.username or parts.password:
        raise DisallowedURLError("credentials in URL are not allowed")
    return url


def is_allowed_aoc_url(url: str) -> bool:
    parts = urlsplit(url)
    return parts.scheme == "https" and (parts.hostname or "").lower() == AOC_HOST and not parts.username


_HEADER_PATTERNS = [
    re.compile(r"(?i)(session=)[^;\s\"']+"),
    re.compile(r"(?i)(authorization[\"']?\s*[:=]\s*[\"']?bearer\s+)[A-Za-z0-9\-._~+/]+=*"),
    re.compile(r"(?i)((?:x-)?api-key[\"']?\s*[:=]\s*[\"']?)[^\s\"',}]+"),
]


def redact_text(text: str, secrets: Iterable[str] = ()) -> str:
    if not text:
        return text
    out = text
    for s in secrets:
        if s and len(s) >= 6:
            out = out.replace(s, REDACTED)
    for pat in _HEADER_PATTERNS:
        out = pat.sub(lambda m: m.group(1) + REDACTED, out)
    return out


def redact_obj(obj, secrets: Iterable[str] = ()):
    secrets = list(secrets)
    if isinstance(obj, str):
        return redact_text(obj, secrets)
    if isinstance(obj, dict):
        return {
            k: (REDACTED if str(k).lower() in {"cookie", "authorization", "api-key", "x-api-key", "aoc_session"}
                else redact_obj(v, secrets))
            for k, v in obj.items()
        }
    if isinstance(obj, (list, tuple)):
        return type(obj)(redact_obj(v, secrets) for v in obj)
    return obj
