---

description: "Task list for the Agentic Advent of Code Solver"
---

# Tasks: Agentic Advent of Code Solver

**Input**: Design documents from `specs/001-agentic-aoc-solver/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Requested — Constitution VI and spec acceptance scenarios A–L require unit, integration
and end-to-end tests with synthetic puzzles and mocked HTTP. Live-cloud tests are opt-in markers.

**Organization**: Tasks are grouped by user story so each story is an independently testable
increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1…US7)

## Path Conventions

Backend in `backend/app/`, backend tests in `backend/tests/`, frontend in `frontend/src/`,
frontend tests in `frontend/tests/`, infrastructure in `infra/`, demo scripts in `scripts/`,
presenter docs in `demo/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create backend project with uv (Python 3.12), dependencies from plan.md, ruff + pytest config in backend/pyproject.toml
- [X] T002 [P] Create frontend project (Vite + React + TypeScript + Tailwind + Radix + lucide + prism-react-renderer + Vitest) in frontend/package.json, frontend/vite.config.ts
- [X] T003 [P] Create .env.example documenting every setting (no secrets) at .env.example
- [X] T004 [P] Add README with purpose, respectful-automation policy and acknowledgement of the puzzle author's stance on AI in README.md (FR-045)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story

- [X] T005 Implement Settings (pydantic-settings, SecretStr for `AOC_SESSION`, API keys; `APS_DATA_DIR`; model deployments; prices; endpoint allowlist validation) in backend/app/config.py
- [X] T006 [P] Implement structlog configuration with secret-redaction processor in backend/app/logging.py
- [X] T007 [P] Implement URL allowlist + redaction helpers in backend/app/security.py (FR-041, FR-042)
- [X] T008 Implement SQLAlchemy async engine/session factory on `<APS_DATA_DIR>/solver.db` in backend/app/persistence/db.py
- [X] T009 Implement tables per data-model.md (Run with status enum "created, running, paused, stopped, completed, budget_exhausted, failed"; PartProgress unique "(run_id, day, part)" with PartState enum; Attempt; CodeRevision; ExecutionResult; ExampleCase; ModelInvocation; Submission with "PENDING is written before the POST"; AccountState; Event) in backend/app/persistence/tables.py
- [X] T010 Implement repository helpers (create run, get/update part, append attempt, ledger queries, totals) in backend/app/persistence/repo.py
- [X] T011 Implement EventBus (persist event → fan-out to subscribers, typed event constructors per contracts/events.md) in backend/app/events/bus.py and backend/app/events/types.py
- [X] T012 Implement FastAPI app factory, lifespan (DB init, recovery hook), CORS restricted to dashboard origin, health/config routes in backend/app/main.py and backend/app/api/system.py
- [X] T013 [P] Unit tests for config validation, redaction and allowlist in backend/tests/unit/test_security.py
- [X] T014 [P] Create test fixtures: synthetic two-part puzzles (HTML pages, inputs, expected answers) and a fake Advent of Code site (respx router with stateful acceptance, cooldowns, wrong answers) in backend/tests/fixtures/

**Checkpoint**: Foundation ready

---

## Phase 3: User Story 1 - Autonomous live solving with real submission (Priority: P1) 🎯 MVP

**Goal**: Solve a part end-to-end: fetch, understand, generate, test in sandbox, repair, run on real input, submit, interpret, unlock Part 2, advance.

**Independent Test**: Scenario A/B/D/F against the fake site with scripted models and fake executor (tests/e2e), plus opt-in live test of one real part.

### Tests for User Story 1

- [X] T015 [P] [US1] Parser tests (title, articles, completed answers, pre blocks, emphasized codes, login detection, calendar stars, hidden form answer) in backend/tests/unit/test_aoc_parser.py
- [X] T016 [P] [US1] Response classification tests for every outcome incl. wait parsing in backend/tests/unit/test_aoc_responses.py
- [X] T017 [P] [US1] AocClient tests: pacing ≥ min interval, cache hits, no redirect following, Retry-After, POST never retried in backend/tests/integration/test_aoc_client.py
- [X] T018 [P] [US1] Harness tests (encode/decode protocol, truncation, missing marker) in backend/tests/unit/test_harness.py
- [X] T019 [P] [US1] Example verification tests (verbatim-in-pre check, expected-in-article check) in backend/tests/unit/test_examples.py
- [X] T020 [P] [US1] Answer ledger tests (duplicate rejection, too-high/too-low bounds, non-numeric answers) in backend/tests/unit/test_ledger.py
- [X] T021 [P] [US1] Model adapter request/response mapping tests (Responses + Messages, usage parsing, JSON schema output, Messages format fallback) in backend/tests/integration/test_model_adapters.py
- [X] T022 [P] [US1] Dynamic Sessions executor tests with mocked pool endpoint (success, exception, timeout, 429 retry, wrapped-body fallback) in backend/tests/integration/test_dynamic_sessions.py
- [X] T023 [US1] E2E progression test (Scenario A + F; also asserts SC-006: ≤ ~10 website requests per day, all spaced ≥ min interval) in backend/tests/e2e/test_progression.py
- [X] T024 [US1] E2E repair test (Scenario B) in backend/tests/e2e/test_repair.py
- [X] T025 [US1] E2E wrong-answer test (Scenario D) in backend/tests/e2e/test_wrong_answer.py

### Implementation for User Story 1

- [X] T026 [P] [US1] Implement HTML parsers (DayPage, PartArticle text rendering preserving pre/code, completed answers, calendar stars, login detection, form hidden answer) in backend/app/aoc/parser.py
- [X] T027 [P] [US1] Implement response classification per contracts/aoc-client.md in backend/app/aoc/responses.py
- [X] T028 [US1] Implement AocClient (single lock, min interval default 5 s floor 1 s, UA with contact, cache dir `<APS_DATA_DIR>/cache/<year>/<day>/`, backoff for GET, no POST retry, UNCERTAIN on post-send network error) in backend/app/aoc/client.py
- [X] T029 [P] [US1] Implement ModelProvider protocol, ModelRequest/Response, errors, Azure token provider (scope https://ai.azure.com/.default) in backend/app/models/base.py and backend/app/models/auth.py
- [X] T030 [P] [US1] Implement ResponsesAdapter (Foundry v1 /responses, reasoning.effort, text.format json_schema, usage incl. reasoning tokens, infra retry; reasoning items discarded, never persisted or displayed — FR-038) in backend/app/models/responses_adapter.py
- [X] T031 [P] [US1] Implement pricing/cost estimation from configured prices in backend/app/models/pricing.py
- [X] T032 [P] [US1] Implement harness generator/decoder per contracts/code-execution.md in backend/app/execution/harness.py
- [X] T033 [US1] Implement CodeExecutionService protocol and DynamicSessionsExecutor (api-version 2025-10-02-preview, fresh identifier per execution, scope https://dynamicsessions.io/.default) in backend/app/execution/base.py and backend/app/execution/dynamic_sessions.py
- [X] T034 [P] [US1] Implement example verification in backend/app/verification/examples.py
- [X] T035 [P] [US1] Implement answer ledger (account-wide rejected answers, bounds) in backend/app/verification/ledger.py
- [X] T036 [US1] Implement prompts (trusted system instructions, delimited untrusted puzzle, input shape preview, Part 1 context for Part 2, repair feedback) and SolutionProposal schema in backend/app/agents/prompts.py
- [X] T037 [US1] Implement Solver steps (analyze+generate, test, repair, execute input, hardcoded-answer guard per plan.md) emitting events and persisting attempts/revisions/results in backend/app/agents/solver.py
- [X] T038 [US1] Implement Orchestrator state machine per plan.md (part loop, submission handling, Part 2 unlock, advance, FAILED→BLOCKED next part, Day 25 rule) in backend/app/agents/orchestrator.py
- [X] T039 [US1] Implement RunManager (create/start runs, one live run at a time, asyncio task lifecycle) in backend/app/agents/run_manager.py
- [X] T040 [US1] Implement run endpoints (create with authorization validation, start, progress, part detail, revisions, submissions) in backend/app/api/runs.py
- [X] T041 [US1] Implement connection verification endpoint (session validity, model ping, sandbox probe) in backend/app/api/system.py

**Checkpoint**: MVP — a part can be solved and submitted end-to-end against the fake site

---

## Phase 4: User Story 2 - Live conference dashboard and presentation mode (Priority: P1)

**Goal**: Real-time dashboard, calendar, activity feed, code inspector, metrics, presentation view.

**Independent Test**: Scenario K — SSE stream test + frontend component tests with recorded events.

### Tests for User Story 2

- [X] T042 [P] [US2] SSE stream tests (ordering, Last-Event-ID resume, no duplicates, keep-alive, publish→receive latency < 2 s per SC-004) in backend/tests/integration/test_sse.py
- [X] T043 [P] [US2] Frontend tests: calendar state derivation (star only when verified), activity feed rendering, escalation banner in frontend/tests/

### Implementation for User Story 2

- [X] T044 [US2] Implement SSE endpoint and event history endpoint in backend/app/api/events.py
- [X] T045 [US2] Implement metrics endpoint (per model/part tokens, calls, latency, cost, escalations) in backend/app/api/metrics.py
- [X] T046 [P] [US2] Implement typed API client, types and SSE hook with reconnect/resume in frontend/src/api/ and frontend/src/hooks/useRunStream.ts
- [X] T047 [P] [US2] Implement UI primitives (button, card, badge, switch, dialog, tabs) on Radix + Tailwind dark theme in frontend/src/components/ui/
- [X] T048 [US2] Implement Calendar (25 days × 2 parts, all states, star animation on star.earned) in frontend/src/components/Calendar.tsx
- [X] T049 [P] [US2] Implement ActivityFeed in frontend/src/components/ActivityFeed.tsx
- [X] T050 [P] [US2] Implement CodeInspector (syntax highlighting, revision history, execution results) in frontend/src/components/CodeInspector.tsx
- [X] T051 [P] [US2] Implement StatusHeader + Metrics panels in frontend/src/components/StatusHeader.tsx and frontend/src/components/MetricsPanel.tsx
- [X] T052 [US2] Implement Dashboard page in frontend/src/pages/Dashboard.tsx
- [X] T053 [US2] Implement Presentation page (large calendar, star count, current activity, model, compact code/exec, fullscreen toggle, demo clock; body text ≥ 24 px, star count ≥ 96 px per SC-010) in frontend/src/pages/Presentation.tsx

**Checkpoint**: Dashboard shows a run live

---

## Phase 5: User Story 3 - Escalation to a stronger model (Priority: P2)

**Goal**: Route to escalation model after repeated failures/timeouts with a concise handover.

**Independent Test**: Scenario C with a scripted failing workhorse.

- [X] T054 [P] [US3] E2E escalation test (Scenario C) in backend/tests/e2e/test_escalation.py
- [X] T055 [P] [US3] Escalation policy unit tests (thresholds, timeout early escalation, effort ladder) in backend/tests/unit/test_policy.py
- [X] T056 [P] [US3] Implement MessagesAdapter (Claude Messages API on Foundry, anthropic-version, adaptive thinking, output_config.effort/format with fallback, refusal handling; thinking blocks discarded, never persisted or displayed — FR-038) in backend/app/models/messages_adapter.py
- [X] T057 [US3] Implement ModelRouter + escalation policy and handover summary builder in backend/app/models/router.py and backend/app/agents/policy.py
- [X] T058 [US3] Implement EscalationBanner (primary → escalation with reason) in frontend/src/components/EscalationBanner.tsx

---

## Phase 6: User Story 4 - Safe control, persistence and recovery (Priority: P2)

**Goal**: Pause/resume/stop/retry, cooldowns, restart recovery, uncertain-submission reconciliation, budgets.

**Independent Test**: Scenarios E, G, H, J.

- [X] T059 [P] [US4] E2E cooldown test (Scenario E) in backend/tests/e2e/test_cooldown.py
- [X] T060 [P] [US4] E2E uncertain submission test (Scenario G) in backend/tests/e2e/test_uncertain_submission.py
- [X] T061 [P] [US4] E2E restart test (Scenario H) in backend/tests/e2e/test_restart.py
- [X] T062 [P] [US4] Model infra failure test (Scenario J: 429/5xx not counted as attempts; budget exhaustion stops run) in backend/tests/e2e/test_infra_failures.py
- [X] T063 [US4] Implement control endpoints (pause/resume/stop/retry/approve, delete run, reset local data with notice) in backend/app/api/runs.py
- [X] T064 [US4] Implement startup recovery (running→paused, PENDING→UNCERTAIN) and reconciliation in backend/app/agents/recovery.py
- [X] T065 [US4] Implement budget enforcement and budget.warning in backend/app/agents/orchestrator.py
- [X] T066 [US4] Implement RunControls + StartRunDialog (explicit authorization checkbox, manual-approval explanation, limits) + Runs page in frontend/src/components/RunControls.tsx, frontend/src/components/StartRunDialog.tsx, frontend/src/pages/Runs.tsx

---

## Phase 7: User Story 5 - Labelled replay of a recorded run (Priority: P3)

- [X] T067 [P] [US5] E2E replay test (Scenario L: no external calls, replay flags) in backend/tests/e2e/test_replay.py
- [X] T068 [US5] Implement replay service (copy events with time compression into a replay run) in backend/app/replay.py and endpoint in backend/app/api/runs.py
- [X] T069 [US5] Implement REPLAY labelling in all views (persistent banner, watermark) in frontend/src/components/ReplayBanner.tsx

---

## Phase 8: User Story 6 - Preflight and connection verification (Priority: P3)

- [X] T070 [P] [US6] Preflight tests (invalid session fails that check only; no POST made) in backend/tests/integration/test_preflight.py
- [X] T071 [US6] Implement preflight CLI (session, both models, sandbox exec + egress probe, storage, unsolved parts, git checkpoints, optional safe input preload) in backend/cli.py
- [X] T072 [P] [US6] Opt-in live Azure tests (synthetic puzzle solved with real models in the real sandbox; forced escalation call) in backend/tests/live/test_live_azure.py

---

## Phase 9: User Story 7 - Checkpoint walkthrough alongside the live solver (Priority: P3)

- [X] T073 [P] [US7] Implement scripts/setup-demo.ps1 (+ .sh): create aps-live and aps-walkthrough worktrees and aps-data dir, install deps
- [X] T074 [P] [US7] Implement scripts/start-live-app.ps1 (+ .sh): start backend 8765 + frontend 5175 from aps-live with APS_DATA_DIR
- [X] T075 [P] [US7] Implement scripts/show-checkpoint.ps1 and scripts/return-to-complete.ps1 (+ .sh): switch walkthrough worktree, refuse on uncommitted changes unless confirmed, set .specify/feature.json
- [X] T076 [P] [US7] Implement scripts/preflight.ps1 (+ .sh) wrapping the CLI and git/worktree checks
- [ ] T077 [US7] Install GitHub Copilot Spec Kit integration without changing the default integration and document it in demo/PRESENTER_GUIDE.md

---

## Phase 10: Polish & Cross-Cutting Concerns

- [X] T078 [P] Infrastructure: infra/main.bicep, infra/modules/*.bicep, infra/main.parameters.json, azure.yaml
- [ ] T079 [P] Presenter docs: demo/PRESENTER_GUIDE.md, CHECKPOINTS.md, DEMO_SCRIPT_25_MIN.md, PREFLIGHT_CHECKLIST.md, TROUBLESHOOTING.md, REPLAY_GUIDE.md
- [ ] T080 [P] ADRs for key decisions in docs/adr/
- [ ] T081 [P] Secret-leak scan test across logs/events/API payloads (SC-009) in backend/tests/integration/test_no_secret_leaks.py
- [ ] T082 Traceability matrix FR → code → tests in specs/001-agentic-aoc-solver/traceability.md
- [ ] T083 Run full test suites, ruff, frontend build/lint; record results

---

## Dependencies & Execution Order

- Setup (Phase 1) → Foundational (Phase 2) → US1 (MVP) → US2 → US3, US4 (parallelisable) → US5, US6, US7 → Polish.
- US2 depends on the event bus (Phase 2) and run endpoints (US1). US3 extends the solver from US1.
  US4 extends the orchestrator. US5 depends on persisted events. US6 depends on adapters and
  executor. US7 is independent of application code.

## Parallel Example: User Story 1

```text
T015–T022 (tests, different files) in parallel
T026, T027, T029, T030, T031, T032, T034, T035 in parallel (different modules)
then T028 → T033 → T036 → T037 → T038 → T039 → T040/T041
```

## Implementation Strategy

1. MVP = Phases 1–3: one part solved and submitted against the fake site, verified by e2e tests.
2. Add the dashboard (US2) — the demo becomes watchable.
3. Add escalation and recovery (US3, US4) — the demo becomes robust.
4. Replay, preflight, worktree tooling, docs (US5–US7, Polish) — the talk becomes reproducible.
