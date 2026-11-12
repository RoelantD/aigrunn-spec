"""Scenario L: a recorded run replays without contacting any external service, labelled as replay."""

import asyncio

from app.persistence.tables import PartState, RunMode, RunStatus
from tests.fixtures.fakes import EX_DAY1_P1, EX_DAY1_P2, proposal


async def test_replay_is_offline_and_labelled(make_env):
    env = await make_env([proposal("drift_buggy", EX_DAY1_P1), proposal("drift", EX_DAY1_P1),
                          proposal("products", EX_DAY1_P2)])
    run_id = await env.run(1, 1)
    assert await env.start_and_wait(run_id) == "completed"
    site_requests, model_requests = len(env.site.requests), len(env.workhorse.requests)
    exec_calls = len(env.executor.calls)

    rep = await env.svc.replay.start(run_id, speed=100)
    await asyncio.wait_for(env.svc.replay.tasks[rep.id], 20)
    assert len(env.site.requests) == site_requests
    assert len(env.workhorse.requests) == model_requests
    assert len(env.executor.calls) == exec_calls

    rep_run = await env.svc.store.get_run(rep.id)
    assert rep_run.mode == RunMode.REPLAY and rep_run.status == RunStatus.COMPLETED
    evs = await env.events(rep.id)
    assert evs and all(e["replay"] for e in evs)
    assert "REPLAY" in evs[0]["message"]
    src_types = [e["type"] for e in await env.events(run_id) if e["type"] != "run.created"]
    assert [e["type"] for e in evs[1:-1]] == src_types
    parts = {(p.day, p.part): p for p in await env.svc.store.parts_for_run(rep.id)}
    assert parts[(1, 1)].state == PartState.VERIFIED and parts[(1, 2)].state == PartState.VERIFIED
