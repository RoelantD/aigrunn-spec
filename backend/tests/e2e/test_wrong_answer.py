"""Scenario D: rejected answer is recorded, never resubmitted, and drives a diagnosis attempt."""

from app.persistence.tables import PartState, SubmissionOutcome
from tests.fixtures.fakes import ALL_BEHAVIORS, EX_DAY1_P1, EX_DAY1_P2, proposal


def wrong_but_passes_examples(text: str) -> str:
    # Passes the example (8) but is wrong on the real input (returns 20 instead of 18).
    return "8" if len(text.strip().splitlines()) == 3 else "20"


async def test_rejected_answer_not_resubmitted(make_env):
    beh = dict(ALL_BEHAVIORS, wrong=wrong_but_passes_examples)
    env = await make_env([proposal("wrong", EX_DAY1_P1), proposal("wrong", EX_DAY1_P1),
                          proposal("drift", EX_DAY1_P1), proposal("products", EX_DAY1_P2)], behaviors=beh)
    run_id = await env.run(1, 1)
    assert await env.start_and_wait(run_id) == "completed"
    assert env.site.posts == [(1, 1, "20"), (1, 1, "18"), (1, 2, "287")]
    subs = await env.svc.store.submissions(run_id)
    assert subs[0].outcome == SubmissionOutcome.TOO_HIGH
    evs = await env.events(run_id)
    assert any(e["type"] == "submit.skipped_duplicate" for e in evs)
    # The diagnosis prompt carries the website feedback.
    assert "rejected the answer 20: it is too high" in env.workhorse.requests[1].user
    assert "less than 20" in env.workhorse.requests[1].user


async def test_submission_limit_fails_part(make_env):
    seq = iter(["21", "10", "19", "12"])
    beh = dict(ALL_BEHAVIORS, rnd=lambda t: "8" if len(t.strip().splitlines()) == 3 else next(seq))
    env = await make_env([proposal("rnd", EX_DAY1_P1)], behaviors=beh)
    run_id = await env.run(1, 1, max_submissions_per_part=2)
    await env.start_and_wait(run_id)
    p1 = await env.svc.store.get_part(run_id, 1, 1)
    assert p1.state == PartState.FAILED and "submission limit" in p1.status_reason
    assert len(env.site.posts) == 2
