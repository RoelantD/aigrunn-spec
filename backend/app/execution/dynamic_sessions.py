"""Azure Container Apps Dynamic Sessions executor (research R9).

Only the generated program, its test/input text and the harness are sent. No credentials,
cookies or backend files ever reach the sandbox.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable

import httpx

from app.execution.base import ExecutionInfraError, ExecutionOutcome
from app.execution.harness import build_harness, decode_harness_output, strip_marker
from app.logsetup import get_logger
from app.models.auth import TokenFn
from app.models.base import ModelInfraError, post_with_retry

log = get_logger("sandbox")
STORE_LIMIT = 8192
SESSION_MGMT_API_VERSION = "2025-02-02-preview"


def _first(d: dict, *keys, default=None):
    for k in keys:
        if isinstance(d, dict) and d.get(k) is not None:
            return d[k]
    return default


class DynamicSessionsExecutor:
    name = "azure-dynamic-sessions"

    def __init__(
        self,
        *,
        pool_endpoint: str,
        token_fn: TokenFn,
        api_version: str = "2025-10-02-preview",
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ):
        self.pool_endpoint = pool_endpoint.rstrip("/")
        self.api_version = api_version
        self._token_fn = token_fn
        self._http = httpx.AsyncClient(transport=transport)
        self._sleep = sleep
        self.wrap_body: bool = False  # learned: some API versions expect {"properties": {...}}

    def new_session_id(self) -> str:
        return f"aps-{uuid.uuid4().hex}"

    async def _headers(self) -> dict[str, str]:
        return {"authorization": f"Bearer {await self._token_fn()}", "content-type": "application/json"}

    def _body(self, code: str, timeout_s: int) -> dict:
        inner = {
            "codeInputType": "Inline",
            "executionType": "Synchronous",
            "code": code,
            "timeoutInSeconds": int(timeout_s),
        }
        return {"properties": inner} if self.wrap_body else inner

    async def run_raw(self, code: str, timeout_s: int, session_id: str) -> ExecutionOutcome:
        url = f"{self.pool_endpoint}/executions?api-version={self.api_version}&identifier={session_id}"
        t0 = time.monotonic()
        try:
            resp, _lat = await post_with_retry(
                self._http, url, json_body=self._body(code, timeout_s), headers_fn=self._headers,
                sleep=self._sleep, timeout_s=timeout_s + 60,
            )
            if resp.status_code == 400 and not self.wrap_body:
                self.wrap_body = True
                resp2, _ = await post_with_retry(
                    self._http, url, json_body=self._body(code, timeout_s), headers_fn=self._headers,
                    sleep=self._sleep, timeout_s=timeout_s + 60,
                )
                if resp2.status_code < 400:
                    log.info("sandbox.wrapped_body_accepted")
                    resp = resp2
                else:
                    self.wrap_body = False
        except ModelInfraError as exc:
            raise ExecutionInfraError(str(exc)) from exc
        duration = int((time.monotonic() - t0) * 1000)
        if resp.status_code in (401, 403):
            raise ExecutionInfraError(f"sandbox authorization failed (HTTP {resp.status_code}); "
                                      "check the 'Azure ContainerApps Session Executor' role")
        if resp.status_code >= 400:
            raise ExecutionInfraError(f"sandbox rejected request: HTTP {resp.status_code} {resp.text[:300]}")
        body = resp.json()
        props = body.get("properties") if isinstance(body.get("properties"), dict) else body
        result = props.get("result") if isinstance(props.get("result"), dict) else props
        status = str(_first(props, "status", default="")).lower()
        stdout = str(_first(result, "stdout", default="") or "")
        stderr = str(_first(result, "stderr", default="") or "")
        exec_ms = _first(result, "executionTimeInMilliseconds", default=None)
        err = props.get("error") or body.get("error")
        err_text = str(err)[:2000] if err else ""
        timed_out = "timeout" in err_text.lower() or "timed out" in (stderr + err_text).lower()
        if status in ("failed", "canceled") and timed_out:
            st = "timeout"
        elif status in ("failed", "canceled"):
            st = "error"
        else:
            st = "ok"
        return ExecutionOutcome(
            status=st, stdout=stdout, stderr=(stderr + ("\n" + err_text if err_text else "")).strip(),
            duration_ms=int(exec_ms) if isinstance(exec_ms, (int, float)) else duration,
            timed_out=st == "timeout", correlation_id=session_id,
        )

    async def run_cases(self, code: str, cases: list[str], timeout_s: int, session_id: str) -> ExecutionOutcome:
        raw = await self.run_raw(build_harness(code, cases), timeout_s, session_id)
        decoded = decode_harness_output(raw.stdout)
        if decoded is None:
            status = "timeout" if raw.timed_out else "error"
            if raw.status == "ok" and not raw.stderr:
                raw.stderr = "harness produced no result (process crashed or was killed, e.g. memory limit)"
            return ExecutionOutcome(status=status, stdout=raw.stdout[-STORE_LIMIT:], stderr=raw.stderr[-STORE_LIMIT:],
                                    duration_ms=raw.duration_ms, timed_out=raw.timed_out,
                                    correlation_id=session_id)
        status = "error" if decoded.load_error else "ok"
        return ExecutionOutcome(
            status=status, results=decoded.results, load_error=decoded.load_error,
            stdout=(decoded.program_stdout or strip_marker(raw.stdout))[-STORE_LIMIT:],
            stderr=raw.stderr[-STORE_LIMIT:], duration_ms=raw.duration_ms, timed_out=False,
            correlation_id=session_id,
        )

    async def release(self, session_id: str) -> None:
        """Best-effort early release of a session (it would otherwise expire after the pool cooldown)."""
        url = f"{self.pool_endpoint}/session?api-version={SESSION_MGMT_API_VERSION}&identifier={session_id}"
        try:
            await self._http.delete(url, headers=await self._headers(), timeout=20)
        except Exception as exc:  # noqa: BLE001 - cleanup must never break solving
            log.info("sandbox.release_failed", error=type(exc).__name__)

    async def aclose(self) -> None:
        await self._http.aclose()
