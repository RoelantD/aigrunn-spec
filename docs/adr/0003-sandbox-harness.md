# ADR 0003: Dynamic Sessions with a marker-based harness

- **Status**: accepted (2026-11-11)
- **Context**: Generated code is untrusted. Constitution II forbids running it in the backend.
  Results must be structured: per-case output, errors, timing and timeout.
- **Decision**:
  - `app/execution/harness.py` builds a Python harness. It embeds the program and the test cases as
    base64, `exec`s the program inside the sandbox, calls `solve(text)` for each case, and captures
    model prints. It truncates outputs at 64 KiB and prints one line,
    `@@APS_RESULT@@<base64 JSON>@@END@@`.
  - `DynamicSessionsExecutor` posts the harness to
    `{pool}/executions?api-version=2025-10-02-preview&identifier=aps-<uuid>` with
    `timeoutInSeconds`.
  - Each attempt uses one fresh session identifier for its example run and its real-input run. The
    session is released afterwards.
  - The pool is `PythonLTS` with `EgressDisabled`. Preflight runs an egress probe to check this.
- **Consequences**: The backend only builds strings and decodes results. A missing marker means a
  crash, an out-of-memory kill or a timeout. No credentials ever enter the sandbox, and a test
  asserts this. The docs disagree on whether the request body must be wrapped in `properties`, so
  the executor retries once with the wrapped form after an HTTP 400.
- **Rejected**:
  - A local subprocess or Docker executor. It would violate the constitution and make the demo
    machine a target.
  - Uploading the input as a file. It costs an extra round trip and inputs are small.
