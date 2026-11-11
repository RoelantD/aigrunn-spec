"""Solver: understand → generate → test → repair/escalate → execute real input (FR-011..FR-015).

Produces a *candidate* answer. Submission and acceptance are handled by the orchestrator.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.agents.control import BudgetExhausted, PauseRun, RunControl
from app.agents.policy import plan_attempt
from app.agents.prompts import (
    SOLUTION_SCHEMA,
    AttemptHistoryItem,
    PromptContext,
    build_user_prompt,
    system_prompt,
)
from app.config import RunConfig
from app.events.bus import EventBus
from app.execution.base import CodeExecutionService, ExecutionInfraError, ExecutionOutcome
from app.models.base import ModelInfraError, ModelOutputError, ModelRequest, ModelResponse
from app.models.pricing import Price, estimate_cost
from app.models.router import ModelRouter
from app.persistence.repo import Store
from app.persistence.tables import (
    Attempt,
    CodeRevision,
    ExampleCase,
    ExecutionResult,
    ModelInvocation,
    PartProgress,
    PartState,
)
from app.verification.examples import VerifiedExample, outputs_match, verify_examples
from app.verification.ledger import AnswerLedger, looks_hardcoded, normalize_answer


@dataclass
class Candidate:
    answer: str
    code: str
    revision_id: int
    attempt_id: int


@dataclass
class PartWork:
    """Mutable working memory for one part (rebuilt from persisted state on resume)."""

    year: int
    day: int
    part: int
    title: str
    puzzle_text: str
    pre_blocks: list[str]
    emphasized: list[str]
    current_article_text: str
    input_text: str
    part1_summary: str | None = None
    part1_answer: str | None = None
    part1_code: str | None = None
    examples: list[VerifiedExample] = field(default_factory=list)
    feedback: list[str] = field(default_factory=list)
    history: list[AttemptHistoryItem] = field(default_factory=list)
    previous_code: str | None = None
    last_failure: str | None = None
    after_rejection: bool = False
    extended_input_timeout: bool = False  # set after a real-input timeout (FR-004 configurable maximum)


def _short(s: str | None, n: int = 160) -> str:
    s = (s or "").strip().replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


class Solver:
    def __init__(self, *, run_id: int, cfg: RunConfig, store: Store, bus: EventBus, router: ModelRouter,
                 executor: CodeExecutionService, control: RunControl):
        self.run_id = run_id
        self.cfg = cfg
        self.store = store
        self.bus = bus
        self.router = router
        self.executor = executor
        self.control = control

    async def emit(self, w: PartWork, _type: str, _message: str, _level: str = "info", **data):
        await self.bus.emit(self.run_id, _type, _message, level=_level, day=w.day, part=w.part, data=data)

    async def set_state(self, pp: PartProgress, w: PartWork, state: PartState, reason: str | None = None) -> None:
        if pp.state == state:
            return
        old = pp.state
        pp.state = state
        await self.store.update_part(pp.id, state=state, **({"status_reason": reason} if reason else {}))
        await self.bus.emit(self.run_id, "part.state", f"{old} → {state}", day=w.day, part=w.part,
                            data={"from": old, "to": str(state), "reason": reason})

    # ------------------------------------------------------------------ model
    async def _check_budget(self) -> None:
        run = await self.store.get_run(self.run_id)
        if self.cfg.max_spend_usd > 0 and run.total_cost_usd >= self.cfg.max_spend_usd:
            raise BudgetExhausted(
                f"spend limit reached (${run.total_cost_usd:.2f} of ${self.cfg.max_spend_usd:.2f})")

    async def _call_model(self, pp: PartProgress, w: PartWork, attempt: Attempt, model_key: str,
                          effort: str, purpose: str, user: str) -> ModelResponse:
        await self._check_budget()
        provider = self.router.get(model_key)
        price = self.router.prices.get(model_key, Price())

        async def on_retry(status, wait):
            await self.emit(w, "model.call.retry",
                            f"{provider.display_name} unavailable (HTTP {status or 'network'}); retrying in {wait:.0f}s",
                            "warning", model_key=model_key, status_code=status, retry_in_s=round(wait, 1))

        provider.on_retry = on_retry
        await self.emit(w, "model.call.started", f"Calling {provider.display_name} ({effort} effort)",
                        model_key=model_key, deployment=provider.deployment, purpose=purpose, effort=effort)
        req = ModelRequest(system=system_prompt(self.cfg.exec_timeout_s), user=user, schema=SOLUTION_SCHEMA,
                           schema_name="solution_proposal", effort=effort,
                           max_output_tokens=self.cfg.max_output_tokens, purpose=purpose)
        inv = ModelInvocation(run_id=self.run_id, part_id=pp.id, attempt_id=attempt.id, model_key=model_key,
                              deployment=provider.deployment, provider=provider.provider, purpose=purpose,
                              effort=effort)
        try:
            resp = await provider.generate(req)
        except ModelInfraError as exc:
            inv.status, inv.error = "infra_error", str(exc)[:500]
            await self.store.add(inv)
            raise PauseRun(f"{provider.display_name} unavailable: {exc}") from exc
        except ModelOutputError as exc:
            inv.status, inv.error = "invalid_output", str(exc)[:500]
            inv.input_tokens, inv.output_tokens = exc.usage.input_tokens, exc.usage.output_tokens
            inv.latency_ms = exc.latency_ms
            inv.cost_usd = estimate_cost(exc.usage, price)
            await self.store.add(inv)
            await self.store.add_usage(self.run_id, cost=inv.cost_usd, inp=inv.input_tokens,
                                       out=inv.output_tokens, reasoning=None)
            raise
        inv.input_tokens = resp.usage.input_tokens
        inv.output_tokens = resp.usage.output_tokens
        inv.reasoning_tokens = resp.usage.reasoning_tokens
        inv.latency_ms = resp.latency_ms
        inv.cost_usd = estimate_cost(resp.usage, price)
        await self.store.add(inv)
        run = await self.store.add_usage(self.run_id, cost=inv.cost_usd, inp=inv.input_tokens,
                                         out=inv.output_tokens, reasoning=inv.reasoning_tokens)
        await self.emit(w, "model.call.finished",
                        f"{provider.display_name} responded in {resp.latency_ms / 1000:.1f}s",
                        model_key=model_key, input_tokens=inv.input_tokens, output_tokens=inv.output_tokens,
                        reasoning_tokens=inv.reasoning_tokens, latency_ms=inv.latency_ms, cost_usd=inv.cost_usd,
                        run_cost_usd=run.total_cost_usd)
        if self.cfg.max_spend_usd > 0 and run.total_cost_usd >= 0.8 * self.cfg.max_spend_usd:
            await self.emit(w, "budget.warning",
                            f"Spent ${run.total_cost_usd:.2f} of ${self.cfg.max_spend_usd:.2f} budget", "warning",
                            spent_usd=run.total_cost_usd, limit_usd=self.cfg.max_spend_usd)
        for note in resp.notes:
            await self.emit(w, "model.note", note, "warning", model_key=model_key)
        return resp

    # ------------------------------------------------------------------ execution
    async def _execute(self, w: PartWork, code: str, cases: list[str], session_id: str,
                       timeout_s: int | None = None) -> ExecutionOutcome:
        try:
            return await self.executor.run_cases(code, cases, timeout_s or self.cfg.exec_timeout_s, session_id)
        except ExecutionInfraError as exc:
            raise PauseRun(f"sandbox unavailable: {exc}") from exc

    # ------------------------------------------------------------------ main loop
    async def find_candidate(self, pp: PartProgress, w: PartWork, ledger: AnswerLedger) -> Candidate | None:
        """Run attempts until a candidate answer is produced or the attempt budget is spent."""
        while pp.attempts_used < self.cfg.max_attempts_per_part:
            self.control.checkpoint()
            number = pp.attempts_used + 1
            plan = plan_attempt(number, self.cfg, last_failure=w.last_failure, already_escalated=pp.escalated,
                                escalation_available=self.router.has("escalation"),
                                after_rejection=w.after_rejection)
            if not self.router.has(plan.model_key):
                raise PauseRun(f"model '{plan.model_key}' is not configured")
            if plan.escalate_reason and not pp.escalated:
                await self.set_state(pp, w, PartState.ESCALATING, plan.escalate_reason)
                await self.emit(w, "agent.escalation",
                                f"Escalating {self.router.display_name('workhorse')} → "
                                f"{self.router.display_name('escalation')}: {plan.escalate_reason}", "warning",
                                from_model=self.router.display_name("workhorse"),
                                to_model=self.router.display_name("escalation"),
                                reason=plan.escalate_reason, attempt=number)
                pp.escalated = True
            elif number == 1:
                await self.set_state(pp, w, PartState.ANALYZING)
            else:
                await self.set_state(pp, w, PartState.REPAIRING)
            pp.attempts_used = number
            pp.current_model = plan.model_key
            await self.store.update_part(pp.id, attempts_used=number, current_model=plan.model_key,
                                         escalated=pp.escalated)
            attempt = await self.store.add(Attempt(part_id=pp.id, number=number, kind=plan.kind,
                                                   model_key=plan.model_key, effort=plan.effort))
            try:
                cand = await self._one_attempt(pp, w, attempt, plan, ledger)
            except PauseRun:
                # Infrastructure problems or an operator pause do not consume a solving attempt.
                attempt.outcome = "infra_error"
                attempt.finished_at = datetime.now(UTC)
                await self.store.merge(attempt)
                pp.attempts_used = number - 1
                await self.store.update_part(pp.id, attempts_used=number - 1)
                raise
            if cand is not None:
                return cand
        return None

    async def _finish_attempt(self, attempt: Attempt, outcome: str, w: PartWork, algorithm: str | None) -> None:
        attempt.outcome = outcome
        attempt.finished_at = datetime.now(UTC)
        await self.store.merge(attempt)
        w.history.append(AttemptHistoryItem(attempt.number, self.router.display_name(attempt.model_key),
                                            algorithm or "(no algorithm)", outcome))

    async def _one_attempt(self, pp, w: PartWork, attempt: Attempt, plan, ledger: AnswerLedger) -> Candidate | None:
        name = self.router.display_name(plan.model_key)
        if attempt.number == 1:
            await self.emit(w, "agent.step", f"Analyzing requirements and generating a solution using {name}")
        elif plan.kind == "escalation":
            await self.emit(w, "agent.step", f"{name} is reassessing the algorithm")
        else:
            await self.emit(w, "agent.step", f"Generating revised solution using {name}")
        ctx = PromptContext(
            year=w.year, day=w.day, part=w.part, title=w.title, puzzle_text=w.puzzle_text,
            input_preview="", input_stats="", timeout_s=self.cfg.exec_timeout_s,
            part1_summary=w.part1_summary, part1_answer=w.part1_answer, part1_code=w.part1_code,
            previous_code=w.previous_code, feedback=list(w.feedback), ledger_feedback=ledger.feedback(),
            history=list(w.history), escalation_reason=plan.escalate_reason,
        )
        from app.agents.prompts import input_shape

        ctx.input_preview, ctx.input_stats = input_shape(w.input_text)
        purpose = "escalate" if plan.model_key == "escalation" else ("analyze_generate" if attempt.number == 1
                                                                    else "repair")
        try:
            resp = await self._call_model(pp, w, attempt, plan.model_key, plan.effort, purpose,
                                          build_user_prompt(ctx))
        except ModelOutputError as exc:
            w.feedback.append(f"Your previous response was unusable: {exc}")
            w.last_failure = "invalid_output"
            await self.emit(w, "agent.repair", f"Model output unusable: {_short(str(exc))}", "warning",
                            attempt=attempt.number, reason=str(exc)[:300])
            await self._finish_attempt(attempt, "invalid_output", w, None)
            return None
        d = resp.data
        attempt.summary, attempt.algorithm, attempt.diagnosis = (str(d.get("summary", "")),
                                                                 str(d.get("algorithm", "")),
                                                                 str(d.get("diagnosis", "")))
        await self.store.merge(attempt)
        understanding = {"summary": attempt.summary, "algorithm": attempt.algorithm,
                         "complexity": str(d.get("complexity", "")), "diagnosis": attempt.diagnosis,
                         "model": name}
        await self.store.update_part(pp.id, understanding=understanding)
        await self.emit(w, "agent.analysis", f"Approach: {_short(attempt.algorithm, 220)}",
                        summary=attempt.summary, algorithm=attempt.algorithm,
                        complexity=understanding["complexity"], diagnosis=attempt.diagnosis, model=name)

        # Examples: verify the model's extraction against the puzzle text (verbatim).
        if not w.examples:
            accepted, notes = verify_examples(d.get("examples") or [], w.pre_blocks, w.emphasized,
                                              w.current_article_text)
            if accepted:
                w.examples = accepted
                for i, ex in enumerate(accepted):
                    await self.store.add(ExampleCase(part_id=pp.id, index=i,
                                                     input_ref=hashlib.sha256(ex.input.encode()).hexdigest(),
                                                     expected=ex.expected, reliable=ex.reliable, note=ex.note))
            for n in notes:
                await self.emit(w, "test.note", n, "warning")

        code = str(d.get("code") or "")
        await self.set_state(pp, w, PartState.GENERATING)
        rev_no = await self.store.next_revision_number(pp.id)
        rev = await self.store.add(CodeRevision(attempt_id=attempt.id, part_id=pp.id, revision=rev_no,
                                                model_key=plan.model_key, code=code,
                                                sha256=hashlib.sha256(code.encode()).hexdigest()))
        await self.emit(w, "agent.code", f"Generated Python solution (revision {rev_no}, "
                        f"{len(code.splitlines())} lines)", revision=rev_no, revision_id=rev.id,
                        sha256=rev.sha256, lines=len(code.splitlines()), model=name)
        w.previous_code = code
        if "def solve" not in code:
            w.feedback.append("The module must define solve(input_text: str) -> str.")
            w.last_failure = "invalid_output"
            await self._finish_attempt(attempt, "invalid_output", w, attempt.algorithm)
            return None

        session_id = self.executor.new_session_id()
        try:
            # ---- example tests
            await self.set_state(pp, w, PartState.TESTING)
            if w.examples:
                await self.emit(w, "test.started", f"Executing {len(w.examples)} example test(s)",
                                revision=rev_no, total=len(w.examples))
                out = await self._execute(w, code, [e.input for e in w.examples], session_id)
                cases, failures = [], []
                for i, ex in enumerate(w.examples):
                    r = next((c for c in out.results if c.index == i), None)
                    actual = r.output if r else None
                    err = (r.error if r else None) or (out.load_error if i == 0 else None)
                    passed = (r is not None and r.error is None and
                              (outputs_match(ex.expected, actual) if ex.reliable else True))
                    cases.append({"index": i, "expected": ex.expected, "actual": actual, "passed": passed,
                                  "error": err[:1500] if err else None, "duration_ms": r.duration_ms if r else None,
                                  "reliable": ex.reliable})
                    if not passed:
                        failures.append(cases[-1])
                if out.status in ("timeout", "error") and not out.results:
                    failures = failures or [{"index": 0, "expected": None, "actual": None,
                                             "error": out.load_error or out.stderr[-1500:] or out.status}]
                await self.store.add(ExecutionResult(
                    revision_id=rev.id, kind="examples", status=out.status, cases=cases, stdout=out.stdout,
                    stderr=out.stderr, duration_ms=out.duration_ms, timed_out=out.timed_out,
                    correlation_id=out.correlation_id))
                if failures:
                    f = failures[0]
                    if out.timed_out:
                        msg = f"Example tests timed out after {self.cfg.exec_timeout_s}s"
                        w.last_failure = "timeout"
                    elif f.get("error"):
                        msg = f"Test {f['index'] + 1} raised {_short(f['error'].splitlines()[0], 140)}"
                        w.last_failure = "error"
                    else:
                        msg = f"Test failed: expected {f['expected']}, received {_short(f['actual'], 60)}"
                        w.last_failure = "wrong"
                    await self.emit(w, "test.result", msg, "error", revision=rev_no, passed=False,
                                    total=len(cases), failures=failures[:5])
                    w.feedback.append(self._test_feedback(failures, out, w))
                    await self.emit(w, "agent.repair", "Analyzing failure", "warning", attempt=attempt.number,
                                    reason=msg)
                    await self._finish_attempt(attempt, "tests_failed", w, attempt.algorithm)
                    return None
                reliable = sum(1 for e in w.examples if e.reliable)
                await self.emit(w, "test.result",
                                f"All example tests passed ({reliable} with verified expected output)"
                                if reliable else "Example runs completed without errors (no verified expected output)",
                                "success" if reliable else "warning", revision=rev_no, passed=True, total=len(cases),
                                failures=[])
                if reliable:
                    pp.tests_passed = True
                    await self.store.update_part(pp.id, tests_passed=True)
                else:
                    await self.emit(w, "test.unavailable", "No reliable example expectations; relying on "
                                    "sanity checks and the website verdict", "warning", reason="no reliable examples")
            else:
                await self.emit(w, "test.unavailable", "No verifiable examples found in the puzzle text", "warning",
                                reason="no examples")

            # ---- real input
            self.control.checkpoint()
            await self.set_state(pp, w, PartState.EXECUTING_INPUT)
            input_timeout = self.cfg.exec_timeout_max_s if w.extended_input_timeout else self.cfg.exec_timeout_s
            await self.emit(w, "exec.started", "Executing actual input"
                            + (f" (extended timeout {input_timeout}s)" if w.extended_input_timeout else ""),
                            revision=rev_no, timeout_s=input_timeout)
            out = await self._execute(w, code, [w.input_text], session_id, input_timeout)
            r = out.results[0] if out.results else None
            answer = normalize_answer(r.output) if (r and r.error is None and r.output is not None) else ""
            err = (r.error if r else None) or out.load_error or (out.stderr[-1500:] if not r else None)
            await self.store.add(ExecutionResult(
                revision_id=rev.id, kind="input", status=out.status if not err else "error",
                cases=[{"index": 0, "actual": answer or None, "error": err[:1500] if err else None,
                        "duration_ms": r.duration_ms if r else None}],
                answer=answer or None, stdout=out.stdout, stderr=out.stderr, duration_ms=out.duration_ms,
                timed_out=out.timed_out, correlation_id=out.correlation_id))
            if out.timed_out or not answer:
                if out.timed_out:
                    w.last_failure = "timeout"
                    w.extended_input_timeout = True
                    msg = (f"Real input timed out after {input_timeout}s — the algorithm is too slow "
                           f"for the full input")
                else:
                    w.last_failure = "error"
                    msg = f"Real input failed: {_short((err or 'empty answer').splitlines()[0], 160)}"
                await self.emit(w, "exec.input", msg, "error", revision=rev_no, status=out.status,
                                duration_ms=out.duration_ms)
                w.feedback.append(msg + (f"\nError:\n{err[-1500:]}" if err else ""))
                await self._finish_attempt(attempt, "exec_failed", w, attempt.algorithm)
                return None
            await self.emit(w, "exec.input", f"Candidate answer computed in {out.duration_ms / 1000:.1f}s",
                            "success", revision=rev_no, status="ok", duration_ms=out.duration_ms, answer=answer)
            if looks_hardcoded(code, answer):
                w.last_failure = "hardcoded"
                msg = "The computed answer appears as a literal in the code; answers must be computed"
                await self.emit(w, "agent.repair", msg, "warning", attempt=attempt.number, reason=msg)
                w.feedback.append(msg + ".")
                await self._finish_attempt(attempt, "rejected_hardcoded", w, attempt.algorithm)
                return None
            ok, why = ledger.check(answer)
            if not ok:
                w.last_failure = "wrong"
                await self.emit(w, "submit.skipped_duplicate", f"Not submitting: {why}", "warning", reason=why)
                w.feedback.append(f"Your program produced {answer}, but {why}. The algorithm or parsing must be wrong.")
                await self._finish_attempt(attempt, "rejected_duplicate", w, attempt.algorithm)
                return None
            pp.candidate_answer = answer
            await self.store.update_part(pp.id, candidate_answer=answer)
            await self._finish_attempt(attempt, "candidate", w, attempt.algorithm)
            return Candidate(answer=answer, code=code, revision_id=rev.id, attempt_id=attempt.id)
        finally:
            await self.executor.release(session_id)

    @staticmethod
    def _test_feedback(failures: list[dict], out: ExecutionOutcome, w: PartWork) -> str:
        lines = ["Example tests failed:"]
        for f in failures[:3]:
            ex = w.examples[f["index"]]
            inp = ex.input if len(ex.input) < 800 else ex.input[:800] + "…"
            line = f"- Example {f['index'] + 1} input:\n{inp}"
            if f.get("error"):
                line += f"\n  raised: {f['error'][-1200:]}"
            else:
                line += f"\n  expected: {f['expected']}\n  actual: {f['actual']}"
            lines.append(line)
        if out.timed_out:
            lines.append("The execution timed out; the algorithm is too slow.")
        if out.stdout:
            lines.append("Program output (tail):\n" + out.stdout[-800:])
        return "\n".join(lines)
