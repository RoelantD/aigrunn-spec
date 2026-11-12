"""Owns run lifecycle: creation, one live orchestrator task at a time, control signals, recovery."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.agents.control import RunControl
from app.agents.orchestrator import Orchestrator
from app.aoc.client import AocClient
from app.config import RunConfig, Settings
from app.events.bus import EventBus
from app.execution.base import CodeExecutionService
from app.logsetup import get_logger
from app.models.router import ModelRouter
from app.persistence.repo import Store
from app.persistence.tables import PartState, Run, RunMode, RunStatus, SubmissionOutcome

log = get_logger("runs")


class RunConflict(Exception):
    pass


@dataclass
class CreateRunRequest:
    year: int
    day_from: int
    day_to: int
    auto_submit: bool
    config: RunConfig


class RunManager:
    def __init__(self, *, settings: Settings, store: Store, bus: EventBus, aoc: AocClient, router: ModelRouter,
                 executor: CodeExecutionService | None):
        self.settings = settings
        self.store = store
        self.bus = bus
        self.aoc = aoc
        self.router = router
        self.executor = executor
        self.controls: dict[int, RunControl] = {}
        self.tasks: dict[int, asyncio.Task] = {}

    # ------------------------------------------------------------------ queries
    def is_active(self, run_id: int) -> bool:
        t = self.tasks.get(run_id)
        return t is not None and not t.done()

    def active_live_run(self) -> int | None:
        for rid, t in self.tasks.items():
            if not t.done():
                return rid
        return None

    # ------------------------------------------------------------------ commands
    async def create(self, req: CreateRunRequest) -> Run:
        run = await self.store.add(Run(mode=RunMode.LIVE, year=req.year, day_from=req.day_from, day_to=req.day_to,
                                       auto_submit=req.auto_submit, config=req.config.model_dump(),
                                       status=RunStatus.CREATED))
        for day in range(req.day_from, req.day_to + 1):
            for part in (1, 2):
                await self.store.get_part(run.id, day, part)
        await self.bus.emit(run.id, "run.created",
                            f"Run created for {req.year}, days {req.day_from}–{req.day_to}"
                            + (" with automatic submission authorized" if req.auto_submit
                               else " in manual-approval mode (Part 2 progression requires approval)"),
                            data={"status": "created", "auto_submit": req.auto_submit})
        return run

    def _check_ready(self) -> None:
        missing = []
        if not self.router.has("workhorse"):
            missing.append("workhorse model (FOUNDRY_OPENAI_BASE_URL)")
        if self.executor is None:
            missing.append("sandbox (SESSIONS_POOL_ENDPOINT)")
        if not self.aoc.has_session:
            missing.append("Advent of Code session (AOC_SESSION)")
        if missing:
            raise RunConflict("not configured: " + ", ".join(missing))

    async def start(self, run_id: int) -> None:
        run = await self.store.get_run(run_id)
        if run is None:
            raise KeyError(run_id)
        if run.mode == RunMode.REPLAY:
            raise RunConflict("replay runs cannot be started as live runs")
        if run.status not in (RunStatus.CREATED, RunStatus.PAUSED):
            raise RunConflict(f"cannot start a run in status {run.status}")
        other = self.active_live_run()
        if other is not None and other != run_id:
            raise RunConflict(f"run {other} is already active; pause or stop it first")
        if self.is_active(run_id):
            raise RunConflict("run is already active")
        self._check_ready()
        control = RunControl()
        self.controls[run_id] = control
        orch = Orchestrator(run_id=run_id, store=self.store, bus=self.bus, aoc=self.aoc, router=self.router,
                            executor=self.executor, control=control)
        self.tasks[run_id] = asyncio.create_task(orch.run(), name=f"run-{run_id}")

    async def pause(self, run_id: int) -> None:
        if self.is_active(run_id):
            self.controls[run_id].request_pause()
            return
        run = await self.store.get_run(run_id)
        if run is None:
            raise KeyError(run_id)
        if run.status != RunStatus.CREATED:
            raise RunConflict(f"cannot pause a run in status {run.status}")
        await self.store.update_run(run_id, status=RunStatus.PAUSED)

    async def resume(self, run_id: int) -> None:
        await self.start(run_id)

    async def stop(self, run_id: int) -> None:
        if self.is_active(run_id):
            self.controls[run_id].request_stop()
            return
        run = await self.store.get_run(run_id)
        if run is None:
            raise KeyError(run_id)
        if run.status in (RunStatus.COMPLETED, RunStatus.STOPPED):
            return
        await self.store.update_run(run_id, status=RunStatus.STOPPED, stop_reason="stopped by operator")
        await self.bus.emit(run_id, "run.stopped", "Run stopped by operator", level="warning",
                            data={"status": "stopped"})

    async def approve(self, run_id: int, day: int, part: int) -> None:
        if not self.is_active(run_id):
            raise RunConflict("run is not active")
        pp = await self.store.get_part(run_id, day, part)
        if not pp.awaiting_approval:
            raise RunConflict("no candidate is awaiting approval for this part")
        self.controls[run_id].approve(day, part)

    async def retry_part(self, run_id: int, day: int, part: int) -> None:
        if self.is_active(run_id):
            raise RunConflict("pause the run before retrying a part")
        pp = await self.store.get_part(run_id, day, part)
        if pp.state not in (PartState.FAILED, PartState.BLOCKED, PartState.SKIPPED):
            raise RunConflict(f"only FAILED/BLOCKED/SKIPPED parts can be retried (state {pp.state})")
        await self.store.update_part(pp.id, state=PartState.NOT_STARTED, attempts_used=0, submissions_used=0,
                                     escalated=False, status_reason="retry requested by operator")
        if part == 1:
            p2 = await self.store.get_part(run_id, day, 2)
            if p2.state == PartState.BLOCKED:
                await self.store.update_part(p2.id, state=PartState.NOT_STARTED, status_reason=None)
        run = await self.store.get_run(run_id)
        if run.status in (RunStatus.COMPLETED, RunStatus.STOPPED, RunStatus.FAILED, RunStatus.BUDGET_EXHAUSTED):
            await self.store.update_run(run_id, status=RunStatus.PAUSED, finished_at=None)
        await self.bus.emit(run_id, "part.retry", f"Day {day:02d} Part {part} reset for retry by operator",
                            day=day, part=part, level="info")

    # ------------------------------------------------------------------ recovery
    async def recover(self) -> None:
        """Called at startup: interrupted runs become paused; in-flight submissions become UNCERTAIN."""
        from sqlalchemy import select

        async with self.store.db.session() as s:
            runs = list((await s.execute(select(Run).where(Run.status == RunStatus.RUNNING))).scalars())
        for run in runs:
            await self.store.update_run(run.id, status=RunStatus.PAUSED, stop_reason="interrupted (backend restart)")
            await self.bus.emit(run.id, "run.interrupted", "Backend restarted: run paused at a safe point; "
                                "resume to continue", level="warning", data={"status": "paused"})
        for sub in await self.store.open_submissions():
            if sub.outcome == SubmissionOutcome.PENDING:
                sub.outcome = SubmissionOutcome.UNCERTAIN
                sub.message = "backend stopped before the response was recorded"
                await self.store.merge(sub)
                if sub.run_id:
                    await self.bus.emit(sub.run_id, "submit.result",
                                        f"Submission of {sub.answer} has an uncertain outcome; it will be reconciled "
                                        "before any further submission", level="warning", day=sub.day, part=sub.part,
                                        data={"outcome": "UNCERTAIN"})

    async def shutdown(self) -> None:
        for rid, t in list(self.tasks.items()):
            if not t.done():
                self.controls[rid].request_pause()
        for t in list(self.tasks.values()):
            if not t.done():
                try:
                    await asyncio.wait_for(t, timeout=10)
                except (TimeoutError, asyncio.CancelledError):
                    t.cancel()
