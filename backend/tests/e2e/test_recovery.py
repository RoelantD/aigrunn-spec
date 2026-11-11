"""Scenarios E (cooldown), G (uncertain submission), H (restart), J (infra failures), budget, sandbox infra."""

import time

import httpx

from app.models.base import ModelInfraError
from app.persistence.tables import PartState, RunStatus, Submission, SubmissionOutcome
from app.services import build_services
from tests.conftest import _nosleep
from tests.fixtures.fakes import EX_DAY1_P1, EX_DAY1_P2, proposal

STEPS = [proposal("drift", EX_DAY1_P1), proposal("products", EX_DAY1_P2)]


async def test_cooldown_is_respected_then_same_answer_resubmitted(make_env):
    env = await make_env(list(STEPS))
    env.site.cooldown_responses = 1
    env.site.cooldown_seconds = 1
    stamps: list[float] = []
    orig = env.site.handler

    def timed(req: httpx.Request):
        if req.method == "POST":
            stamps.append(time.monotonic())
        return orig(req)

    env.site.handler = timed
    env.svc.aoc._http._transport = httpx.MockTransport(timed)
    run_id = await env.run(1, 1)
    assert await env.start_and_wait(run_id) == "completed"
    assert env.site.posts[:2] == [(1, 1, "18"), (1, 1, "18")]
    assert stamps[1] - stamps[0] >= 1.5  # waited for "1s left" (+1s safety margin)
    evs = await env.events(run_id)
    assert any(e["type"] == "submit.cooldown" for e in evs)
    subs = await env.svc.store.submissions(run_id)
    assert subs[0].outcome == SubmissionOutcome.COOLDOWN
    p1 = await env.svc.store.get_part(run_id, 1, 1)
    assert p1.submissions_used == 0  # a cooldown is not a judged submission


async def test_connection_lost_after_send_is_reconciled_not_resubmitted(make_env):
    env = await make_env(list(STEPS))
    env.site.drop_next_post_after_processing = True
    run_id = await env.run(1, 1)
    assert await env.start_and_wait(run_id) == "completed"
    assert env.site.posts.count((1, 1, "18")) == 1  # never repeated
    p1 = await env.svc.store.get_part(run_id, 1, 1)
    assert p1.state == PartState.VERIFIED and not p1.previously_completed
    evs = await env.events(run_id)
    rec = [e for e in evs if e["type"] == "submit.reconciled"]
    assert rec and rec[0]["data"]["verified"] is True


async def test_unexpected_response_reconciles_and_pauses_if_not_accepted(make_env):
    env = await make_env(list(STEPS))
    env.site.unexpected_next_post = True
    run_id = await env.run(1, 1)
    assert await env.start_and_wait(run_id) == "paused"
    run = await env.svc.store.get_run(run_id)
    assert "unexpected submission response" in run.stop_reason


async def test_restart_with_inflight_submission_reconciles(make_env, settings, site):
    env = await make_env(list(STEPS))
    run_id = await env.run(1, 1)
    # Simulate: the backend crashed right after the server accepted Part 1 (response never recorded).
    site.completed[1] = {1}
    await env.svc.store.update_run(run_id, status=RunStatus.RUNNING)
    p1 = await env.svc.store.get_part(run_id, 1, 1)
    await env.svc.store.update_part(p1.id, state=PartState.SUBMITTING, candidate_answer="18", attempts_used=1)
    await env.svc.store.add(Submission(run_id=run_id, part_id=p1.id, year=2024, day=1, part=1, answer="18",
                                       outcome=SubmissionOutcome.PENDING))
    await env.svc.db.dispose()

    # "Restart": fresh services over the same database.
    svc2 = build_services(settings, aoc_transport=site.transport(), router=env.svc.router, executor=env.executor,
                          aoc_min_interval_floor_s=0.0, aoc_sleep=_nosleep)
    await svc2.db.init()
    env.workhorse.steps = [proposal("products", EX_DAY1_P2)]
    await svc2.runs.recover()
    run = await svc2.store.get_run(run_id)
    assert run.status == RunStatus.PAUSED and "restart" in run.stop_reason
    subs = await svc2.store.submissions(run_id)
    assert subs[0].outcome == SubmissionOutcome.UNCERTAIN
    await svc2.runs.resume(run_id)
    await svc2.runs.tasks[run_id]
    assert (await svc2.store.get_run(run_id)).status == RunStatus.COMPLETED
    p1 = await svc2.store.get_part(run_id, 1, 1)
    assert p1.state == PartState.VERIFIED and not p1.previously_completed
    assert (1, 1, "18") not in site.posts  # reconciled, never re-posted
    assert site.posts == [(1, 2, "287")]


async def test_model_outage_pauses_without_consuming_attempts(make_env):
    env = await make_env([ModelInfraError("HTTP 429", 429)])
    run_id = await env.run(1, 1)
    assert await env.start_and_wait(run_id) == "paused"
    p1 = await env.svc.store.get_part(run_id, 1, 1)
    assert p1.attempts_used == 0 and p1.state not in (PartState.FAILED, PartState.BLOCKED)
    run = await env.svc.store.get_run(run_id)
    assert "unavailable" in run.stop_reason
    env.workhorse.steps = list(STEPS)
    await env.svc.runs.resume(run_id)
    await env.svc.runs.tasks[run_id]
    assert (await env.svc.store.get_run(run_id)).status == RunStatus.COMPLETED
    assert (await env.svc.store.get_part(run_id, 1, 1)).attempts_used == 1


async def test_sandbox_outage_pauses_run(make_env):
    env = await make_env(list(STEPS))
    env.executor.infra_failures = 1
    run_id = await env.run(1, 1)
    assert await env.start_and_wait(run_id) == "paused"
    assert (await env.svc.store.get_part(run_id, 1, 1)).attempts_used == 0
    await env.svc.runs.resume(run_id)
    await env.svc.runs.tasks[run_id]
    assert (await env.svc.store.get_run(run_id)).status == RunStatus.COMPLETED


async def test_budget_exhaustion_stops_run(make_env):
    from app.models.pricing import Price

    env = await make_env([proposal("drift_buggy", EX_DAY1_P1)])
    env.svc.router.prices["workhorse"] = Price(1000.0, 1000.0)  # 1000 in + 500 out tokens = $1.50 per call
    run_id = await env.run(1, 1, max_spend_usd=2.0)
    assert await env.start_and_wait(run_id) == "budget_exhausted"
    assert len(env.workhorse.requests) == 2
    evs = await env.events(run_id)
    assert any(e["type"] == "budget.warning" for e in evs)


async def test_operator_pause_and_stop(make_env):
    env = await make_env(list(STEPS))
    run_id = await env.run(1, 1)
    await env.svc.runs.start(run_id)
    await env.svc.runs.pause(run_id)
    await env.svc.runs.tasks[run_id]
    assert (await env.svc.store.get_run(run_id)).status == RunStatus.PAUSED
    await env.svc.runs.stop(run_id)
    assert (await env.svc.store.get_run(run_id)).status == RunStatus.STOPPED


async def test_manual_approval_mode(make_env):
    import asyncio

    env = await make_env(list(STEPS))
    run_id = await env.run(1, 1, auto_submit=False)
    await env.svc.runs.start(run_id)
    for _ in range(200):
        p1 = await env.svc.store.get_part(run_id, 1, 1)
        if p1.awaiting_approval:
            break
        await asyncio.sleep(0.02)
    assert p1.awaiting_approval and env.site.posts == []
    await env.svc.runs.approve(run_id, 1, 1)
    for _ in range(300):
        p2 = await env.svc.store.get_part(run_id, 1, 2)
        if p2.awaiting_approval:
            break
        await asyncio.sleep(0.02)
    await env.svc.runs.approve(run_id, 1, 2)
    await asyncio.wait_for(env.svc.runs.tasks[run_id], 20)
    assert env.site.posts == [(1, 1, "18"), (1, 2, "287")]
