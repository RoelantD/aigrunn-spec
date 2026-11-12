"""Small repository layer used by the orchestrator and API."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select

from app.persistence.db import Database
from app.persistence.tables import (
    REJECTED_OUTCOMES,
    AccountState,
    Attempt,
    CodeRevision,
    ExecutionResult,
    ModelInvocation,
    PartProgress,
    Run,
    Submission,
    SubmissionOutcome,
)
from app.verification.ledger import AnswerLedger


class Store:
    def __init__(self, db: Database):
        self.db = db

    # runs ------------------------------------------------------------------
    async def get_run(self, run_id: int) -> Run | None:
        async with self.db.session() as s:
            return await s.get(Run, run_id)

    async def update_run(self, run_id: int, **fields: Any) -> Run:
        async with self.db.session() as s:
            run = await s.get(Run, run_id)
            if run is None:  # deleted meanwhile (e.g. local data reset)
                return None
            for k, v in fields.items():
                setattr(run, k, v)
            await s.commit()
            return run

    async def add_usage(self, run_id: int, *, cost: float, inp: int, out: int, reasoning: int | None) -> Run:
        async with self.db.session() as s:
            run = await s.get(Run, run_id)
            run.total_cost_usd = round((run.total_cost_usd or 0) + cost, 6)
            run.total_input_tokens += inp
            run.total_output_tokens += out
            run.total_reasoning_tokens += reasoning or 0
            run.total_model_calls += 1
            await s.commit()
            return run

    # parts -----------------------------------------------------------------
    async def get_part(self, run_id: int, day: int, part: int) -> PartProgress:
        async with self.db.session() as s:
            pp = (await s.execute(select(PartProgress).where(
                PartProgress.run_id == run_id, PartProgress.day == day, PartProgress.part == part))).scalar_one_or_none()
            if pp is None:
                pp = PartProgress(run_id=run_id, day=day, part=part)
                s.add(pp)
                await s.commit()
            return pp

    async def update_part(self, part_id: int, **fields: Any) -> PartProgress:
        async with self.db.session() as s:
            pp = await s.get(PartProgress, part_id)
            for k, v in fields.items():
                setattr(pp, k, v)
            pp.updated_at = datetime.now(UTC)
            await s.commit()
            return pp

    async def parts_for_run(self, run_id: int) -> list[PartProgress]:
        async with self.db.session() as s:
            return list((await s.execute(select(PartProgress).where(PartProgress.run_id == run_id)
                                         .order_by(PartProgress.day, PartProgress.part))).scalars())

    # attempts / revisions --------------------------------------------------
    async def add(self, obj):
        async with self.db.session() as s:
            s.add(obj)
            await s.commit()
            return obj

    async def merge(self, obj):
        async with self.db.session() as s:
            obj = await s.merge(obj)
            await s.commit()
            return obj

    async def next_revision_number(self, part_id: int) -> int:
        async with self.db.session() as s:
            n = (await s.execute(select(func.max(CodeRevision.revision)).where(CodeRevision.part_id == part_id))).scalar()
            return (n or 0) + 1

    async def latest_revision(self, part_id: int) -> CodeRevision | None:
        async with self.db.session() as s:
            return (await s.execute(select(CodeRevision).where(CodeRevision.part_id == part_id)
                                    .order_by(CodeRevision.revision.desc()).limit(1))).scalar_one_or_none()

    async def attempts(self, part_id: int) -> list[Attempt]:
        async with self.db.session() as s:
            return list((await s.execute(select(Attempt).where(Attempt.part_id == part_id)
                                         .order_by(Attempt.number))).scalars())

    async def revisions(self, part_id: int) -> list[tuple[CodeRevision, list[ExecutionResult]]]:
        async with self.db.session() as s:
            revs = list((await s.execute(select(CodeRevision).where(CodeRevision.part_id == part_id)
                                         .order_by(CodeRevision.revision))).scalars())
            out = []
            for r in revs:
                res = list((await s.execute(select(ExecutionResult).where(ExecutionResult.revision_id == r.id)
                                            .order_by(ExecutionResult.id))).scalars())
                out.append((r, res))
            return out

    # submissions -----------------------------------------------------------
    async def ledger(self, year: int, day: int, part: int) -> AnswerLedger:
        led = AnswerLedger()
        async with self.db.session() as s:
            rows = (await s.execute(select(Submission).where(
                Submission.year == year, Submission.day == day, Submission.part == part))).scalars()
            for sub in rows:
                if sub.outcome in REJECTED_OUTCOMES:
                    led.record(sub.answer, sub.outcome)
        return led

    async def submissions(self, run_id: int | None = None, **where) -> list[Submission]:
        async with self.db.session() as s:
            q = select(Submission)
            if run_id is not None:
                q = q.where(Submission.run_id == run_id)
            for k, v in where.items():
                q = q.where(getattr(Submission, k) == v)
            return list((await s.execute(q.order_by(Submission.id))).scalars())

    async def open_submissions(self) -> list[Submission]:
        async with self.db.session() as s:
            return list((await s.execute(select(Submission).where(Submission.outcome.in_(
                [SubmissionOutcome.PENDING, SubmissionOutcome.UNCERTAIN])))).scalars())

    # account ---------------------------------------------------------------
    async def account(self, year: int) -> AccountState:
        async with self.db.session() as s:
            acc = await s.get(AccountState, year)
            if acc is None:
                acc = AccountState(year=year, stars={})
                s.add(acc)
                await s.commit()
            return acc

    async def set_cooldown(self, year: int, until: datetime | None) -> None:
        async with self.db.session() as s:
            acc = await s.get(AccountState, year) or AccountState(year=year, stars={})
            if until is None or acc.cooldown_until is None or _aware(acc.cooldown_until) < until:
                acc.cooldown_until = until
            s.add(acc)
            await s.commit()

    async def set_stars(self, year: int, stars: dict[int, int]) -> None:
        async with self.db.session() as s:
            acc = await s.get(AccountState, year) or AccountState(year=year, stars={})
            acc.stars = {str(k): v for k, v in stars.items()}
            acc.last_calendar_fetch = datetime.now(UTC)
            s.add(acc)
            await s.commit()

    # metrics ---------------------------------------------------------------
    async def invocations(self, run_id: int) -> list[ModelInvocation]:
        async with self.db.session() as s:
            return list((await s.execute(select(ModelInvocation).where(ModelInvocation.run_id == run_id)
                                         .order_by(ModelInvocation.id))).scalars())

    async def delete_run(self, run_id: int) -> None:
        async with self.db.session() as s:
            await s.execute(delete(Run).where(Run.id == run_id))
            await s.commit()


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def aware(dt: datetime | None) -> datetime | None:
    return None if dt is None else _aware(dt)
