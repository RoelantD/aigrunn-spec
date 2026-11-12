"""Run orchestrator: the per-part state machine around the solver (plan.md "Solving state machine").

Responsibilities: acquisition, submission, interpretation, cooldowns, reconciliation, Part 2 unlock,
advancing days, and run lifecycle. Only server-confirmed acceptance marks a part VERIFIED.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

from app.agents.control import PauseRun, RunControl, RunInterrupt
from app.agents.solver import PartWork, Solver
from app.aoc.client import (
    AocAuthError,
    AocClient,
    AocError,
    AocLockedError,
    AocNotSentError,
    AocUncertainError,
)
from app.aoc.parser import DayPage
from app.config import RunConfig
from app.events.bus import EventBus
from app.execution.base import CodeExecutionService
from app.logsetup import get_logger
from app.models.router import ModelRouter
from app.persistence.repo import Store, aware
from app.persistence.tables import (
    TERMINAL_PART_STATES,
    PartProgress,
    PartState,
    RunStatus,
    Submission,
    SubmissionOutcome,
)

log = get_logger("orchestrator")
FINAL_DAY = 25
RECONCILE_WAIT_S = 60  # safety wait before re-submitting after an unconfirmed submission


class Orchestrator:
    def __init__(self, *, run_id: int, store: Store, bus: EventBus, aoc: AocClient, router: ModelRouter,
                 executor: CodeExecutionService, control: RunControl):
        self.run_id = run_id
        self.store = store
        self.bus = bus
        self.aoc = aoc
        self.router = router
        self.executor = executor
        self.control = control
        self.cfg: RunConfig | None = None
        self.year = 0
        self.auto_submit = True

    async def emit(self, _type: str, _message: str, _level: str = "info", day=None, part=None, **data):
        await self.bus.emit(self.run_id, _type, _message, level=_level, day=day, part=part, data=data)

    # ------------------------------------------------------------------ lifecycle
    async def run(self) -> str:
        run = await self.store.get_run(self.run_id)
        self.cfg = RunConfig.model_validate(run.config)
        self.year = run.year
        self.auto_submit = run.auto_submit
        self.aoc.set_min_interval(self.cfg.aoc_min_interval_s)
        self.solver = Solver(run_id=self.run_id, cfg=self.cfg, store=self.store, bus=self.bus, router=self.router,
                             executor=self.executor, control=self.control)

        async def on_fetch(what: str, cached: bool) -> None:
            await self.emit("aoc.fetch", f"{'Loaded cached' if cached else 'Fetched'} {what}",
                            day=run.current_day, part=run.current_part, what=what, cached=cached)

        self.aoc.on_fetch = on_fetch
        resumed = run.status in (RunStatus.PAUSED,)
        started_at = time.monotonic()
        await self.store.update_run(self.run_id, status=RunStatus.RUNNING, stop_reason=None,
                                    started_at=run.started_at or datetime.now(UTC))
        await self.emit("run.resumed" if resumed else "run.started",
                        f"Run {'resumed' if resumed else 'started'}: {run.year} days {run.day_from}–{run.day_to}"
                        f" ({'automatic submission authorized' if run.auto_submit else 'manual approval mode'})",
                        status="running")
        final_status, reason = RunStatus.COMPLETED, None
        try:
            await self._prepare()
            for day in range(run.day_from, run.day_to + 1):
                for part in (1, 2):
                    self.control.checkpoint()
                    await self.store.update_run(self.run_id, current_day=day, current_part=part)
                    await self._process_part(day, part)
        except RunInterrupt as ri:
            final_status, reason = RunStatus(ri.status), ri.reason
        except AocAuthError as exc:
            final_status, reason = RunStatus.PAUSED, f"Advent of Code session problem: {exc}"
        except AocError as exc:
            final_status, reason = RunStatus.PAUSED, f"Advent of Code unavailable: {exc}"
        except Exception as exc:  # noqa: BLE001 - never crash the process; record and stop safely
            log.exception("orchestrator.crash")
            await self.emit("error", f"Internal error: {type(exc).__name__}: {str(exc)[:300]}", "error",
                            kind="internal", detail=str(exc)[:500])
            final_status, reason = RunStatus.FAILED, f"internal error: {type(exc).__name__}"
        run = await self.store.get_run(self.run_id)
        elapsed = (run.elapsed_seconds or 0) + (time.monotonic() - started_at)
        fields = {"status": final_status, "stop_reason": reason, "elapsed_seconds": elapsed}
        if final_status in (RunStatus.COMPLETED, RunStatus.STOPPED, RunStatus.BUDGET_EXHAUSTED, RunStatus.FAILED):
            fields["finished_at"] = datetime.now(UTC)
        await self.store.update_run(self.run_id, **fields)
        level = {"completed": "success", "paused": "warning", "stopped": "warning"}.get(final_status, "error")
        msg = {"completed": "Run completed: selected day range finished",
               "paused": f"Run paused: {reason}", "stopped": f"Run stopped: {reason}",
               "budget_exhausted": f"Run stopped: {reason}"}.get(final_status, f"Run failed: {reason}")
        await self.emit(f"run.{final_status}", msg, level, status=str(final_status), reason=reason)
        return final_status

    async def _prepare(self) -> None:
        run = await self.store.get_run(self.run_id)
        if not self.aoc.has_session:
            raise PauseRun("AOC_SESSION is not configured")
        stars = await self.aoc.calendar(self.year, refresh=True)
        await self.store.set_stars(self.year, stars)
        own = {(s.day, s.part) for s in await self.store.submissions(self.run_id)}
        for day in range(run.day_from, run.day_to + 1):
            n = stars.get(day, 0)
            for part in (1, 2):
                pp = await self.store.get_part(self.run_id, day, part)
                if pp.state == PartState.VERIFIED or (day, part) in own:
                    continue  # parts this run submitted are reconciled in _process_part, not "previously completed"
                if n >= part:
                    await self.store.update_part(pp.id, state=PartState.VERIFIED, previously_completed=True)
                    await self.emit("aoc.previously_completed",
                                    f"Day {day:02d} Part {part} was already completed on this account", "success",
                                    day=day, part=part, answer_known=False)

    # ------------------------------------------------------------------ helpers
    async def _set_state(self, pp: PartProgress, state: PartState, reason: str | None = None) -> None:
        if pp.state == state:
            return
        old = pp.state
        pp.state = state
        await self.store.update_part(pp.id, state=state, status_reason=reason)
        await self.emit("part.state", f"{old} → {state}" + (f" ({reason})" if reason else ""),
                        day=pp.day, part=pp.part, **{"from": old, "to": str(state), "reason": reason})

    def _title_for(self, page: DayPage, day: int) -> str:
        return page.title or f"Day {day}"

    async def _wait_for_cooldown(self, pp: PartProgress) -> None:
        acc = await self.store.account(self.year)
        until = aware(acc.cooldown_until)
        now = datetime.now(UTC)
        if until and until > now:
            await self._set_state(pp, PartState.WAITING_FOR_COOLDOWN)
            await self.emit("submit.cooldown", f"Waiting for Advent of Code cooldown until {until:%H:%M:%S} UTC",
                            "warning", day=pp.day, part=pp.part, until=until.isoformat())
            while True:
                remaining = (until - datetime.now(UTC)).total_seconds()
                if remaining <= 0:
                    break
                await self.control.sleep(min(remaining, 30))

    # ------------------------------------------------------------------ per part
    async def _process_part(self, day: int, part: int) -> None:
        pp = await self.store.get_part(self.run_id, day, part)
        if pp.state in TERMINAL_PART_STATES:
            return
        if part == 2:
            p1 = await self.store.get_part(self.run_id, day, 1)
            if p1.state != PartState.VERIFIED:
                await self._set_state(pp, PartState.BLOCKED, "Part 1 is not verified")
                return
        pending_answer = None
        open_subs = [x for x in await self.store.submissions(None, year=self.year, day=day, part=part)
                     if x.outcome in (SubmissionOutcome.PENDING, SubmissionOutcome.UNCERTAIN)]
        if open_subs:
            # FR-021: an earlier submission may or may not have reached the server. Never repeat blindly.
            sub = open_subs[-1]
            await self.emit("submit.result", f"Previous submission of {sub.answer} has an uncertain outcome; "
                            "reconciling with the account state", "warning", day=day, part=part, outcome="UNCERTAIN")
            if await self.reconcile(pp, sub) == "verified":
                return
            pending_answer = sub.answer
        await self._set_state(pp, PartState.FETCHING)
        await self.emit("agent.step", "Loading puzzle…", day=day, part=part)
        try:
            page = await self.aoc.day_page(self.year, day)
            if part == 2 and len(page.parts) < 2 and 2 not in page.completed_parts:
                # Part 1 is verified, so the Part 2 description is legitimately available now.
                page = await self.aoc.day_page(self.year, day, refresh=True)
        except AocLockedError as exc:
            await self._set_state(pp, PartState.BLOCKED, str(exc))
            return
        if page.title and pp.title != page.title:
            await self.store.update_part(pp.id, title=page.title)
        if part in page.completed_answers:
            await self.store.update_part(pp.id, previously_completed=True,
                                         accepted_answer=page.completed_answers.get(part))
            await self._set_state(pp, PartState.VERIFIED)
            await self.emit("aoc.previously_completed",
                            f"Day {day:02d} Part {part} was already completed on this account", "success",
                            day=day, part=part, answer_known=page.completed_answers.get(part) is not None)
            return
        if day == FINAL_DAY and part == 2:
            await self._final_day_claim(pp, page)
            return
        if len(page.parts) < part:
            await self._set_state(pp, PartState.BLOCKED, "Part description not available")
            return
        input_text = await self.aoc.input(self.year, day)
        w = await self._build_work(pp, page, input_text)
        if part == 2:
            await self.emit("part.unlocked", f"Day {day:02d} Part 2 unlocked: {self._title_for(page, day)}",
                            "success", day=day, part=2)
        await self._solve_and_submit(pp, w, pending_answer)

    async def _build_work(self, pp: PartProgress, page: DayPage, input_text: str) -> PartWork:
        art = page.parts[pp.part - 1]
        relevant = page.parts[: pp.part]
        w = PartWork(
            year=self.year, day=pp.day, part=pp.part, title=self._title_for(page, pp.day),
            puzzle_text="\n\n".join(a.text for a in relevant), pre_blocks=[b for a in relevant for b in a.pre_blocks],
            emphasized=art.emphasized, current_article_text=art.text, input_text=input_text,
        )
        if pp.part == 2:
            p1 = await self.store.get_part(self.run_id, pp.day, 1)
            w.part1_answer = p1.accepted_answer
            if p1.understanding:
                w.part1_summary = (p1.understanding.get("summary", "") + " " +
                                   p1.understanding.get("algorithm", "")).strip()
            rev = await self.store.latest_revision(p1.id)
            w.part1_code = rev.code if rev else None
        # Resume: restore what earlier attempts in this part learned.
        for a in await self.store.attempts(pp.id):
            if a.outcome not in ("pending", "infra_error"):
                from app.agents.prompts import AttemptHistoryItem

                w.history.append(AttemptHistoryItem(a.number, self.router.display_name(a.model_key),
                                                    a.algorithm or "", a.outcome))
        rev = await self.store.latest_revision(pp.id)
        if rev:
            w.previous_code = rev.code
        return w

    async def _solve_and_submit(self, pp: PartProgress, w: PartWork, pending_answer: str | None = None) -> None:
        while True:
            self.control.checkpoint()
            if pending_answer is None:
                ledger = await self.store.ledger(self.year, pp.day, pp.part)
                if pp.submissions_used >= self.cfg.max_submissions_per_part:
                    await self._fail(pp, f"submission limit reached ({self.cfg.max_submissions_per_part})")
                    return
                cand = await self.solver.find_candidate(pp, w, ledger)
                if cand is None:
                    await self._fail(pp, f"no candidate after {pp.attempts_used} attempts")
                    return
                answer = cand.answer
                await self._set_state(pp, PartState.READY_TO_SUBMIT)
                if not self.auto_submit:
                    await self._await_approval(pp, answer)
            else:
                answer, pending_answer = pending_answer, None
            # A cooldown or an unreceived POST means the answer was never judged: resubmit the same answer.
            outcome = await self._submit(pp, answer)
            while outcome == "retry_same":
                outcome = await self._submit(pp, answer)
            if outcome == "rejected":
                self._note_rejection(w)
                continue
            return  # verified or blocked

    async def _fail(self, pp: PartProgress, reason: str) -> None:
        await self._set_state(pp, PartState.FAILED, reason)
        await self.emit("part.failed", f"Day {pp.day:02d} Part {pp.part} failed: {reason}", "error",
                        day=pp.day, part=pp.part, reason=reason)
        if pp.part == 1:
            p2 = await self.store.get_part(self.run_id, pp.day, 2)
            if p2.state not in TERMINAL_PART_STATES:
                await self._set_state(p2, PartState.BLOCKED, "Part 1 failed")

    async def _await_approval(self, pp: PartProgress, answer: str) -> None:
        await self.store.update_part(pp.id, awaiting_approval=True, approved=False)
        await self.emit("submit.awaiting_approval", f"Candidate answer {answer} awaits operator approval",
                        day=pp.day, part=pp.part, answer=answer)
        ev = self.control.approval_event(pp.day, pp.part)
        while not ev.is_set():
            await self.control.sleep(5)
        ev.clear()
        await self.store.update_part(pp.id, awaiting_approval=False, approved=True)

    async def _submit(self, pp: PartProgress, answer: str, level: int | None = None) -> str:
        """Submit once. Returns verified | rejected | retry_same | blocked."""
        await self._wait_for_cooldown(pp)
        self.control.checkpoint()
        await self._set_state(pp, PartState.SUBMITTING)
        sub = await self.store.add(Submission(run_id=self.run_id, part_id=pp.id, year=self.year, day=pp.day,
                                              part=pp.part, answer=answer, outcome=SubmissionOutcome.PENDING))
        await self.emit("submit.sent", f"Submitting candidate answer {answer}", day=pp.day, part=pp.part,
                        answer=answer)
        try:
            res = await self.aoc.submit(self.year, pp.day, level or pp.part, answer)
        except AocNotSentError as exc:
            sub.outcome, sub.message = SubmissionOutcome.UNEXPECTED, f"not sent: {exc}"
            sub.responded_at = datetime.now(UTC)
            await self.store.merge(sub)
            raise PauseRun(f"could not reach Advent of Code ({exc}); nothing was submitted") from exc
        except AocUncertainError as exc:
            sub.outcome, sub.message = SubmissionOutcome.UNCERTAIN, f"no response: {exc}"
            await self.store.merge(sub)
            await self.emit("submit.result", "Submission outcome uncertain (connection lost); reconciling with "
                            "the account state before any further submission", "warning", day=pp.day, part=pp.part,
                            outcome="UNCERTAIN")
            return await self.reconcile(pp, sub)
        sub.outcome, sub.message, sub.wait_seconds = res.outcome, res.message, res.wait_seconds
        sub.responded_at = datetime.now(UTC)
        await self.store.merge(sub)
        o = res.outcome
        if o == SubmissionOutcome.CORRECT:
            await self._verified(pp, answer)
            return "verified"
        if o in (SubmissionOutcome.INCORRECT, SubmissionOutcome.TOO_HIGH, SubmissionOutcome.TOO_LOW):
            pp.submissions_used += 1
            await self.store.update_part(pp.id, submissions_used=pp.submissions_used)
            hint = {"TOO_HIGH": " (too high)", "TOO_LOW": " (too low)"}.get(str(o), "")
            await self.emit("submit.result", f"Advent of Code rejected {answer}{hint}", "error", day=pp.day,
                            part=pp.part, outcome=str(o), wait_seconds=res.wait_seconds, message=res.message[:300])
            if res.wait_seconds:
                await self.store.set_cooldown(self.year, datetime.now(UTC) + timedelta(seconds=res.wait_seconds))
            self.solver_feedback(pp, answer, o)
            return "rejected"
        if o == SubmissionOutcome.COOLDOWN:
            wait = res.wait_seconds or 60
            await self.store.set_cooldown(self.year, datetime.now(UTC) + timedelta(seconds=wait + 1))
            await self.emit("submit.result", f"Advent of Code asked to wait {wait}s before submitting", "warning",
                            day=pp.day, part=pp.part, outcome="COOLDOWN", wait_seconds=wait)
            return "retry_same"
        if o == SubmissionOutcome.ALREADY_COMPLETED:
            await self.emit("submit.result", "Advent of Code reports this part is already complete; reconciling",
                            "warning", day=pp.day, part=pp.part, outcome="ALREADY_COMPLETED")
            return await self.reconcile(pp, sub)
        if o == SubmissionOutcome.LOCKED:
            await self._set_state(pp, PartState.BLOCKED, "Advent of Code reports this level is not available")
            await self.emit("submit.result", "Part is not available on Advent of Code", "error", day=pp.day,
                            part=pp.part, outcome="LOCKED")
            return "blocked"
        if o == SubmissionOutcome.AUTH_FAILED:
            await self.emit("submit.result", "Advent of Code session is not valid", "error", day=pp.day,
                            part=pp.part, outcome="AUTH_FAILED")
            await self._set_state(pp, PartState.READY_TO_SUBMIT, "session invalid")
            raise PauseRun("Advent of Code session expired or invalid; update AOC_SESSION and resume")
        await self.emit("submit.result", "Unexpected response from Advent of Code; reconciling", "warning",
                        day=pp.day, part=pp.part, outcome="UNEXPECTED", message=res.message[:300])
        result = await self.reconcile(pp, sub)
        if result != "verified":
            raise PauseRun("unexpected submission response; inspect the submission history before resuming")
        return result

    def solver_feedback(self, pp: PartProgress, answer: str, outcome) -> None:
        self._last_rejection = (answer, str(outcome))

    def _note_rejection(self, w: PartWork) -> None:
        w.after_rejection = True
        answer, outcome = getattr(self, "_last_rejection", ("?", "INCORRECT"))
        hint = {"TOO_HIGH": "it is too high", "TOO_LOW": "it is too low"}.get(outcome, "it is wrong")
        w.feedback.append(
            f"Advent of Code rejected the answer {answer}: {hint}. The examples passed, so the bug is likely in "
            "an edge case of the real input, a misread requirement, or an assumption that only holds for the "
            "examples. Re-read the puzzle carefully and diagnose before changing the code.")
        w.last_failure = "wrong"

    async def _verified(self, pp: PartProgress, answer: str) -> None:
        await self.store.update_part(pp.id, accepted_answer=answer)
        await self._set_state(pp, PartState.VERIFIED)
        await self.emit("submit.result", "Advent of Code accepted the answer", "success", day=pp.day, part=pp.part,
                        outcome="CORRECT", answer=answer)
        acc = await self.store.account(self.year)
        stars = {int(k): v for k, v in (acc.stars or {}).items()}
        stars[pp.day] = max(stars.get(pp.day, 0), pp.part)
        await self.store.set_stars(self.year, stars)
        parts = await self.store.parts_for_run(self.run_id)
        total = sum(1 for p in parts if p.state == PartState.VERIFIED)
        await self.emit("star.earned", f"⭐ Day {pp.day:02d} Part {pp.part} verified by Advent of Code", "success",
                        day=pp.day, part=pp.part, stars_total=total)
        if pp.part == 1 and pp.day != FINAL_DAY:
            await self.emit("agent.step", "Unlocking Part 2", day=pp.day, part=2)
            # Part 2 description becomes available only now; refresh the cached page once.
            await self.aoc.day_page(self.year, pp.day, refresh=True)

    async def reconcile(self, pp: PartProgress, sub: Submission | None = None) -> str:
        """Determine acceptance from account state (never POSTs). Returns verified | retry_same."""
        page = await self.aoc.day_page(self.year, pp.day, refresh=True)
        accepted = pp.part in page.completed_answers
        if sub is not None:
            sub.outcome = SubmissionOutcome.CORRECT if accepted else SubmissionOutcome.UNEXPECTED
            sub.message = (sub.message or "") + (" | reconciled: accepted" if accepted else " | reconciled: not accepted")
            sub.responded_at = datetime.now(UTC)
            await self.store.merge(sub)
        await self.emit("submit.reconciled", "Reconciled with account state: " +
                        ("part is complete" if accepted else "part is not complete"),
                        "success" if accepted else "warning", day=pp.day, part=pp.part, verified=accepted)
        if accepted:
            ans = page.completed_answers.get(pp.part) or (sub.answer if sub else None)
            await self._verified(pp, ans or "")
            return "verified"
        # Not accepted: the answer may not have arrived. Allow one re-submission after a safety wait.
        await self.store.set_cooldown(self.year, datetime.now(UTC) + timedelta(seconds=RECONCILE_WAIT_S))
        return "retry_same"

    async def _final_day_claim(self, pp: PartProgress, page: DayPage) -> None:
        stars = await self.aoc.calendar(self.year, refresh=True)
        await self.store.set_stars(self.year, stars)
        others = sum(min(stars.get(d, 0), 2) for d in range(1, FINAL_DAY))
        day25_p1 = stars.get(FINAL_DAY, 0) >= 1
        if others < 2 * (FINAL_DAY - 1) or not day25_p1:
            await self._set_state(pp, PartState.SKIPPED,
                                  f"needs all 49 other stars (account has {others + (1 if day25_p1 else 0)})")
            await self.emit("part.skipped", "Day 25 Part 2 skipped: the final star requires all 49 other stars",
                            "warning", day=FINAL_DAY, part=2)
            return
        answer = page.form_hidden_answer if page.form_hidden_answer is not None else "0"
        await self.emit("agent.step", "All 49 other stars present — claiming the final star", day=FINAL_DAY, part=2)
        outcome = await self._submit(pp, answer)
        if outcome == "retry_same":
            await self._submit(pp, answer)
