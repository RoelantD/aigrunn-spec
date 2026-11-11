"""Service container wiring settings → clients → run manager."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.agents.run_manager import RunManager
from app.aoc.client import AocClient
from app.config import Settings
from app.events.bus import EventBus
from app.execution.base import CodeExecutionService
from app.execution.dynamic_sessions import DynamicSessionsExecutor
from app.models.auth import AzureTokenProvider
from app.models.router import ModelRouter, build_router
from app.persistence.db import Database
from app.persistence.repo import Store
from app.replay import ReplayService


@dataclass
class Services:
    settings: Settings
    db: Database
    store: Store
    bus: EventBus
    aoc: AocClient
    router: ModelRouter
    executor: CodeExecutionService | None
    runs: RunManager
    replay: ReplayService

    async def aclose(self) -> None:
        await self.runs.shutdown()
        await self.aoc.aclose()
        await self.router.aclose()
        close = getattr(self.executor, "aclose", None)
        if close:
            await close()
        await self.db.dispose()


def build_services(
    settings: Settings,
    *,
    aoc_transport: httpx.AsyncBaseTransport | None = None,
    router: ModelRouter | None = None,
    executor: CodeExecutionService | None = None,
    aoc_min_interval_floor_s: float = 1.0,
    aoc_sleep=None,
) -> Services:
    db = Database(settings.db_path)
    store = Store(db)
    bus = EventBus(db, secrets=settings.secret_values())
    kw = {"sleep": aoc_sleep} if aoc_sleep else {}
    aoc = AocClient(
        settings.aoc_session.get_secret_value() if settings.aoc_session else None,
        settings.cache_dir,
        contact=settings.aoc_contact,
        repo_url=settings.aps_repo_url,
        min_interval_s=settings.aoc_min_interval_s,
        min_interval_floor_s=aoc_min_interval_floor_s,
        transport=aoc_transport,
        **kw,
    )
    if router is None:
        router = build_router(settings)
    if executor is None and settings.sessions_pool_endpoint:
        executor = DynamicSessionsExecutor(
            pool_endpoint=settings.sessions_pool_endpoint,
            token_fn=AzureTokenProvider(settings.sessions_token_scope),
            api_version=settings.sessions_api_version,
        )
    runs = RunManager(settings=settings, store=store, bus=bus, aoc=aoc, router=router, executor=executor)
    return Services(settings=settings, db=db, store=store, bus=bus, aoc=aoc, router=router, executor=executor,
                    runs=runs, replay=ReplayService(store, bus))
