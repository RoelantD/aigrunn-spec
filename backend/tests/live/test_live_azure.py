"""Opt-in live tests against REAL Microsoft Foundry deployments and a REAL Dynamic Sessions pool.

    uv run pytest -m live_azure -p no:cacheprovider tests/live

Uses an unfamiliar SYNTHETIC puzzle served by the fake website — never contacts Advent of Code and
never submits a real answer. Requires .env with FOUNDRY_* endpoints and SESSIONS_POOL_ENDPOINT.
"""

from __future__ import annotations

import asyncio

import pytest

from app.agents.run_manager import CreateRunRequest
from app.config import RunConfig, Settings
from app.models.router import build_router
from app.persistence.tables import PartState
from app.preflight import check_model, check_sandbox
from app.services import build_services
from tests.fixtures.fake_aoc import FakeAoc, FakePuzzle

pytestmark = pytest.mark.live_azure


def _settings(tmp_path) -> Settings:
    real = Settings()
    if not (real.foundry_openai_base_url and real.sessions_pool_endpoint):
        pytest.skip("FOUNDRY_OPENAI_BASE_URL and SESSIONS_POOL_ENDPOINT must be configured")
    from pydantic import SecretStr

    return real.model_copy(update={"aps_data_dir": tmp_path / "data",
                                   "aoc_session": SecretStr("synthetic-session-not-real")})


def unfamiliar_puzzle() -> FakePuzzle:
    return FakePuzzle(
        title="Clockwork Orchard",
        part1_html=(
            "<p>Each line describes a tree as <code>name: a,b,c</code>, the heights of its apples. A tree is "
            "<em>balanced</em> when the largest height is at most twice the smallest.</p><p>For example:</p>"
            "<pre><code>oak: 3,5,6\nelm: 2,9\nfig: 4,4,8\nyew: 1\n</code></pre>"
            "<p>Here oak, fig and yew are balanced; elm is not. Sum the number of apples on balanced trees: "
            "3 + 3 + 1 = <code><em>7</em></code>.</p><p>How many apples grow on balanced trees?</p>"),
        part2_html=(
            "<p>Now find, over all trees (balanced or not), the sum of each tree's largest height minus its "
            "smallest height.</p><p>In the example this is 3 + 7 + 4 + 0 = <code><em>14</em></code>.</p>"),
        input="".join(f"t{i}: {','.join(str((i * 7 + k * 13) % 23 + 1) for k in range(1 + i % 5))}\n"
                      for i in range(400)),
        answers={},
    )


def _answers(p: FakePuzzle) -> dict[int, str]:
    a1 = a2 = 0
    for line in p.input.strip().splitlines():
        hs = [int(x) for x in line.split(": ")[1].split(",")]
        if max(hs) <= 2 * min(hs):
            a1 += len(hs)
        a2 += max(hs) - min(hs)
    return {1: str(a1), 2: str(a2)}


async def test_both_models_respond(tmp_path):
    s = _settings(tmp_path)
    svc = build_services(s)
    for key in ("workhorse", "escalation"):
        r = await check_model(svc, key)
        assert r.status in ("pass", "skipped"), r.detail
    await svc.aclose()


async def test_sandbox_executes_and_blocks_egress(tmp_path):
    svc = build_services(_settings(tmp_path))
    r = await check_sandbox(svc)
    assert r.status == "pass", r.detail
    await svc.aclose()


@pytest.mark.parametrize("force_escalation", [False, True])
async def test_synthetic_puzzle_solved_by_real_models_in_real_sandbox(tmp_path, force_escalation):
    s = _settings(tmp_path)
    site = FakeAoc()
    pz = unfamiliar_puzzle()
    pz.answers = _answers(pz)
    site.puzzles[1] = pz
    router = build_router(s)
    if force_escalation and not router.has("escalation"):
        pytest.skip("escalation model not configured")
    svc = build_services(s, aoc_transport=site.transport(), router=router, aoc_min_interval_floor_s=0.0)
    await svc.db.init()
    cfg = RunConfig(aoc_min_interval_s=1, escalate_after_failures=0 if not force_escalation else 1,
                    max_spend_usd=5)
    if force_escalation:
        # Make the first workhorse attempt fail so the escalation path runs against the real Opus deployment.
        real = router.providers["workhorse"]

        class FailingOnce:
            key, display_name, deployment, provider = real.key, real.display_name, real.deployment, real.provider
            on_retry = None
            calls = 0

            async def generate(self, req):
                FailingOnce.calls += 1
                if FailingOnce.calls == 1:
                    from app.models.base import ModelOutputError
                    raise ModelOutputError("forced failure to exercise escalation")
                return await real.generate(req)

        router.providers["workhorse"] = FailingOnce()
    run = await svc.runs.create(CreateRunRequest(2024, 1, 1, True, cfg))
    await svc.runs.start(run.id)
    await asyncio.wait_for(svc.runs.tasks[run.id], 900)
    parts = {(p.day, p.part): p for p in await svc.store.parts_for_run(run.id)}
    evs = await svc.bus.history(run.id)
    print("\n".join(f"{e['type']}: {e['message']}" for e in evs))
    assert parts[(1, 1)].state == PartState.VERIFIED, parts[(1, 1)].status_reason
    assert parts[(1, 2)].state == PartState.VERIFIED, parts[(1, 2)].status_reason
    if force_escalation:
        assert any(e["type"] == "agent.escalation" for e in evs)
    await svc.aclose()
