"""Replay of a recorded run (FR-039). Never contacts Advent of Code, models or the sandbox."""

from __future__ import annotations

import asyncio
from datetime import datetime

from app.events.bus import EventBus
from app.persistence.repo import Store
from app.persistence.tables import Event, PartState, Run, RunMode, RunStatus

MAX_GAP_S = 2.0


class ReplayService:
    def __init__(self, store: Store, bus: EventBus):
        self.store = store
        self.bus = bus
        self.tasks: dict[int, asyncio.Task] = {}

    async def start(self, source_run_id: int, speed: float = 10.0) -> Run:
        src = await self.store.get_run(source_run_id)
        if src is None:
            raise KeyError(source_run_id)
        if src.mode == RunMode.REPLAY:
            raise ValueError("cannot replay a replay")
        rep = await self.store.add(Run(mode=RunMode.REPLAY, source_run_id=src.id, year=src.year,
                                       day_from=src.day_from, day_to=src.day_to, auto_submit=src.auto_submit,
                                       config=src.config, status=RunStatus.RUNNING))
        for day in range(src.day_from, src.day_to + 1):
            for part in (1, 2):
                await self.store.get_part(rep.id, day, part)
        events = await self.bus.history(src.id, 0, limit=100000)
        self.tasks[rep.id] = asyncio.create_task(self._play(rep.id, src.id, events, max(0.5, min(speed, 100.0))))
        return rep

    async def _apply(self, rep_id: int, ev: dict) -> None:
        day, part, data, t = ev.get("day"), ev.get("part"), ev.get("data") or {}, ev["type"]
        if not day or not part:
            return
        pp = await self.store.get_part(rep_id, day, part)
        fields = {}
        if t == "part.state" and data.get("to"):
            fields["state"] = data["to"]
        elif t == "aoc.previously_completed":
            fields.update(state=PartState.VERIFIED, previously_completed=True)
        elif t == "test.result" and data.get("passed"):
            fields["tests_passed"] = True
        elif t == "exec.input" and data.get("answer"):
            fields["candidate_answer"] = data["answer"]
        elif t == "submit.result" and data.get("outcome") == "CORRECT":
            fields["accepted_answer"] = data.get("answer")
        elif t == "agent.escalation":
            fields.update(escalated=True, current_model="escalation")
        elif t == "model.call.started":
            fields["current_model"] = data.get("model_key")
        elif t == "agent.analysis":
            fields["understanding"] = {k: data.get(k) for k in ("summary", "algorithm", "complexity", "diagnosis",
                                                               "model")}
        if fields:
            await self.store.update_part(pp.id, **fields)

    async def _play(self, rep_id: int, src_id: int, events: list[dict], speed: float) -> None:
        await self.bus.emit(rep_id, "run.started", f"REPLAY of recorded run #{src_id} at {speed:g}× speed "
                            "(no live services are contacted)", level="info", replay=True,
                            data={"status": "running", "source_run_id": src_id})
        prev: datetime | None = None
        try:
            for ev in events:
                ts = datetime.fromisoformat(ev["created_at"]) if ev.get("created_at") else None
                if prev and ts:
                    await asyncio.sleep(min(MAX_GAP_S, max(0.0, (ts - prev).total_seconds() / speed)))
                prev = ts or prev
                if ev["type"] in ("run.created",):
                    continue
                await self._apply(rep_id, ev)
                await self.bus.emit(rep_id, ev["type"], ev["message"], level=ev["level"], day=ev.get("day"),
                                    part=ev.get("part"), data={**(ev.get("data") or {}), "source_event_id": ev["id"]},
                                    replay=True)
            if await self.store.update_run(rep_id, status=RunStatus.COMPLETED) is not None:
                await self.bus.emit(rep_id, "run.completed", "Replay finished", level="info", replay=True,
                                    data={"status": "completed"})
        except asyncio.CancelledError:
            await self.store.update_run(rep_id, status=RunStatus.STOPPED)
            raise

    async def stop(self, rep_id: int) -> None:
        t = self.tasks.get(rep_id)
        if t and not t.done():
            t.cancel()


def is_replay_event(e: Event) -> bool:
    return bool(e.replay)
