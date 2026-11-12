# Test status and verification record

As of 2026-11-11, at checkpoint `demo/07-complete`. `/speckit-converge` pass 3 found no remaining gaps.

## Automated suites (run, all passing)

| Suite | Command | Result |
|-------|---------|--------|
| Backend unit + integration + e2e | `cd backend && uv run pytest` | **79 passed** (4 live tests deselected) |
| Backend lint | `cd backend && uv run ruff check .` | clean |
| Frontend unit/component | `cd frontend && npm test` | **5 passed** |
| Frontend type-check + production build | `cd frontend && npm run build` | succeeds |
| Bicep compile | `az bicep build --file infra/main.bicep` | succeeds (warnings: local Bicep 0.40 lacks types for `sessionPools@2026-07-01` and `modelProviderData`) |
| PowerShell scripts parse | PowerShell parser over `scripts/*.ps1` | no errors |
| Worktree/checkpoint scripts | `setup-demo.ps1`, `show-checkpoint.ps1` (tags 00-06), dirty-tree guard | exercised locally, see the bottom of this file |

The automated tests use **synthetic puzzles**, a stateful **fake Advent of Code website**, **scripted
model providers** and a **fake executor** that never runs code. No test submits a real answer or needs
secrets.

Acceptance scenarios A–L ([quickstart.md](../specs/001-agentic-aoc-solver/quickstart.md)) map to tests
as follows:

| Scenario | Test |
|----------|------|
| A progression | `tests/e2e/test_progression.py::test_part1_accepted_unlocks_part2_and_advances` |
| B repair | `tests/e2e/test_repair.py::test_failed_example_triggers_repair` |
| C escalation | `tests/e2e/test_escalation.py` |
| D wrong answer | `tests/e2e/test_wrong_answer.py` |
| E cooldown | `tests/e2e/test_recovery.py::test_cooldown_is_respected_then_same_answer_resubmitted` |
| F already completed | `tests/e2e/test_progression.py::test_previously_completed_part1_goes_straight_to_part2` |
| G uncertain submission | `tests/e2e/test_recovery.py::test_connection_lost_after_send_is_reconciled_not_resubmitted` |
| H restart | `tests/e2e/test_recovery.py::test_restart_with_inflight_submission_reconciles` |
| I sandbox failure | `tests/integration/test_adapters.py` (timeout, crash, 403/503), `tests/e2e/test_recovery.py::test_sandbox_outage_pauses_run`, `tests/e2e/test_repair.py::test_crashing_program_reports_error_and_recovers` |
| J model failure | `tests/integration/test_adapters.py` (429 retry, outage), `tests/e2e/test_recovery.py::test_model_outage_pauses_without_consuming_attempts` |
| K real-time dashboard | `tests/integration/test_api.py::test_full_run_over_http_with_sse_and_resume`, `frontend/tests/components.test.tsx` |
| L replay | `tests/e2e/test_replay.py`, plus replay over HTTP in `test_api.py` |

## Integrations against real services

| Integration | Status | Notes |
|-------------|--------|-------|
| Advent of Code: logged-out page structure, the 400 for input without a session, calendar classes | **Verified live (read-only)** during research on 2026-11-11 | No login and no submission |
| Advent of Code: authenticated pages, answer submission, response wording | **UNVERIFIED live.** Built from public client source code and fixtures (aocd, advent-of-code-api) and tested against the fake site | First verification happens at the presenter's preflight and test start |
| Microsoft Foundry Responses API (GPT-6.1 Sol) | **UNVERIFIED live.** Request and response shapes come from the docs and are tested with mocks | The subscription used during development had no `gpt-6.1-sol` deployment. Run `pytest -m live_azure` after `azd provision` |
| Claude Messages API in Foundry (Claude Opus 5.5) | **UNVERIFIED live.** Same as above; `output_config.format` has an automatic fallback | Same |
| Azure Container Apps Dynamic Sessions | **UNVERIFIED live.** Shapes come from the REST reference; the wrapped and flat request bodies are both handled | No session pool existed in the development subscription |
| Bicep deployment | **NOT DEPLOYED.** Compiled only | Creating cloud resources needs the operator's authorization |
| Entra ID token acquisition (`DefaultAzureCredential`) | Not exercised against these resources | |

Opt-in live tests, which need the resources above and never touch Advent of Code:

```bash
cd backend
uv run python cli.py preflight --days 1-5          # real AoC session check + both models + sandbox (no submission)
uv run pytest -m live_azure tests/live -s          # an unfamiliar synthetic puzzle solved by the real models in the real sandbox,
                                                   # including a forced escalation to Claude Opus 5.5
```

**Not executed**: `tests/live/test_live_azure.py` (all 4 tests) and the preflight against real
services. Both are blocked on provisioning.

## Script verification log

Executed by the implementing agent on 2026-11-11, before the `demo/07-complete` commit, using a
scratch demo root (`APS_DEMO_ROOT`):

- `setup-demo.ps1 -LiveRef demo/06-implement -SkipInstall` created both worktrees and `aps-data/.env`.
- `show-checkpoint.ps1` switched through `initial` … `implement`. `.specify/feature.json` was absent
  for `initial` and `constitution`, and present from `specify` onwards.
- With an untracked file in the walkthrough, `show-checkpoint.ps1 plan` and an empty answer cancelled
  the switch and kept the file. `-Force` stashed the file ("show-checkpoint backup …") before
  switching.
- The backend started from the worktree with `uvicorn app.main:get_app --factory`, using the external
  `APS_ENV_FILE`/`APS_DATA_DIR`. `/api/health` was OK, and `solver.db` was created in `aps-data`.
- `start-live-app.ps1` opens two console windows. Its commands are the ones exercised above, but the
  windowed launcher itself was not run unattended.
