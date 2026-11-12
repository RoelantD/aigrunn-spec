"""Event bus: persist every event first, then fan out to live subscribers (FR-030, FR-031)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.persistence.db import Database
from app.persistence.tables import Event, iso_utc
from app.security import redact_obj


def event_to_dict(e: Event) -> dict[str, Any]:
    return {
        "id": e.id,
        "run_id": e.run_id,
        "type": e.type,
        "day": e.day,
        "part": e.part,
        "level": e.level,
        "message": e.message,
        "data": e.data or {},
        "replay": e.replay,
        "created_at": iso_utc(e.created_at) if isinstance(e.created_at, datetime) else e.created_at,
    }


@dataclass
class _Subscriber:
    run_id: int | None
    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=10000))


class EventBus:
    def __init__(self, db: Database, secrets: list[str] | None = None):
        self.db = db
        self._secrets = list(secrets or [])
        self._subs: list[_Subscriber] = []
        self._lock = asyncio.Lock()

    async def emit(
        self,
        run_id: int,
        type: str,
        message: str,
        *,
        level: str = "info",
        day: int | None = None,
        part: int | None = None,
        data: dict[str, Any] | None = None,
        replay: bool = False,
    ) -> dict[str, Any]:
        # Defence in depth: never let a secret value reach storage or clients.
        message = redact_obj(message, self._secrets)
        data = redact_obj(data or {}, self._secrets)
        async with self._lock:  # keeps id order == delivery order
            async with self.db.session() as s:
                ev = Event(run_id=run_id, type=type, message=message, level=level, day=day, part=part,
                           data=data, replay=replay)
                s.add(ev)
                await s.commit()
                payload = event_to_dict(ev)
            for sub in list(self._subs):
                if sub.run_id is None or sub.run_id == run_id:
                    try:
                        sub.queue.put_nowait(payload)
                    except asyncio.QueueFull:  # pragma: no cover - slow client; it can resume by id
                        pass
        return payload

    def subscribe(self, run_id: int | None) -> _Subscriber:
        sub = _Subscriber(run_id=run_id)
        self._subs.append(sub)
        return sub

    def unsubscribe(self, sub: _Subscriber) -> None:
        if sub in self._subs:
            self._subs.remove(sub)

    async def history(self, run_id: int, after_id: int = 0, limit: int = 5000) -> list[dict[str, Any]]:
        async with self.db.session() as s:
            rows = (
                await s.execute(
                    select(Event).where(Event.run_id == run_id, Event.id > after_id).order_by(Event.id).limit(limit)
                )
            ).scalars().all()
            return [event_to_dict(e) for e in rows]
