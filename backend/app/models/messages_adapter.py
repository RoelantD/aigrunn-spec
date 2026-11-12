"""Escalation adapter: Claude Messages API in Microsoft Foundry. Research R8."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable

import httpx

from app.models.auth import TokenFn
from app.models.base import (
    ModelOutputError,
    ModelRequest,
    ModelResponse,
    RetryListener,
    Usage,
    parse_json_object,
    post_with_retry,
    validate_required,
)

ANTHROPIC_VERSION = "2023-06-01"


class MessagesAdapter:
    provider = "messages"

    def __init__(
        self,
        *,
        key: str,
        display_name: str,
        base_url: str,
        deployment: str,
        token_fn: TokenFn | None = None,
        api_key: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ):
        if not token_fn and not api_key:
            raise ValueError("either token_fn or api_key is required")
        self.key = key
        self.display_name = display_name
        self.deployment = deployment
        base = base_url.rstrip("/")
        self._url = base + ("/messages" if base.endswith("/v1") else "/v1/messages")
        self._token_fn = token_fn
        self._api_key = api_key
        self._http = httpx.AsyncClient(transport=transport)
        self._sleep = sleep
        self.on_retry: RetryListener | None = None
        self.structured_output_supported: bool | None = None  # learned at runtime

    async def _headers(self) -> dict[str, str]:
        h = {"anthropic-version": ANTHROPIC_VERSION, "content-type": "application/json"}
        if self._api_key:
            h["x-api-key"] = self._api_key
        else:
            h["authorization"] = f"Bearer {await self._token_fn()}"
        return h

    def build_body(self, req: ModelRequest, *, structured: bool) -> dict:
        system = req.system
        output_config: dict = {"effort": req.effort}
        if structured:
            output_config["format"] = {"type": "json_schema", "schema": req.schema}
        else:
            system += (
                "\n\nReturn ONLY a single JSON object matching this JSON Schema, in a ```json fenced block:\n"
                + json.dumps(req.schema)
            )
        return {
            "model": self.deployment,
            "max_tokens": req.max_output_tokens,
            "system": system,
            "messages": [{"role": "user", "content": req.user}],
            "thinking": {"type": "adaptive"},
            "output_config": output_config,
        }

    async def _call(self, req: ModelRequest, structured: bool):
        return await post_with_retry(
            self._http, self._url, json_body=self.build_body(req, structured=structured),
            headers_fn=self._headers, sleep=self._sleep, on_retry=self.on_retry,
        )

    async def generate(self, req: ModelRequest) -> ModelResponse:
        notes: list[str] = []
        structured = self.structured_output_supported is not False
        resp, latency = await self._call(req, structured)
        if resp.status_code == 400 and structured and ("format" in resp.text or "output_config" in resp.text):
            self.structured_output_supported = False
            notes.append("structured output not accepted by deployment; used JSON-in-text fallback")
            resp, latency = await self._call(req, False)
        elif resp.status_code < 400 and structured:
            self.structured_output_supported = True
        if resp.status_code >= 400:
            raise ModelOutputError(f"Messages API rejected request: HTTP {resp.status_code} {resp.text[:300]}",
                                   latency_ms=latency)
        body = resp.json()
        u = body.get("usage") or {}
        usage = Usage(input_tokens=int(u.get("input_tokens") or 0) + int(u.get("cache_read_input_tokens") or 0),
                      output_tokens=int(u.get("output_tokens") or 0), reasoning_tokens=None)
        if body.get("stop_reason") == "refusal":
            raise ModelOutputError("model refused the request", usage, latency)
        if body.get("stop_reason") == "max_tokens":
            raise ModelOutputError("response truncated at max_tokens", usage, latency)
        # Thinking blocks are intentionally ignored: never stored or displayed (FR-038).
        text = "".join(b.get("text", "") for b in body.get("content") or [] if b.get("type") == "text")
        try:
            data = parse_json_object(text)
            validate_required(data, req.schema)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ModelOutputError(f"invalid structured output: {exc}", usage, latency) from exc
        return ModelResponse(data=data, raw_text=text, usage=usage, latency_ms=latency,
                             deployment=self.deployment, model_key=self.key, notes=notes)

    async def aclose(self) -> None:
        await self._http.aclose()
