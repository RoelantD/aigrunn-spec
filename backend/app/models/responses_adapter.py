"""Workhorse adapter: Microsoft Foundry OpenAI-compatible Responses API (v1). Research R7."""

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


class ResponsesAdapter:
    provider = "responses"

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
        self._url = base_url.rstrip("/") + "/responses"
        self._token_fn = token_fn
        self._api_key = api_key
        self._http = httpx.AsyncClient(transport=transport)
        self._sleep = sleep
        self.on_retry: RetryListener | None = None

    async def _headers(self) -> dict[str, str]:
        if self._api_key:
            return {"api-key": self._api_key, "content-type": "application/json"}
        return {"authorization": f"Bearer {await self._token_fn()}", "content-type": "application/json"}

    def build_body(self, req: ModelRequest) -> dict:
        return {
            "model": self.deployment,
            "instructions": req.system,
            "input": req.user,
            "reasoning": {"effort": req.effort},
            "max_output_tokens": req.max_output_tokens,
            "text": {"format": {"type": "json_schema", "name": req.schema_name, "schema": req.schema,
                                "strict": True}},
            "store": False,
        }

    @staticmethod
    def extract_text(body: dict) -> str:
        if isinstance(body.get("output_text"), str) and body["output_text"]:
            return body["output_text"]
        chunks: list[str] = []
        for item in body.get("output") or []:
            # Reasoning items are intentionally ignored: never stored or displayed (FR-038).
            if item.get("type") != "message":
                continue
            for c in item.get("content") or []:
                if c.get("type") in ("output_text", "text") and isinstance(c.get("text"), str):
                    chunks.append(c["text"])
                if c.get("type") == "refusal":
                    raise ModelOutputError(f"model refused: {str(c.get('refusal'))[:200]}")
        return "".join(chunks)

    async def generate(self, req: ModelRequest) -> ModelResponse:
        resp, latency = await post_with_retry(
            self._http, self._url, json_body=self.build_body(req), headers_fn=self._headers,
            sleep=self._sleep, on_retry=self.on_retry,
        )
        if resp.status_code >= 400:
            raise ModelOutputError(f"Responses API rejected request: HTTP {resp.status_code} {resp.text[:300]}",
                                   latency_ms=latency)
        body = resp.json()
        u = body.get("usage") or {}
        usage = Usage(
            input_tokens=int(u.get("input_tokens") or 0),
            output_tokens=int(u.get("output_tokens") or 0),
            reasoning_tokens=(u.get("output_tokens_details") or {}).get("reasoning_tokens"),
        )
        if body.get("status") == "incomplete":
            reason = (body.get("incomplete_details") or {}).get("reason", "unknown")
            raise ModelOutputError(f"response incomplete: {reason}", usage, latency)
        text = self.extract_text(body)
        try:
            data = parse_json_object(text)
            validate_required(data, req.schema)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ModelOutputError(f"invalid structured output: {exc}", usage, latency) from exc
        return ModelResponse(data=data, raw_text=text, usage=usage, latency_ms=latency,
                             deployment=self.deployment, model_key=self.key)

    async def aclose(self) -> None:
        await self._http.aclose()
