"""Run management, progress, code, submissions, metrics and replay endpoints (contracts/rest-api.md)."""

from __future__ import annotations

import re
import shutil
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import delete, select

from app.agents.run_manager import CreateRunRequest, RunConflict
from app.api.deps import services
from app.config import RunConfig
from app.persistence.tables import (
    Event,
    PartProgress,
    PartState,
    Run,
    RunMode,
    RunStatus,
    Submission,
    SubmissionOutcome,
    iso_utc,
)
from app.services import Services

router = APIRouter()

NOT_RESET_NOTICE = "Only local data was removed. Advent of Code account progress is not affected and cannot be reset."
ACTIVE_STATES = {PartState.FETCHING, PartState.ANALYZING, PartState.GENERATING, PartState.TESTING,
                 PartState.REPAIRING, PartState.ESCALATING, PartState.EXECUTING_INPUT}


class CreateRunBody(BaseModel):
    calendar_url: str | None = None
    year: int | None = Field(None, ge=2015, le=2100)
    day_from: int = Field(1, ge=1, le=25)
    day_to: int = Field(25, ge=1, le=25)
    auto_submit: bool = True
    authorize_submission: bool = False
    config: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _check(self):
        if self.calendar_url:
            m = re.fullmatch(r"https://adventofcode\.com/(\d{4})/?", self.calendar_url.strip())
            if not m:
                raise ValueError("calendar_url must look like https://adventofcode.com/2024")
            self.year = int(m.group(1))
        if self.year is None:
            raise ValueError("year or calendar_url is required")
        if self.day_from > self.day_to:
            raise ValueError("day_from must be <= day_to")
        if self.auto_submit and not self.authorize_submission:
            raise ValueError("automatic submission requires explicit authorization (authorize_submission=true)")
        return self


def ui_state(p: PartProgress, submitted_pending: bool) -> str:
    s = p.state
    if s == PartState.VERIFIED:
        return "previously_completed" if p.previously_completed else "verified"
    if s in (PartState.FAILED, PartState.BLOCKED, PartState.SKIPPED):
        return s.lower() if isinstance(s, str) else str(s)
    if s in (PartState.SUBMITTING, PartState.WAITING_FOR_COOLDOWN) or submitted_pending:
        return "submitted"
    if s == PartState.READY_TO_SUBMIT:
        return "tests_passed" if p.tests_passed else "solving"
    if s in ACTIVE_STATES:
        return "solving"
    if p.tests_passed:
        return "tests_passed"
    return "unsolved"


def run_dict(r: Run, active: bool = False) -> dict:
    return {
        "id": r.id, "mode": r.mode, "source_run_id": r.source_run_id, "year": r.year, "day_from": r.day_from,
        "day_to": r.day_to, "status": r.status, "stop_reason": r.stop_reason, "auto_submit": r.auto_submit,
        "config": r.config, "current_day": r.current_day, "current_part": r.current_part,
        "created_at": iso_utc(r.created_at),
        "started_at": iso_utc(r.started_at),
        "finished_at": iso_utc(r.finished_at),
        "elapsed_seconds": r.elapsed_seconds, "total_cost_usd": r.total_cost_usd,
        "total_input_tokens": r.total_input_tokens, "total_output_tokens": r.total_output_tokens,
        "total_reasoning_tokens": r.total_reasoning_tokens, "total_model_calls": r.total_model_calls,
        "active": active,
    }


async def _run_or_404(svc: Services, run_id: int) -> Run:
    run = await svc.store.get_run(run_id)
    if run is None:
        raise HTTPException(404, "run not found")
    return run


def _conflict(fn):
    async def wrapper(*a, **kw):
        try:
            return await fn(*a, **kw)
        except RunConflict as exc:
            raise HTTPException(409, str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(404, "not found") from exc

    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    import inspect

    wrapper.__signature__ = inspect.signature(fn)
    return wrapper


@router.get("/runs")
async def list_runs(svc: Services = Depends(services)) -> list[dict]:
    async with svc.db.session() as s:
        runs = list((await s.execute(select(Run).order_by(Run.id.desc()).limit(200))).scalars())
    return [run_dict(r, svc.runs.is_active(r.id) or r.id in svc.replay.tasks and not svc.replay.tasks[r.id].done())
            for r in runs]


@router.post("/runs", status_code=201)
async def create_run(body: CreateRunBody, svc: Services = Depends(services)) -> dict:
    cfg_data = svc.settings.default_run_config().model_dump()
    cfg_data.update(body.config or {})
    try:
        cfg = RunConfig.model_validate(cfg_data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if svc.aoc.has_session:
        st = await svc.aoc.validate_session(body.year)
        if not st.logged_in:
            raise HTTPException(409, f"Advent of Code session invalid: {st.detail}")
    else:
        raise HTTPException(409, "AOC_SESSION is not configured")
    run = await svc.runs.create(CreateRunRequest(year=body.year, day_from=body.day_from, day_to=body.day_to,
                                                 auto_submit=body.auto_submit, config=cfg))
    return run_dict(run)


@router.get("/runs/{run_id}")
async def get_run(run_id: int, svc: Services = Depends(services)) -> dict:
    run = await _run_or_404(svc, run_id)
    return run_dict(run, svc.runs.is_active(run_id))


@router.post("/runs/{run_id}/start")
@_conflict
async def start(run_id: int, svc: Services = Depends(services)) -> dict:
    await svc.runs.start(run_id)
    return {"ok": True}


@router.post("/runs/{run_id}/pause")
@_conflict
async def pause(run_id: int, svc: Services = Depends(services)) -> dict:
    await svc.runs.pause(run_id)
    return {"ok": True}


@router.post("/runs/{run_id}/resume")
@_conflict
async def resume(run_id: int, svc: Services = Depends(services)) -> dict:
    await svc.runs.resume(run_id)
    return {"ok": True}


@router.post("/runs/{run_id}/stop")
@_conflict
async def stop(run_id: int, svc: Services = Depends(services)) -> dict:
    run = await _run_or_404(svc, run_id)
    if run.mode == RunMode.REPLAY:
        await svc.replay.stop(run_id)
    else:
        await svc.runs.stop(run_id)
    return {"ok": True}


@router.post("/runs/{run_id}/parts/{day}/{part}/retry")
@_conflict
async def retry(run_id: int, day: int, part: int, svc: Services = Depends(services)) -> dict:
    await svc.runs.retry_part(run_id, day, part)
    return {"ok": True}


@router.post("/runs/{run_id}/parts/{day}/{part}/approve")
@_conflict
async def approve(run_id: int, day: int, part: int, svc: Services = Depends(services)) -> dict:
    await svc.runs.approve(run_id, day, part)
    return {"ok": True}


@router.get("/runs/{run_id}/progress")
async def progress(run_id: int, svc: Services = Depends(services)) -> dict:
    run = await _run_or_404(svc, run_id)
    parts = await svc.store.parts_for_run(run_id)
    pending = {(s.day, s.part) for s in await svc.store.submissions(run_id)
               if s.outcome in (SubmissionOutcome.PENDING, SubmissionOutcome.UNCERTAIN)}
    days: dict[int, dict] = {}
    for p in parts:
        d = days.setdefault(p.day, {"day": p.day, "title": None, "parts": {}})
        d["title"] = d["title"] or p.title
        d["parts"][str(p.part)] = {
            "state": p.state, "ui_state": ui_state(p, (p.day, p.part) in pending),
            "previously_completed": p.previously_completed, "tests_passed": p.tests_passed,
            "candidate_answer": p.candidate_answer, "accepted_answer": p.accepted_answer,
            "attempts_used": p.attempts_used, "submissions_used": p.submissions_used,
            "current_model": p.current_model, "escalated": p.escalated, "status_reason": p.status_reason,
            "awaiting_approval": p.awaiting_approval,
        }
    verified_new = sum(1 for p in parts if p.state == PartState.VERIFIED and not p.previously_completed)
    verified_prev = sum(1 for p in parts if p.state == PartState.VERIFIED and p.previously_completed)
    return {
        "run": run_dict(run, svc.runs.is_active(run_id)),
        "days": [days[k] for k in sorted(days)],
        "stars": {"earned_this_run": verified_new, "previously_completed": verified_prev,
                  "total": verified_new + verified_prev},
        "failed": sum(1 for p in parts if p.state == PartState.FAILED),
        "blocked": sum(1 for p in parts if p.state == PartState.BLOCKED),
        "attempts": sum(p.attempts_used for p in parts),
    }


async def _source_part(svc: Services, run: Run, day: int, part: int) -> PartProgress:
    rid = run.source_run_id if run.mode == RunMode.REPLAY and run.source_run_id else run.id
    return await svc.store.get_part(rid, day, part)


@router.get("/runs/{run_id}/parts/{day}/{part}")
async def part_detail(run_id: int, day: int, part: int, svc: Services = Depends(services)) -> dict:
    run = await _run_or_404(svc, run_id)
    pp = await svc.store.get_part(run_id, day, part)
    src = await _source_part(svc, run, day, part)
    attempts = await svc.store.attempts(src.id)
    subs = await svc.store.submissions(None, part_id=src.id)
    return {
        "day": day, "part": part, "title": pp.title, "state": pp.state, "understanding": pp.understanding,
        "attempts": [{"number": a.number, "kind": a.kind, "model_key": a.model_key, "effort": a.effort,
                      "summary": a.summary, "algorithm": a.algorithm, "diagnosis": a.diagnosis,
                      "outcome": a.outcome} for a in attempts],
        "submissions": [_sub_dict(s) for s in subs],
    }


def _sub_dict(s: Submission) -> dict:
    return {"id": s.id, "year": s.year, "day": s.day, "part": s.part, "answer": s.answer, "outcome": s.outcome,
            "message": s.message, "wait_seconds": s.wait_seconds,
            "submitted_at": iso_utc(s.submitted_at),
            "responded_at": iso_utc(s.responded_at)}


@router.get("/runs/{run_id}/parts/{day}/{part}/revisions")
async def revisions(run_id: int, day: int, part: int, svc: Services = Depends(services)) -> list[dict]:
    run = await _run_or_404(svc, run_id)
    src = await _source_part(svc, run, day, part)
    max_rev = None
    if run.mode == RunMode.REPLAY:
        # Only reveal revisions the replay timeline has reached.
        async with svc.db.session() as s:
            evs = (await s.execute(select(Event).where(Event.run_id == run_id, Event.type == "agent.code",
                                                       Event.day == day, Event.part == part))).scalars()
            revs = [e.data.get("revision", 0) for e in evs]
        max_rev = max(revs, default=0)
    out = []
    for rev, results in await svc.store.revisions(src.id):
        if max_rev is not None and rev.revision > max_rev:
            continue
        out.append({
            "revision": rev.revision, "model_key": rev.model_key, "code": rev.code, "sha256": rev.sha256,
            "created_at": iso_utc(rev.created_at),
            "results": [{"kind": r.kind, "status": r.status, "cases": r.cases, "answer": r.answer,
                         "stdout": r.stdout[-4000:], "stderr": r.stderr[-4000:], "duration_ms": r.duration_ms,
                         "timed_out": r.timed_out, "correlation_id": r.correlation_id} for r in results],
        })
    return out


@router.get("/runs/{run_id}/submissions")
async def submissions(run_id: int, svc: Services = Depends(services)) -> list[dict]:
    run = await _run_or_404(svc, run_id)
    rid = run.source_run_id if run.mode == RunMode.REPLAY and run.source_run_id else run_id
    return [_sub_dict(s) for s in await svc.store.submissions(rid)]


@router.get("/runs/{run_id}/metrics")
async def metrics(run_id: int, svc: Services = Depends(services)) -> dict:
    run = await _run_or_404(svc, run_id)
    rid = run.source_run_id if run.mode == RunMode.REPLAY and run.source_run_id else run_id
    invs = await svc.store.invocations(rid)
    by_model: dict[str, dict] = defaultdict(lambda: {"calls": 0, "input_tokens": 0, "output_tokens": 0,
                                                     "reasoning_tokens": 0, "latency_ms_total": 0, "cost_usd": 0.0,
                                                     "errors": 0})
    by_part: dict[str, dict] = defaultdict(lambda: {"calls": 0, "cost_usd": 0.0, "tokens": 0, "latency_ms_total": 0})
    parts = {p.id: p for p in await svc.store.parts_for_run(rid)}
    for i in invs:
        m = by_model[i.model_key]
        m["calls"] += 1
        m["input_tokens"] += i.input_tokens
        m["output_tokens"] += i.output_tokens
        m["reasoning_tokens"] += i.reasoning_tokens or 0
        m["latency_ms_total"] += i.latency_ms
        m["cost_usd"] = round(m["cost_usd"] + i.cost_usd, 6)
        m["errors"] += 0 if i.status == "ok" else 1
        if i.part_id in parts:
            p = parts[i.part_id]
            k = f"{p.day}-{p.part}"
            by_part[k]["calls"] += 1
            by_part[k]["cost_usd"] = round(by_part[k]["cost_usd"] + i.cost_usd, 6)
            by_part[k]["tokens"] += i.input_tokens + i.output_tokens
            by_part[k]["latency_ms_total"] += i.latency_ms
    for m in by_model.values():
        m["avg_latency_ms"] = int(m["latency_ms_total"] / m["calls"]) if m["calls"] else 0
    names = {k: svc.router.display_name(k) for k in by_model}
    return {
        "run_id": run_id, "total_cost_usd": run.total_cost_usd, "total_model_calls": run.total_model_calls,
        "escalations": sum(1 for p in parts.values() if p.escalated),
        "pricing_configured": {k: svc.router.prices[k].configured for k in svc.router.prices},
        "by_model": {k: {**v, "display_name": names[k]} for k, v in by_model.items()},
        "by_part": dict(by_part),
    }


class ReplayBody(BaseModel):
    speed: float = Field(10.0, ge=0.5, le=100)


@router.post("/runs/{run_id}/replay", status_code=201)
async def replay(run_id: int, body: ReplayBody, svc: Services = Depends(services)) -> dict:
    await _run_or_404(svc, run_id)
    try:
        rep = await svc.replay.start(run_id, body.speed)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return run_dict(rep, True)


@router.delete("/runs/{run_id}")
async def delete_run(run_id: int, svc: Services = Depends(services)) -> dict:
    await _run_or_404(svc, run_id)
    if svc.runs.is_active(run_id):
        raise HTTPException(409, "stop the run before deleting it")
    await svc.replay.stop(run_id)
    await svc.store.delete_run(run_id)
    return {"ok": True, "notice": NOT_RESET_NOTICE}


class ResetBody(BaseModel):
    include_cache: bool = False


@router.post("/local-data/reset")
async def reset_local(body: ResetBody, svc: Services = Depends(services)) -> dict:
    if svc.runs.active_live_run() is not None:
        raise HTTPException(409, "stop the active run before resetting local data")
    async with svc.db.session() as s:
        for rid in list((await s.execute(select(Run.id))).scalars()):
            await svc.replay.stop(rid)
        await s.execute(delete(Event))
        await s.execute(delete(Run))
        await s.commit()
    if body.include_cache and svc.settings.cache_dir.exists():
        shutil.rmtree(svc.settings.cache_dir)
    return {"ok": True, "notice": NOT_RESET_NOTICE,
            "kept": "submission history (rejected-answer ledger) is kept to prevent duplicate wrong submissions"}


__all__ = ["router", "ui_state", "RunStatus"]
