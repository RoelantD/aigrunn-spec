"""Scenario A (successful live progression) and F (already completed Part 1); SC-006 traffic budget."""

from app.persistence.tables import PartState
from tests.fixtures.fakes import EX_DAY1_P1, EX_DAY1_P2, EX_DAY2_P1, EX_DAY2_P2, proposal


async def test_part1_accepted_unlocks_part2_and_advances(make_env):
    env = await make_env([proposal("drift", EX_DAY1_P1), proposal("products", EX_DAY1_P2),
                          proposal("moss", EX_DAY2_P1), proposal("moss_neighbors", EX_DAY2_P2)])
    run_id = await env.run(1, 2)
    status = await env.start_and_wait(run_id)
    assert status == "completed"
    parts = await env.svc.store.parts_for_run(run_id)
    assert [(p.day, p.part, p.state, p.accepted_answer) for p in parts] == [
        (1, 1, PartState.VERIFIED, "18"), (1, 2, PartState.VERIFIED, "287"),
        (2, 1, PartState.VERIFIED, "7"), (2, 2, PartState.VERIFIED, "6")]
    assert env.site.posts == [(1, 1, "18"), (1, 2, "287"), (2, 1, "7"), (2, 2, "6")]
    evs = await env.events(run_id)
    types = [e["type"] for e in evs]
    assert types.count("star.earned") == 4
    # Part 2 is only fetched after Part 1 acceptance: only the Part 2 prompt contains the Part 2 text.
    p2_prompt = env.workhorse.requests[1].user
    assert "Part Two" in p2_prompt and "Part 1 was solved and accepted (answer 18)" in p2_prompt
    assert "Part Two" not in env.workhorse.requests[0].user
    # Stars appear only after server acceptance.
    first_star = types.index("star.earned")
    assert any(e["type"] == "submit.result" and e["data"].get("outcome") == "CORRECT" for e in evs[:first_star])
    # SC-006: website traffic per day stays small; inputs fetched once per day.
    gets_input = [r for r in env.site.requests if r[1].endswith("/input")]
    assert len(gets_input) == 2
    assert len(env.site.requests) / 2 <= 10, env.site.requests


async def test_personal_input_never_sent_to_models(make_env):
    env = await make_env([proposal("drift", EX_DAY1_P1), proposal("products", EX_DAY1_P2)])
    extra = "".join(f"{i} {i + 1}\n" for i in range(100, 400))
    env.site.puzzles[1].input = "1 4\n9 2\n5 5\n12 20\n" + extra
    env.site.puzzles[1].answers = {1: str(18 + 300), 2: str(287 + sum(i * (i + 1) for i in range(100, 400)))}
    run_id = await env.run(1, 1)
    assert await env.start_and_wait(run_id) == "completed"
    for req in env.workhorse.requests:
        assert "399 400" not in req.user  # beyond the 5-line preview
        assert "real_input_shape" in req.user


async def test_previously_completed_part1_goes_straight_to_part2(make_env):
    env = await make_env([proposal("products", EX_DAY1_P2)])
    env.site.completed[1] = {1}
    run_id = await env.run(1, 1)
    assert await env.start_and_wait(run_id) == "completed"
    p1 = await env.svc.store.get_part(run_id, 1, 1)
    p2 = await env.svc.store.get_part(run_id, 1, 2)
    assert p1.state == PartState.VERIFIED and p1.previously_completed
    assert p2.state == PartState.VERIFIED and not p2.previously_completed
    assert env.site.posts == [(1, 2, "287")]
    assert len(env.workhorse.requests) == 1


async def test_fully_completed_day_is_skipped_without_model_calls(make_env):
    env = await make_env([proposal("drift", EX_DAY1_P1)])
    env.site.completed[1] = {1, 2}
    run_id = await env.run(1, 1)
    assert await env.start_and_wait(run_id) == "completed"
    assert env.workhorse.requests == []
    assert env.site.posts == []
