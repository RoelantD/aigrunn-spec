from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from app.agents import orchestrator as orch_mod
from app.config import RunConfig, Settings
from app.models.router import ModelRouter
from app.services import Services, build_services
from tests.fixtures.fake_aoc import FakeAoc, synthetic_day1, synthetic_day2
from tests.fixtures.fakes import ALL_BEHAVIORS, FakeExecutor, ScriptedProvider

TEST_SESSION = "53616c7465645f5ftestsessiontoken0123456789abcdef"


async def _nosleep(_s: float) -> None:
    await asyncio.sleep(0)


@dataclass
class Env:
    svc: Services
    site: FakeAoc
    workhorse: ScriptedProvider
    escalation: ScriptedProvider | None
    executor: FakeExecutor

    async def run(self, day_from=1, day_to=1, auto_submit=True, **cfg) -> int:
        from app.agents.run_manager import CreateRunRequest

        base = dict(aoc_min_interval_s=1.0)
        base.update(cfg)
        run = await self.svc.runs.create(CreateRunRequest(year=2024, day_from=day_from, day_to=day_to,
                                                          auto_submit=auto_submit, config=RunConfig(**base)))
        return run.id

    async def start_and_wait(self, run_id: int, timeout: float = 30) -> str:
        await self.svc.runs.start(run_id)
        await asyncio.wait_for(self.svc.runs.tasks[run_id], timeout)
        return self.svc.runs.tasks[run_id].result()

    async def events(self, run_id: int) -> list[dict]:
        return await self.svc.bus.history(run_id, 0, 100000)


@pytest.fixture(autouse=True)
def fast_reconcile(monkeypatch):
    monkeypatch.setattr(orch_mod, "RECONCILE_WAIT_S", 1)


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(_env_file=None, aps_data_dir=tmp_path / "data", aoc_session=TEST_SESSION,
                    aoc_contact="tests@example.invalid", foundry_openai_base_url=None)


@pytest.fixture
def site() -> FakeAoc:
    s = FakeAoc()
    s.puzzles[1] = synthetic_day1()
    s.puzzles[2] = synthetic_day2()
    return s


@pytest.fixture
def make_env(settings, site):
    created: list[Services] = []

    async def _make(workhorse_steps, escalation_steps=None, behaviors=None, settings_override=None) -> Env:
        wh = ScriptedProvider("workhorse", "Test Sol", list(workhorse_steps))
        es = ScriptedProvider("escalation", "Test Opus", list(escalation_steps), provider="messages") \
            if escalation_steps is not None else None
        router = ModelRouter(providers={"workhorse": wh, **({"escalation": es} if es else {})})
        ex = FakeExecutor(dict(behaviors or ALL_BEHAVIORS))
        svc = build_services(settings_override or settings, aoc_transport=site.transport(), router=router,
                             executor=ex, aoc_min_interval_floor_s=0.0, aoc_sleep=_nosleep)
        await svc.db.init()
        created.append(svc)
        return Env(svc, site, wh, es, ex)

    return _make
