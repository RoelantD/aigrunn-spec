# Implementation Plan: Agentic Advent of Code Solver

**Branch**: `001-agentic-aoc-solver` (spec directory; work happens on `main`) | **Date**: 2026-11-11 |
**Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-agentic-aoc-solver/spec.md`

## Summary

A locally run web application (FastAPI backend + React dashboard) drives a custom, persisted agent
state machine that solves Advent of Code 2024 parts in order. Puzzle access, model inference,
sandboxed execution, answer verification, persistence and event delivery are separate modules.
The workhorse model (GPT-6.1 Sol, Foundry Responses API) analyses puzzles and writes a
`solve(input_text) -> str` Python program; the program is tested against verbatim-checked
examples and run on the real input inside Azure Container Apps Dynamic Sessions (egress disabled).
Repeated failures escalate to Claude Opus 5.5 (Claude Messages API in Foundry) with a concise
handover. Answers are submitted to the real website with run-level authorization, responses are
classified, cooldowns persisted, uncertain submissions reconciled, and Part 2 fetched only after
Part 1 acceptance. Every action becomes a persisted event streamed over SSE to the dashboard and a
fullscreen presentation view. Recorded runs replay without any external calls, labelled REPLAY.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5 / Node 22 (frontend)

**Primary Dependencies**: FastAPI, Pydantic v2, pydantic-settings, SQLAlchemy 2 (async) +
aiosqlite, httpx, azure-identity, BeautifulSoup4, structlog, sse-starlette; React, Vite,
Tailwind CSS, Radix UI, lucide-react, prism-react-renderer

**Storage**: SQLite file in a runtime data directory outside the source tree
(`APS_DATA_DIR`, default `../aps-data` relative to the repo), plus a puzzle cache directory
(`<data>/cache/<year>/<day>/`) for pages and inputs

**Testing**: pytest + pytest-asyncio + respx (backend unit/integration/e2e with synthetic puzzles
and a fake AoC site), Vitest + Testing Library (frontend). Real-cloud tests are opt-in
(`pytest -m live_azure`, `-m live_aoc`) and never submit answers.

**Target Platform**: Windows 11 presenter laptop (also Linux/macOS); backend binds to 127.0.0.1;
Azure for models and sandbox

**Project Type**: Web application (backend + frontend) with infrastructure-as-code and demo scripts

**Performance Goals**: Dashboard event latency < 2 s (SC-004); no artificial delays in local
steps; AoC requests ≥ 5 s apart (configurable, floor 1 s)

**Constraints**: Sandbox per-execution timeout default 30 s, max 220 s; ≤ 3 distinct submissions
per part; ≤ 6 attempts per part; configurable spend cap; secrets never leave the backend

**Scale/Scope**: Single operator, one active live run at a time, 25 days × 2 parts, tens of
thousands of events per run at most

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Pre-research | Post-design |
|-----------|------|--------------|-------------|
| I Authentic Verification | Three success levels modelled separately; star only on CORRECT/reconciled; replay flagged; no hardcoded answers (prompt rule + static check for answer literals) | PASS | PASS — `PartState`, `Submission.outcome`, `Run.mode=replay`, see data-model |
| II Isolation | Generated code only via `CodeExecutionService` → Dynamic Sessions (EgressDisabled); no host executor; secrets only in `Settings` (SecretStr) and HTTP clients; prompts delimit untrusted content | PASS | PASS — no local executor exists outside tests' fake; redaction processor + tests |
| III Respectful Automation | Sequential paced AoC client, cache, UA with contact, Retry-After, no POST auto-retry, rejected-answer ledger | PASS | PASS — `aoc/client.py` single gate; contract in `contracts/aoc-client.md` |
| IV Observability | Every step emits persisted events; usage metrics; no chain-of-thought requested/displayed | PASS | PASS — `contracts/events.md` |
| V Bounded Autonomy | Limits in `RunConfig`; infra retries separate from attempts; restart reconciliation of PENDING submissions | PASS | PASS — state machine + recovery section |
| VI Test-Backed | Synthetic puzzles, fake AoC site, scripted fake models, fake executor (tests only); live tests opt-in | PASS | PASS — quickstart scenarios A–L map to tests |
| VII Simplicity | One process, module boundaries as listed, custom loop, two provider adapters behind one interface | PASS | PASS — see Complexity Tracking (empty) |

No violations; Complexity Tracking is empty.

## Architecture

```text
            ┌──────────────────────────── FastAPI process (127.0.0.1:8765) ───────────────────────────┐
 Browser ── │ api/ (REST + SSE) ── RunManager ── Orchestrator (per run, asyncio task)                 │
 (React)    │                                     │   ├─ agents/solver.py   (understand/generate/repair)│
            │                                     │   ├─ models/  ModelRouter → ResponsesAdapter (Sol) │──► Foundry
            │                                     │   │                       → MessagesAdapter (Opus)│
            │                                     │   ├─ execution/ CodeExecutionService → DynamicSessions ──► ACA pool
            │                                     │   ├─ verification/ examples, answer ledger, bounds│
            │                                     │   └─ aoc/ AocClient (paced, cached) + parsers     │──► adventofcode.com
            │ events/ EventBus (persist → fan-out) ◄──── all modules emit events                      │
            │ persistence/ SQLAlchemy async (SQLite in APS_DATA_DIR)                                   │
            └──────────────────────────────────────────────────────────────────────────────────────────┘
```

### Solving state machine (per part)

```text
NOT_STARTED → FETCHING → ANALYZING → GENERATING → TESTING ─pass→ EXECUTING_INPUT → READY_TO_SUBMIT
                               ▲            │fail                                     │
                               │            ▼                                         ▼
                          ESCALATING ◄─ REPAIRING (attempt < max)              SUBMITTING
                                                                                │  │  │
            VERIFIED ◄──────────── CORRECT / ALREADY_COMPLETED / reconciled ────┘  │  └─ COOLDOWN → WAITING_FOR_COOLDOWN → SUBMITTING
                                                                                   └─ INCORRECT/TOO_HIGH/TOO_LOW → REPAIRING (diagnose)
 attempts or submissions exhausted → FAILED      dependency/session problem → BLOCKED      Day25 P2 w/o 49★ → SKIPPED
```

- Attempt = one generated program revision that is tested. Repairs consume attempts.
- Model selection per attempt: attempts 1–3 → workhorse (effort medium, medium, high);
  attempt ≥ `escalate_after_failures + 1` (default 4) → escalation model (effort high). Early
  escalation when the last failure was a timeout and `escalate_on_timeout` is true (from attempt 2).
- Infra errors (HTTP 429/5xx/network to Foundry or Dynamic Sessions) are retried by the adapter with
  exponential backoff honoring `Retry-After` (max 5 tries) and do **not** consume attempts; if the
  retries are exhausted the part is BLOCKED with `infra_error` and the run pauses (not fails).
- Wrong answer: the rejected answer and its bound (too high/low) go into the answer ledger; the next
  attempt receives the feedback; any candidate equal to a rejected answer or outside known bounds
  is not submitted (counts as a failed attempt with feedback "answer previously rejected").
- Cooldown: account-wide `cooldown_until` persisted; the orchestrator sleeps until then (interruptible
  by pause/stop) before submitting.
- Pause/stop are cooperative: checked between steps; an in-flight model call or execution completes
  and is recorded first.

### Recovery

- On startup, runs left `running` become `paused` (event `run.interrupted`).
- Submissions with `outcome = PENDING` (request sent, no classified response persisted) are marked
  `UNCERTAIN`; on resume the orchestrator re-fetches the day page and treats the part as VERIFIED if
  "Your puzzle answer was" is present for that part, otherwise allows the next (different or same)
  submission only after reconciliation proves it was not accepted. Reconciliation never POSTs.
- Parts resume from their last durable state: VERIFIED stays VERIFIED; in-progress states restart
  at GENERATING with existing attempts counted.

### Model prompts (observable, no chain-of-thought)

- System instructions (trusted) are separate from a `<puzzle_description>` block that is declared
  untrusted data. The full personal input is never sent to models: only a short shape preview
  (first 5 lines, each truncated to 120 chars) plus statistics (line count, max width, character
  set) so the model can match the real format — minimises private data in prompts.
- Structured output schema `SolutionProposal`: `summary`, `algorithm`, `complexity`,
  `examples[] {input, expected_output|null, note}`, `code`. Repairs add a `diagnosis` field. The
  `summary`, `algorithm`, `diagnosis` are short user-facing explanations displayed on the dashboard.
- Handover to escalation model: requirements summary, Part 1 summary/code (for Part 2), list of
  prior approaches with their failure, current code, latest failing tests/timeouts, submission
  feedback.

### Security controls

- `Settings` holds secrets as `SecretStr`; structlog processor redacts known secret values and
  cookie/authorization headers; events built from typed payloads that never include input text.
- AoC client: base URL fixed to `https://adventofcode.com`, paths built from validated ints,
  `follow_redirects=False`, any redirect to a non-allowlisted host is an error. Model/sandbox
  endpoints must be `https://` and match allowlisted suffixes (`.openai.azure.com`,
  `.services.ai.azure.com`, `.cognitiveservices.azure.com`, `.dynamicsessions.io`).
- Backend binds 127.0.0.1; CORS limited to the dashboard origin.
- Sandbox receives only the program, the input/example text, and the harness.

## Project Structure

### Documentation (this feature)

```text
specs/001-agentic-aoc-solver/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── rest-api.md      # Backend REST + SSE contract
│   ├── events.md        # Event types and payloads
│   ├── aoc-client.md    # Website access contract and response classification
│   ├── model-provider.md# ModelProvider interface + structured output schema
│   └── code-execution.md# CodeExecutionService + harness protocol
├── checklists/
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml
├── app/
│   ├── main.py              # FastAPI app factory, lifespan (recovery), CORS
│   ├── config.py            # Settings (pydantic-settings), RunConfig defaults, pricing
│   ├── logging.py           # structlog + redaction
│   ├── security.py          # URL allowlist, redaction helpers
│   ├── api/                 # routers: runs, control, progress, code, metrics, events(SSE), health
│   ├── aoc/                 # client.py (paced/cached), parser.py, responses.py (classification)
│   ├── agents/              # orchestrator.py (state machine), solver.py, prompts.py, policy.py
│   ├── models/              # base.py, responses_adapter.py, messages_adapter.py, router.py, pricing.py, auth.py
│   ├── execution/           # base.py, harness.py, dynamic_sessions.py
│   ├── verification/        # examples.py, ledger.py (rejected answers/bounds)
│   ├── persistence/         # db.py, tables.py, repo.py
│   ├── events/              # bus.py, types.py
│   └── replay.py            # replay of recorded runs
├── cli.py                   # preflight, check connections, export recording
└── tests/
    ├── unit/  integration/  e2e/  live/   fixtures/ (synthetic puzzles, fake AoC site)
frontend/
├── package.json, vite.config.ts, tailwind config
├── src/
│   ├── api/ (client.ts, types.ts, sse.ts)  hooks/ (useRunStream.ts)
│   ├── components/ (Calendar, ActivityFeed, CodeInspector, EscalationBanner, Metrics, RunControls, StartRunDialog, ui/)
│   └── pages/ (Dashboard.tsx, Presentation.tsx, Runs.tsx)
└── tests/
infra/      main.bicep, modules/ (foundry.bicep, sessionpool.bicep, roles.bicep), main.parameters.json
azure.yaml
scripts/    setup-demo.ps1, start-live-app.ps1, show-checkpoint.ps1, return-to-complete.ps1, preflight.ps1 (+ .sh)
demo/       PRESENTER_GUIDE.md, CHECKPOINTS.md, DEMO_SCRIPT_25_MIN.md, PREFLIGHT_CHECKLIST.md, TROUBLESHOOTING.md, REPLAY_GUIDE.md
docs/adr/   architecture decision records
```

**Structure Decision**: Web application layout (`backend/` + `frontend/`) with the module split
mandated by Constitution VII; infra and demo tooling at the root.

### Runtime layout for the presentation

```text
<parent>/agentic-puzzle-solver   # development clone (main)
<parent>/aps-live                # worktree A: detached at demo/07-complete; runs backend:8765 + frontend:5175
<parent>/aps-walkthrough         # worktree B: switched between demo/00..07 tags
<parent>/aps-data                # APS_DATA_DIR: SQLite, cache, recordings (never inside a worktree)
```

## Complexity Tracking

No constitution violations to justify.
