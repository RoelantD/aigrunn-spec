"""Model provider interface (contracts/model-provider.md)."""

from __future__ import annotations

import asyncio
import json
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

MAX_INFRA_TRIES = 5


@dataclass
class ModelRequest:
    system: str
    user: str
    schema: dict[str, Any]
    schema_name: str
    effort: str
    max_output_tokens: int
    purpose: str = "analyze_generate"


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int | None = None


@dataclass
class ModelResponse:
    data: dict[str, Any]
    raw_text: str
    usage: Usage
    latency_ms: int
    deployment: str
    model_key: str
    notes: list[str] = field(default_factory=list)


class ModelInfraError(Exception):
    """Service-side failure (rate limit, outage, network). Not a solving failure."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class ModelOutputError(Exception):
    """The model answered but the output is unusable (refusal, invalid JSON). Counts as an attempt."""

    def __init__(self, message: str, usage: Usage | None = None, latency_ms: int = 0):
        super().__init__(message)
        self.usage = usage or Usage()
        self.latency_ms = latency_ms


class ModelProvider(Protocol):
    key: str
    display_name: str
    deployment: str
    provider: str

    async def generate(self, req: ModelRequest) -> ModelResponse: ...


RetryListener = Callable[[int | None, float], Awaitable[None]]


def _retry_after(resp: httpx.Response) -> float | None:
    for h in ("retry-after-ms", "x-ms-retry-after-ms"):
        if h in resp.headers:
            try:
                return float(resp.headers[h]) / 1000.0
            except ValueError:
                pass
    if "retry-after" in resp.headers:
        try:
            return float(resp.headers["retry-after"])
        except ValueError:
            return None
    return None


async def post_with_retry(
    http: httpx.AsyncClient,
    url: str,
    *,
    json_body: dict[str, Any],
    headers_fn: Callable[[], Awaitable[dict[str, str]]],
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    on_retry: RetryListener | None = None,
    max_tries: int = MAX_INFRA_TRIES,
    timeout_s: float = 600.0,
) -> tuple[httpx.Response, int]:
    """POST with infra retries (429/5xx/network). Returns (response, latency_ms of last call).

    4xx other than 408/409/429 are returned to the caller (they are request problems).
    """
    delay = 2.0
    last_err: str = ""
    for attempt in range(1, max_tries + 1):
        headers = await headers_fn()
        t0 = time.monotonic()
        try:
            resp = await http.post(url, json=json_body, headers=headers, timeout=timeout_s)
        except httpx.TransportError as exc:
            last_err = f"network error: {type(exc).__name__}"
            status = None
            wait = delay
        else:
            latency = int((time.monotonic() - t0) * 1000)
            if resp.status_code in (408, 409, 429) or resp.status_code >= 500:
                status = resp.status_code
                last_err = f"HTTP {resp.status_code}"
                wait = _retry_after(resp) or delay
            else:
                return resp, latency
        if attempt == max_tries:
            break
        wait = min(wait, 60.0)
        if on_retry:
            await on_retry(status, wait)
        await sleep(wait)
        delay = min(delay * 2, 60.0)
    raise ModelInfraError(f"model service unavailable after {max_tries} tries ({last_err})",
                          status_code=status)


_FENCE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.S)


def parse_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    m = _FENCE.search(text)
    if m:
        return json.loads(m.group(1))
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        return json.loads(text[start : end + 1])
    raise json.JSONDecodeError("no JSON object found", text, 0)


def validate_required(data: dict[str, Any], schema: dict[str, Any]) -> None:
    missing = [k for k in schema.get("required", []) if k not in data]
    if missing:
        raise ValueError(f"missing fields: {', '.join(missing)}")
