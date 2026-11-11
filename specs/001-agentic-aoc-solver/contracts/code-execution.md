# Code Execution Contract

```python
class CodeExecutionService(Protocol):
    name: str
    async def run_cases(code: str, cases: list[str], timeout_s: int) -> ExecutionOutcome
```

`ExecutionOutcome`: `status` (`ok` | `error` | `timeout` | `infra_error`),
`results: list[CaseResult(index, output|None, error|None, duration_ms)]`, `stdout`, `stderr`,
`duration_ms`, `timed_out`, `correlation_id`.

## Harness protocol

The service wraps the untrusted module in a harness:

1. Cases are embedded as a base64-encoded JSON list of strings (no file system or network needed).
2. The module source is embedded as a string and executed with `exec` into a fresh namespace
   inside the sandbox (never in the backend).
3. For each case the harness calls `solve(text)`, converts the result with `str()`, measures
   duration, captures exceptions (`type: message` + last 20 traceback lines), truncates outputs to
   64 KiB.
4. Model `print` output is captured into a buffer (max 64 KiB) to keep the protocol line clean.
5. The harness prints exactly one line `@@APS_RESULT@@<base64 JSON>@@END@@` to stdout.
6. Missing marker → `error` (crash/oom) unless the platform reported a timeout.

## Implementations

- `DynamicSessionsExecutor` (production): `POST {pool}/executions?api-version=2025-10-02-preview&
  identifier=aps-<uuid4>`; token scope `https://dynamicsessions.io/.default`; request timeout =
  `timeout_s + 30`; HTTP 429/5xx retried as infra errors (not attempts).
- `FakeExecutor` (tests only, in `tests/`): returns scripted outcomes; never executes code.

There is intentionally no local/in-process executor (Constitution II).
