"""SQLAlchemy ORM tables per specs/001-agentic-aoc-solver/data-model.md."""

from __future__ import annotations

import enum
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class RunStatus(enum.StrEnum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    BUDGET_EXHAUSTED = "budget_exhausted"
    FAILED = "failed"


class RunMode(enum.StrEnum):
    LIVE = "live"
    REPLAY = "replay"


class PartState(enum.StrEnum):
    NOT_STARTED = "NOT_STARTED"
    FETCHING = "FETCHING"
    ANALYZING = "ANALYZING"
    GENERATING = "GENERATING"
    TESTING = "TESTING"
    REPAIRING = "REPAIRING"
    ESCALATING = "ESCALATING"
    EXECUTING_INPUT = "EXECUTING_INPUT"
    READY_TO_SUBMIT = "READY_TO_SUBMIT"
    SUBMITTING = "SUBMITTING"
    WAITING_FOR_COOLDOWN = "WAITING_FOR_COOLDOWN"
    VERIFIED = "VERIFIED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


TERMINAL_PART_STATES = {PartState.VERIFIED, PartState.BLOCKED, PartState.FAILED, PartState.SKIPPED}


class SubmissionOutcome(enum.StrEnum):
    PENDING = "PENDING"
    UNCERTAIN = "UNCERTAIN"
    CORRECT = "CORRECT"
    INCORRECT = "INCORRECT"
    TOO_HIGH = "TOO_HIGH"
    TOO_LOW = "TOO_LOW"
    COOLDOWN = "COOLDOWN"
    ALREADY_COMPLETED = "ALREADY_COMPLETED"
    LOCKED = "LOCKED"
    AUTH_FAILED = "AUTH_FAILED"
    UNEXPECTED = "UNEXPECTED"


REJECTED_OUTCOMES = {SubmissionOutcome.INCORRECT, SubmissionOutcome.TOO_HIGH, SubmissionOutcome.TOO_LOW}


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mode: Mapped[str] = mapped_column(String(10), default=RunMode.LIVE)
    source_run_id: Mapped[int | None] = mapped_column(ForeignKey("runs.id"), nullable=True)
    year: Mapped[int] = mapped_column(Integer)
    day_from: Mapped[int] = mapped_column(Integer)
    day_to: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default=RunStatus.CREATED)
    stop_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    auto_submit: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    current_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_part: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    elapsed_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    total_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_reasoning_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_model_calls: Mapped[int] = mapped_column(Integer, default=0)


class PartProgress(Base):
    __tablename__ = "part_progress"
    __table_args__ = (UniqueConstraint("run_id", "day", "part"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    day: Mapped[int] = mapped_column(Integer)
    part: Mapped[int] = mapped_column(Integer)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(30), default=PartState.NOT_STARTED)
    previously_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    tests_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    candidate_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    accepted_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts_used: Mapped[int] = mapped_column(Integer, default=0)
    submissions_used: Mapped[int] = mapped_column(Integer, default=0)
    current_model: Mapped[str | None] = mapped_column(String(20), nullable=True)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    status_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    understanding: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    awaiting_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Attempt(Base):
    __tablename__ = "attempts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    part_id: Mapped[int] = mapped_column(ForeignKey("part_progress.id", ondelete="CASCADE"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(20))  # initial | repair | escalation | post_rejection
    model_key: Mapped[str] = mapped_column(String(20))
    effort: Mapped[str] = mapped_column(String(10))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    algorithm: Mapped[str | None] = mapped_column(Text, nullable=True)
    diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[str] = mapped_column(String(30), default="pending")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CodeRevision(Base):
    __tablename__ = "code_revisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("attempts.id", ondelete="CASCADE"), index=True)
    part_id: Mapped[int] = mapped_column(ForeignKey("part_progress.id", ondelete="CASCADE"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    model_key: Mapped[str] = mapped_column(String(20))
    code: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ExecutionResult(Base):
    __tablename__ = "execution_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    revision_id: Mapped[int] = mapped_column(ForeignKey("code_revisions.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(10))  # examples | input | probe
    status: Mapped[str] = mapped_column(String(15))  # ok | error | timeout | infra_error
    cases: Mapped[list] = mapped_column(JSON, default=list)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    stdout: Mapped[str] = mapped_column(Text, default="")
    stderr: Mapped[str] = mapped_column(Text, default="")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    timed_out: Mapped[bool] = mapped_column(Boolean, default=False)
    correlation_id: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ExampleCase(Base):
    __tablename__ = "example_cases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    part_id: Mapped[int] = mapped_column(ForeignKey("part_progress.id", ondelete="CASCADE"), index=True)
    index: Mapped[int] = mapped_column(Integer)
    input_ref: Mapped[str] = mapped_column(String(64))
    expected: Mapped[str | None] = mapped_column(Text, nullable=True)
    reliable: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class ModelInvocation(Base):
    __tablename__ = "model_invocations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    part_id: Mapped[int | None] = mapped_column(ForeignKey("part_progress.id", ondelete="CASCADE"), nullable=True)
    attempt_id: Mapped[int | None] = mapped_column(ForeignKey("attempts.id", ondelete="CASCADE"), nullable=True)
    model_key: Mapped[str] = mapped_column(String(20))
    deployment: Mapped[str] = mapped_column(String(100))
    provider: Mapped[str] = mapped_column(String(20))
    purpose: Mapped[str] = mapped_column(String(30))
    effort: Mapped[str] = mapped_column(String(10))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    reasoning_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="ok")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id", ondelete="SET NULL"), nullable=True, index=True)
    part_id: Mapped[int | None] = mapped_column(ForeignKey("part_progress.id", ondelete="SET NULL"), nullable=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    day: Mapped[int] = mapped_column(Integer)
    part: Mapped[int] = mapped_column(Integer)
    answer: Mapped[str] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(String(20), default=SubmissionOutcome.PENDING)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    wait_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AccountState(Base):
    __tablename__ = "account_state"
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stars: Mapped[dict] = mapped_column(JSON, default=dict)
    last_calendar_fetch: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(40))
    day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    part: Mapped[int | None] = mapped_column(Integer, nullable=True)
    level: Mapped[str] = mapped_column(String(10), default="info")
    message: Mapped[str] = mapped_column(Text)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    replay: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
