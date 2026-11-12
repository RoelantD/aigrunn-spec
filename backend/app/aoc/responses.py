"""Classification of answer-submission responses (contracts/aoc-client.md rule 5, research R4)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.aoc.parser import is_logged_in, main_article_text
from app.persistence.tables import SubmissionOutcome

_WAIT_RECENT = re.compile(r"You have (?:(\d+)m )?(\d+)s left to wait", re.I)
_WAIT_WRONG = re.compile(r"please wait (one|\d+) minutes?", re.I)


@dataclass
class SubmitResult:
    outcome: SubmissionOutcome
    message: str
    wait_seconds: int | None = None


def classify_submission(html: str, status_code: int = 200) -> SubmitResult:
    if status_code in (301, 302, 303, 307, 308) or not is_logged_in(html):
        return SubmitResult(SubmissionOutcome.AUTH_FAILED, "Not logged in (session invalid or expired).")
    text = main_article_text(html)
    msg = text[:1000]
    if "That's the right answer" in text or "You've finished every puzzle" in text:
        return SubmitResult(SubmissionOutcome.CORRECT, msg)
    if "Did you already complete it" in text:
        return SubmitResult(SubmissionOutcome.ALREADY_COMPLETED, msg)
    if "You gave an answer too recently" in text:
        m = _WAIT_RECENT.search(text)
        wait = (int(m.group(1) or 0) * 60 + int(m.group(2))) if m else 60
        return SubmitResult(SubmissionOutcome.COOLDOWN, msg, wait)
    if "That's not the right answer" in text:
        m = _WAIT_WRONG.search(text)
        wait = None
        if m:
            wait = 60 if m.group(1).lower() == "one" else int(m.group(1)) * 60
        lowered = text.lower()
        if "answer is too high" in lowered:
            return SubmitResult(SubmissionOutcome.TOO_HIGH, msg, wait)
        if "answer is too low" in lowered:
            return SubmitResult(SubmissionOutcome.TOO_LOW, msg, wait)
        return SubmitResult(SubmissionOutcome.INCORRECT, msg, wait)
    if "You don't seem to be solving the right level" in text:
        return SubmitResult(SubmissionOutcome.LOCKED, msg)
    if status_code >= 400:
        return SubmitResult(SubmissionOutcome.UNEXPECTED, f"HTTP {status_code}: {msg[:300]}")
    return SubmitResult(SubmissionOutcome.UNEXPECTED, msg)
