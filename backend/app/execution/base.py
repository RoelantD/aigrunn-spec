"""Code execution interface (contracts/code-execution.md).

There is intentionally no local/in-process implementation (Constitution II).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.execution.harness import CaseResult


class ExecutionInfraError(Exception):
    """Sandbox service unavailable (not a solving failure)."""


@dataclass
class ExecutionOutcome:
    status: str  # ok | error | timeout | infra_error
    results: list[CaseResult] = field(default_factory=list)
    load_error: str | None = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    timed_out: bool = False
    correlation_id: str = ""


class CodeExecutionService(Protocol):
    name: str

    def new_session_id(self) -> str: ...

    async def run_cases(self, code: str, cases: list[str], timeout_s: int, session_id: str) -> ExecutionOutcome: ...

    async def release(self, session_id: str) -> None: ...

    async def run_raw(self, code: str, timeout_s: int, session_id: str) -> ExecutionOutcome: ...
