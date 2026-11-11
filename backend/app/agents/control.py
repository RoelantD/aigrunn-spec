"""Cooperative run control: pause/stop signals and interruptible waits."""

from __future__ import annotations

import asyncio


class RunInterrupt(Exception):  # noqa: N818 - control-flow signal
    status: str = "paused"

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class PauseRun(RunInterrupt):
    status = "paused"


class StopRun(RunInterrupt):
    status = "stopped"


class BudgetExhausted(RunInterrupt):
    status = "budget_exhausted"


class RunControl:
    def __init__(self) -> None:
        self.pause_requested = False
        self.stop_requested = False
        self._wake = asyncio.Event()
        self._approvals: dict[tuple[int, int], asyncio.Event] = {}

    def request_pause(self) -> None:
        self.pause_requested = True
        self._wake.set()

    def request_stop(self) -> None:
        self.stop_requested = True
        self._wake.set()

    def checkpoint(self) -> None:
        if self.stop_requested:
            raise StopRun("stopped by operator")
        if self.pause_requested:
            raise PauseRun("paused by operator")

    async def sleep(self, seconds: float) -> None:
        """Sleep that wakes immediately on pause/stop (then raises at the checkpoint)."""
        if seconds > 0:
            self._wake.clear()
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=seconds)
            except TimeoutError:
                pass
        self.checkpoint()

    def approval_event(self, day: int, part: int) -> asyncio.Event:
        return self._approvals.setdefault((day, part), asyncio.Event())

    def approve(self, day: int, part: int) -> None:
        self.approval_event(day, part).set()
        self._wake.set()
