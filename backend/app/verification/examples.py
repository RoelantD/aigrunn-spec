"""Example verification (research R3): accept model-extracted examples only if they are verbatim."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class VerifiedExample:
    input: str
    expected: str | None
    reliable: bool
    note: str


def _norm(s: str) -> str:
    return "\n".join(line.rstrip() for line in s.replace("\r\n", "\n").split("\n")).strip("\n")


def _in_blocks(candidate: str, blocks: list[str]) -> bool:
    c = _norm(candidate)
    if not c:
        return False
    return any(c in _norm(b) for b in blocks)


def verify_examples(
    proposed: list[dict[str, Any]],
    pre_blocks: list[str],
    emphasized: list[str],
    article_text: str,
    max_examples: int = 8,
) -> tuple[list[VerifiedExample], list[str]]:
    """Return (accepted examples, rejection notes).

    - input must occur verbatim (modulo trailing whitespace) in a <pre> block of the puzzle;
    - expected output is "reliable" only if it appears as emphasised text or inline code in the
      current part's article.
    """
    accepted: list[VerifiedExample] = []
    notes: list[str] = []
    seen: set[tuple[str, str | None]] = set()
    emph = {e.strip() for e in emphasized}
    for i, ex in enumerate(proposed or []):
        raw_in = str(ex.get("input") or "")
        exp = ex.get("expected_output")
        exp = None if exp in (None, "") else str(exp).strip()
        if not _in_blocks(raw_in, pre_blocks):
            notes.append(f"example {i + 1} discarded: input not found verbatim in the puzzle")
            continue
        reliable = False
        if exp is not None:
            reliable = exp in emph or bool(re.search(r"`" + re.escape(exp) + r"`", article_text)) or (
                f"**{exp}**" in article_text
            )
            if not reliable:
                notes.append(f"example {i + 1}: expected output {exp!r} not found in puzzle text (treated as unreliable)")
        key = (_norm(raw_in), exp)
        if key in seen:
            continue
        seen.add(key)
        accepted.append(VerifiedExample(input=_norm(raw_in) + "\n", expected=exp if reliable else None,
                                        reliable=reliable, note=str(ex.get("note") or "")))
        if len(accepted) >= max_examples:
            break
    return accepted, notes


def outputs_match(expected: str, actual: str | None) -> bool:
    if actual is None:
        return False
    return expected.strip() == actual.strip()
