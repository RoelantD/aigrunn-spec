"""Model routing / escalation policy (research §6 defaults, FR-014)."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import RunConfig


@dataclass(frozen=True)
class AttemptPlan:
    model_key: str  # workhorse | escalation
    effort: str
    kind: str  # initial | repair | escalation | post_rejection
    escalate_reason: str | None = None


def plan_attempt(
    number: int,
    cfg: RunConfig,
    *,
    last_failure: str | None,
    already_escalated: bool,
    escalation_available: bool,
    after_rejection: bool = False,
) -> AttemptPlan:
    """Decide model and effort for attempt `number` (1-based).

    - Attempts below the threshold use the workhorse with the configured effort ladder.
    - After `escalate_after_failures` failures (or an earlier timeout when enabled) switch to the
      escalation model; once escalated a part stays escalated.
    """
    failures = number - 1
    kind = "initial" if number == 1 else ("post_rejection" if after_rejection else "repair")
    if escalation_available:
        if already_escalated:
            return AttemptPlan("escalation", cfg.escalation_effort, kind)
        reason = None
        if cfg.escalate_after_failures and failures >= cfg.escalate_after_failures:
            reason = f"{failures} unsuccessful attempts with the workhorse model"
        elif cfg.escalate_on_timeout and last_failure == "timeout" and number >= 2:
            reason = "the previous solution timed out (algorithmic complexity)"
        if reason:
            return AttemptPlan("escalation", cfg.escalation_effort, "escalation", reason)
    efforts = cfg.workhorse_efforts
    return AttemptPlan("workhorse", efforts[min(failures, len(efforts) - 1)], kind)
