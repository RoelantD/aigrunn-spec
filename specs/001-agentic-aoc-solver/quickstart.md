# Quickstart & Validation Guide

## Prerequisites

- Python 3.12 + `uv`, Node 22 + npm, Azure CLI (logged in), Git.
- Provisioned Azure resources (see `infra/` and `demo/PRESENTER_GUIDE.md`): AIServices account with
  deployments for the workhorse and escalation models, a Dynamic Sessions pool (PythonLTS,
  EgressDisabled), and role assignments for the operator.
- `.env` (copied from `.env.example`) with endpoints, deployment names, `AOC_SESSION`,
  `AOC_CONTACT`, `APS_DATA_DIR`.

## Run locally

```bash
cd backend && uv sync && uv run uvicorn app.main:app --host 127.0.0.1 --port 8765
cd frontend && npm install && npm run dev -- --port 5175
```

Open http://127.0.0.1:5175 (dashboard) or http://127.0.0.1:5175/present (presentation view).

## Automated validation (no secrets, no real submissions)

```bash
cd backend && uv run pytest              # unit + integration + e2e with fakes
cd frontend && npm test
```

| Scenario | Test location | Expected |
|----------|---------------|----------|
| A Successful progression | `tests/e2e/test_progression.py` | P1 accepted → P2 fetched → P2 accepted → next day |
| B Failed example → repair | `tests/e2e/test_repair.py` | repair attempt passes |
| C Escalation | `tests/e2e/test_escalation.py` | escalation model invoked after 3 failures |
| D Wrong answer | `tests/e2e/test_wrong_answer.py` | ledger blocks identical resubmission |
| E Cooldown | `tests/e2e/test_cooldown.py` | no POST before deadline |
| F Already completed P1 | `tests/e2e/test_progression.py` | P1 previously completed, P2 solved |
| G Network failure on submit | `tests/e2e/test_uncertain_submission.py` | reconcile via GET, no double POST |
| H Restart | `tests/e2e/test_restart.py` | progress restored, run resumable |
| I Sandbox failure | `tests/unit/test_harness.py`, `tests/integration/test_dynamic_sessions.py` | crash/timeout classified, backend stable |
| J Model service failure | `tests/integration/test_model_adapters.py` | 429 retried, not counted as attempt |
| K Real-time dashboard | `tests/integration/test_sse.py`, `frontend/tests` | events streamed, resume by Last-Event-ID |
| L Replay | `tests/e2e/test_replay.py` | replay events flagged, no external calls |

## Opt-in live validation (requires cloud resources; never submits)

```bash
cd backend
uv run python -m cli preflight                    # all checks, no submissions
uv run pytest -m live_azure                       # real models + sandbox on a synthetic puzzle
```

Expected: synthetic puzzle solved by the workhorse model in the sandbox; a forced escalation call
to the escalation model succeeds; sandbox egress probe fails to connect (isolation confirmed).

## Live demo run (real submission)

Start the dashboard, choose year 2024 and a range with unsolved parts, tick "Authorize automatic
answer submission", Start. Expect stars only after "Advent of Code accepted the answer".
