"""Scenario B: failing example -> feedback -> repaired program passes; example and hardcode guards."""

from app.persistence.tables import PartState
from tests.fixtures.fakes import ALL_BEHAVIORS, EX_DAY1_P1, EX_DAY1_P2, program, proposal


async def test_failed_example_triggers_repair(make_env):
    env = await make_env([proposal("drift_buggy", EX_DAY1_P1), proposal("drift", EX_DAY1_P1, diagnosis="abs"),
                          proposal("products", EX_DAY1_P2)])
    run_id = await env.run(1, 1)
    assert await env.start_and_wait(run_id) == "completed"
    p1 = await env.svc.store.get_part(run_id, 1, 1)
    assert p1.state == PartState.VERIFIED and p1.attempts_used == 2
    evs = await env.events(run_id)
    fails = [e for e in evs if e["type"] == "test.result" and not e["data"]["passed"]]
    assert fails and fails[0]["message"] == "Test failed: expected 8, received -4"
    repair_prompt = env.workhorse.requests[1].user
    assert "expected: 8" in repair_prompt and "actual: -4" in repair_prompt
    assert env.site.posts[0] == (1, 1, "18")  # buggy candidate never submitted
    revs = await env.svc.store.revisions(p1.id)
    assert [r.revision for r, _ in revs] == [1, 2]


async def test_hallucinated_example_is_discarded(make_env):
    bogus = [{"input": "100 1\n", "expected_output": "99", "note": ""}, *EX_DAY1_P1]
    env = await make_env([proposal("drift", bogus), proposal("products", EX_DAY1_P2)])
    run_id = await env.run(1, 1)
    assert await env.start_and_wait(run_id) == "completed"
    evs = await env.events(run_id)
    assert any(e["type"] == "test.note" and "not found verbatim" in e["message"] for e in evs)


async def test_hardcoded_answer_is_rejected(make_env):
    beh = dict(ALL_BEHAVIORS, big=lambda t: "8" if len(t.strip().splitlines()) == 3 else "123456")
    hard = proposal("big", EX_DAY1_P1, code=program("big", "    return '123456'\n"))
    env = await make_env([hard, proposal("drift", EX_DAY1_P1), proposal("products", EX_DAY1_P2)], behaviors=beh)
    run_id = await env.run(1, 1)
    assert await env.start_and_wait(run_id) == "completed"
    evs = await env.events(run_id)
    assert any(e["type"] == "agent.repair" and "literal" in e["message"] for e in evs)
    assert (1, 1, "123456") not in env.site.posts


async def test_crashing_program_reports_error_and_recovers(make_env):
    env = await make_env([proposal("crash", EX_DAY1_P1), proposal("drift", EX_DAY1_P1),
                          proposal("products", EX_DAY1_P2)])
    run_id = await env.run(1, 1)
    assert await env.start_and_wait(run_id) == "completed"
    evs = await env.events(run_id)
    assert any(e["type"] == "test.result" and "ZeroDivisionError" in e["message"] for e in evs)
