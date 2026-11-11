"""Scripted model providers and a fake executor for tests.

The fake executor NEVER executes code. A "program" in tests is text tagged with `# BEHAVIOR: <name>`,
and the executor looks up a Python function registered by the test for that tag.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.execution.base import ExecutionInfraError, ExecutionOutcome
from app.execution.harness import CaseResult
from app.models.base import ModelInfraError, ModelOutputError, ModelRequest, ModelResponse, Usage


def program(behavior: str, extra: str = "") -> str:
    return f"# BEHAVIOR: {behavior}\ndef solve(input_text):\n    ...  # synthetic test program\n{extra}"


def proposal(behavior: str, examples: list[dict] | None = None, algorithm: str = "", diagnosis: str = "",
             code: str | None = None) -> dict[str, Any]:
    return {
        "summary": f"Synthetic summary for {behavior}",
        "algorithm": algorithm or f"Approach {behavior}",
        "complexity": "O(n)",
        "diagnosis": diagnosis,
        "examples": examples or [],
        "code": code if code is not None else program(behavior),
    }


Step = dict[str, Any] | Exception | Callable[[ModelRequest], dict[str, Any]]


@dataclass
class ScriptedProvider:
    key: str
    display_name: str
    steps: list[Step]
    deployment: str = "test-deployment"
    provider: str = "responses"
    requests: list[ModelRequest] = field(default_factory=list)
    on_retry: Any = None

    async def generate(self, req: ModelRequest) -> ModelResponse:
        self.requests.append(req)
        if not self.steps:
            raise AssertionError(f"{self.key}: no scripted response left")
        step = self.steps.pop(0) if len(self.steps) > 1 else self.steps[0]
        if isinstance(step, Exception):
            if isinstance(step, ModelInfraError) and self.on_retry:
                await self.on_retry(step.status_code, 0)
            raise step
        data = step(req) if callable(step) else step
        return ModelResponse(data=data, raw_text="{}", usage=Usage(1000, 500, 200), latency_ms=5,
                             deployment=self.deployment, model_key=self.key)


Behavior = Callable[[str], str]


@dataclass
class FakeExecutor:
    behaviors: dict[str, Behavior | str]
    name: str = "fake"
    calls: list[tuple[str, int]] = field(default_factory=list)
    released: list[str] = field(default_factory=list)
    infra_failures: int = 0

    def new_session_id(self) -> str:
        return f"fake-{uuid.uuid4().hex[:8]}"

    async def run_cases(self, code: str, cases: list[str], timeout_s: int, session_id: str) -> ExecutionOutcome:
        self.calls.append((code, len(cases)))
        if self.infra_failures > 0:
            self.infra_failures -= 1
            raise ExecutionInfraError("HTTP 503 from pool")
        m = re.search(r"# BEHAVIOR: (\S+)", code)
        beh = self.behaviors.get(m.group(1)) if m else self.behaviors.get("__preflight__")
        if beh is None:
            return ExecutionOutcome(status="error", load_error="solve(input_text) is not defined",
                                    correlation_id=session_id)
        if isinstance(beh, tuple):  # ("needs", seconds, fn): times out unless the timeout is large enough
            _, need, fn = beh
            if len(cases) == 1 and len(cases[0]) > 30 and timeout_s < need:
                return ExecutionOutcome(status="timeout", timed_out=True, stderr="execution timed out",
                                        correlation_id=session_id, duration_ms=timeout_s * 1000)
            beh = fn
        if beh == "timeout":
            return ExecutionOutcome(status="timeout", timed_out=True, stderr="execution timed out",
                                    correlation_id=session_id, duration_ms=timeout_s * 1000)
        results = []
        for i, c in enumerate(cases):
            try:
                results.append(CaseResult(i, str(beh(c)), None, 1))
            except Exception as exc:  # noqa: BLE001
                results.append(CaseResult(i, None, f"{type(exc).__name__}: {exc}", 1))
        return ExecutionOutcome(status="ok", results=results, correlation_id=session_id, duration_ms=3)

    async def run_raw(self, code: str, timeout_s: int, session_id: str) -> ExecutionOutcome:
        return ExecutionOutcome(status="ok", stdout="EGRESS:1.1.1.1:blocked(OSError)", correlation_id=session_id)

    async def release(self, session_id: str) -> None:
        self.released.append(session_id)


# --- reference behaviours for the synthetic puzzles --------------------------------------------
def drift(text: str) -> str:
    return str(sum(abs(int(a) - int(b)) for a, b in (ln.split() for ln in text.strip().splitlines())))


def products(text: str) -> str:
    return str(sum(int(a) * int(b) for a, b in (ln.split() for ln in text.strip().splitlines())))


def drift_buggy(text: str) -> str:  # forgets abs()
    return str(sum(int(b) - int(a) for a, b in (ln.split() for ln in text.strip().splitlines())))


def moss(text: str) -> str:
    return str(text.count("#"))


def moss_neighbors(text: str) -> str:
    g = text.strip().splitlines()
    n = 0
    for r, row in enumerate(g):
        for c, ch in enumerate(row):
            if ch != "#":
                continue
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                rr, cc = r + dr, c + dc
                if 0 <= rr < len(g) and 0 <= cc < len(g[rr]) and g[rr][cc] == "#":
                    n += 1
                    break
    return str(n)


EX_DAY1_P1 = [{"input": "3 5\n10 4\n7 7\n", "expected_output": "8", "note": ""}]
EX_DAY1_P2 = [{"input": "3 5\n10 4\n7 7\n", "expected_output": "104", "note": ""}]
EX_DAY2_P1 = [{"input": "#.#\n.#.\n...\n", "expected_output": "3", "note": ""}]
EX_DAY2_P2 = [{"input": "##.\n.#.\n..#\n", "expected_output": "3", "note": ""}]

ALL_BEHAVIORS: dict[str, Behavior | str] = {
    "drift": drift, "products": products, "drift_buggy": drift_buggy, "moss": moss,
    "moss_neighbors": moss_neighbors, "slow": "timeout",
    "const42": lambda _t: "42", "crash": lambda _t: 1 / 0,
    "__preflight__": lambda t: str(sum(int(x) for x in t.split())),
}

__all__ = ["ModelInfraError", "ModelOutputError"]
