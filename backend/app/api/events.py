"""Event history and Server-Sent Events stream (FR-031, contracts/events.md)."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from app.api.deps import services
from app.services import Services

router = APIRouter()


@router.get("/runs/{run_id}/events")
async def events(run_id: int, after_id: int = 0, limit: int = 2000, svc: Services = Depends(services)) -> list[dict]:
    return await svc.bus.history(run_id, after_id, min(limit, 10000))


@router.get("/runs/{run_id}/events/stream")
async def stream(run_id: int, request: Request, after_id: int | None = None, svc: Services = Depends(services)):
    last = request.headers.get("last-event-id")
    start_after = int(last) if last and last.isdigit() else (after_id or 0)

    async def gen():
        sub = svc.bus.subscribe(run_id)  # subscribe first so nothing is missed between history and live
        try:
            sent = start_after
            for ev in await svc.bus.history(run_id, sent, 100000):
                yield {"id": str(ev["id"]), "event": "message", "data": json.dumps(ev)}
                sent = ev["id"]
            while True:
                if await request.is_disconnected():
                    break
                try:
                    ev = await asyncio.wait_for(sub.queue.get(), timeout=15)
                except TimeoutError:
                    yield {"comment": "keep-alive"}
                    continue
                if ev["id"] <= sent:
                    continue
                sent = ev["id"]
                yield {"id": str(ev["id"]), "event": "message", "data": json.dumps(ev)}
        finally:
            svc.bus.unsubscribe(sub)

    return EventSourceResponse(gen(), ping=15)
