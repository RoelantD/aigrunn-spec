"""Scenario C: repeated workhorse failures escalate to the escalation model with handover context."""

from app.persistence.tables import PartState
from tests.fixtures.fakes import EX_DAY1_P1, EX_DAY1_P2, EX_DAY2_P1, EX_DAY2_P2, proposal


async def test_escalates_after_three_failures(make_env):
    env = await make_env([proposal("drift_buggy", EX_DAY1_P1, algorithm="subtract readings")] * 3
                         + [proposal("products", EX_DAY1_P2)],
                         escalation_steps=[proposal("drift", EX_DAY1_P1, algorithm="absolute difference")])
    run_id = await env.run(1, 1)
    assert await env.start_and_wait(run_id) == "completed"
    p1 = await env.svc.store.get_part(run_id, 1, 1)
    assert p1.state == PartState.VERIFIED and p1.escalated and p1.attempts_used == 4
    assert len(env.workhorse.requests) == 4 and len(env.escalation.requests) == 1  # 3 for P1, 1 for P2
    handover = env.escalation.requests[0].user
    assert "taking over" in handover and "subtract readings" in handover and "expected: 8" in handover
    evs = await env.events(run_id)
    esc = [e for e in evs if e["type"] == "agent.escalation"]
    assert len(esc) == 1 and "Test Sol → Test Opus" in esc[0]["message"]
    assert [r.effort for r in env.workhorse.requests[:3]] == ["medium", "medium", "high"]
    p2 = await env.svc.store.get_part(run_id, 1, 2)
    assert not p2.escalated  # escalation is per part


async def test_timeout_escalates_early(make_env):
    env = await make_env([proposal("slow", EX_DAY1_P1), proposal("products", EX_DAY1_P2)],
                         escalation_steps=[proposal("drift", EX_DAY1_P1)])
    run_id = await env.run(1, 1)
    assert await env.start_and_wait(run_id) == "completed"
    assert len(env.workhorse.requests) == 2 and len(env.escalation.requests) == 1
    evs = await env.events(run_id)
    assert any(e["type"] == "agent.escalation" and "timed out" in e["data"]["reason"] for e in evs)


async def test_attempt_limit_marks_failed_and_blocks_part2_then_continues(make_env):
    steps = [proposal("drift_buggy", EX_DAY1_P1)] * 3 + [proposal("moss", EX_DAY2_P1),
                                                          proposal("moss_neighbors", EX_DAY2_P2)]
    env = await make_env(steps)
    run_id = await env.run(1, 2, max_attempts_per_part=3)
    assert await env.start_and_wait(run_id) == "completed"
    parts = {(p.day, p.part): p for p in await env.svc.store.parts_for_run(run_id)}
    assert parts[(1, 1)].state == PartState.FAILED
    assert parts[(1, 2)].state == PartState.BLOCKED
    assert parts[(2, 1)].state == PartState.VERIFIED and parts[(2, 2)].state == PartState.VERIFIED
