"""Rejected-answer ledger and bounds (FR-019) plus the hardcoded-answer guard (Constitution I)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.persistence.tables import SubmissionOutcome


def normalize_answer(answer: str) -> str:
    return (answer or "").strip()


def _as_int(s: str) -> int | None:
    try:
        return int(s.strip())
    except (ValueError, AttributeError):
        return None


@dataclass
class AnswerLedger:
    rejected: set[str] = field(default_factory=set)
    lower_exclusive: int | None = None  # answer must be > this (from TOO_LOW)
    upper_exclusive: int | None = None  # answer must be < this (from TOO_HIGH)

    def record(self, answer: str, outcome: SubmissionOutcome | str) -> None:
        a = normalize_answer(answer)
        outcome = SubmissionOutcome(outcome)
        if outcome not in (SubmissionOutcome.INCORRECT, SubmissionOutcome.TOO_HIGH, SubmissionOutcome.TOO_LOW):
            return
        self.rejected.add(a)
        v = _as_int(a)
        if v is None:
            return
        if outcome == SubmissionOutcome.TOO_HIGH:
            self.upper_exclusive = v if self.upper_exclusive is None else min(self.upper_exclusive, v)
        elif outcome == SubmissionOutcome.TOO_LOW:
            self.lower_exclusive = v if self.lower_exclusive is None else max(self.lower_exclusive, v)

    def check(self, answer: str) -> tuple[bool, str]:
        a = normalize_answer(answer)
        if not a:
            return False, "empty answer"
        if a in self.rejected:
            return False, f"answer {a} was already rejected by Advent of Code"
        v = _as_int(a)
        if v is not None:
            if self.upper_exclusive is not None and v >= self.upper_exclusive:
                return False, f"answer {a} is not below the known upper bound {self.upper_exclusive} (previously too high)"
            if self.lower_exclusive is not None and v <= self.lower_exclusive:
                return False, f"answer {a} is not above the known lower bound {self.lower_exclusive} (previously too low)"
        return True, ""

    def feedback(self) -> str:
        parts = []
        if self.rejected:
            parts.append("Rejected answers: " + ", ".join(sorted(self.rejected)))
        if self.lower_exclusive is not None:
            parts.append(f"The answer is greater than {self.lower_exclusive}.")
        if self.upper_exclusive is not None:
            parts.append(f"The answer is less than {self.upper_exclusive}.")
        return " ".join(parts)


def looks_hardcoded(code: str, answer: str) -> bool:
    """True if the computed answer appears as a literal in the source (min length 4)."""
    a = normalize_answer(answer)
    if len(a) < 4:
        return False
    return re.search(r"(?<![\w.])" + re.escape(a) + r"(?![\w.])", code) is not None
