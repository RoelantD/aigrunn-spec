"""Day 25 final-star rule (FR-022) and the configurable timeout maximum (FR-004)."""

from app.persistence.tables import PartState
from tests.fixtures.fake_aoc import synthetic_day1
from tests.fixtures.fakes import ALL_BEHAVIORS, EX_DAY1_P1, EX_DAY1_P2, drift, proposal


def _day25(site):
    pz = synthetic_day1()
    pz.title = "Final Lantern"
    pz.answers = {1: "18", 2: "0"}
    site.puzzles[25] = pz


async def test_day25_second_star_claimed_with_49_stars(make_env, site):
    _day25(site)
    for d in range(1, 25):
        site.completed[d] = {1, 2}
    env = await make_env([proposal("drift", EX_DAY1_P1)])
    run_id = await env.run(25, 25)
    assert await env.start_and_wait(run_id) == "completed"
    assert site.posts == [(25, 1, "18"), (25, 2, "0")]  # hidden form value, no model involved
    p2 = await env.svc.store.get_part(run_id, 25, 2)
    assert p2.state == PartState.VERIFIED
    assert len(env.workhorse.requests) == 1


async def test_day25_second_star_skipped_without_49_stars(make_env, site):
    _day25(site)
    site.completed[1] = {1, 2}
    env = await make_env([proposal("drift", EX_DAY1_P1)])
    run_id = await env.run(25, 25)
    assert await env.start_and_wait(run_id) == "completed"
    assert site.posts == [(25, 1, "18")]
    p2 = await env.svc.store.get_part(run_id, 25, 2)
    assert p2.state == PartState.SKIPPED and "49" in p2.status_reason


async def test_real_input_timeout_retries_with_configured_maximum(make_env):
    beh = dict(ALL_BEHAVIORS, slowish=("needs", 90, drift))
    env = await make_env([proposal("slowish", EX_DAY1_P1), proposal("slowish", EX_DAY1_P1),
                          proposal("products", EX_DAY1_P2)], behaviors=beh)
    env.site.puzzles[1].input = "1 4\n9 2\n5 5\n12 20\n" + "0 0\n" * 10  # same answers, long enough for "real"
    run_id = await env.run(1, 1, escalate_on_timeout=False, exec_timeout_s=30, exec_timeout_max_s=120)
    assert await env.start_and_wait(run_id) == "completed"
    evs = await env.events(run_id)
    started = [e for e in evs if e["type"] == "exec.started" and e["part"] == 1]
    assert started[0]["data"]["timeout_s"] == 30 and started[1]["data"]["timeout_s"] == 120
