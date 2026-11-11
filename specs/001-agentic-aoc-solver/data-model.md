# Data Model: Agentic Advent of Code Solver

All tables live in one SQLite database at `<APS_DATA_DIR>/solver.db`. Timestamps are UTC ISO-8601.
Private content (puzzle text, inputs) is **not** stored in the database; it lives in the cache
directory `<APS_DATA_DIR>/cache/<year>/<day>/` (`page.html`, `input.txt`, `meta.json`).

## Run

| Field | Type | Notes |
|-------|------|-------|
| id | int PK | |
| mode | enum `live` \| `replay` | replay runs never contact external services (FR-039) |
| source_run_id | int? FK Run | for replays |
| year | int | 2015–2100, validated |
| day_from, day_to | int | 1 ≤ from ≤ to ≤ 25 |
| status | enum | `created`, `running`, `paused`, `stopped`, `completed`, `budget_exhausted`, `failed` |
| stop_reason | text? | human readable |
| auto_submit | bool | run-level authorization (FR-002); false = manual approval mode |
| config | JSON | `RunConfig` snapshot (limits, models, efforts, pacing, prices) |
| current_day, current_part | int? | |
| created_at, started_at, finished_at | datetime | |
| elapsed_seconds | float | accumulated running time (excludes paused) |
| total_cost_usd, total_input_tokens, total_output_tokens, total_reasoning_tokens | numeric/int | denormalised totals |

Transitions: `created → running ↔ paused → stopped|completed|budget_exhausted|failed`;
on process start any `running` → `paused` (interrupted).

## PartProgress

Unique `(run_id, day, part)`.

| Field | Type | Notes |
|-------|------|-------|
| id | int PK | |
| run_id | FK Run | |
| day, part | int | part ∈ {1,2} |
| title | text? | day title (public metadata) |
| state | enum `PartState` | NOT_STARTED, FETCHING, ANALYZING, GENERATING, TESTING, REPAIRING, ESCALATING, EXECUTING_INPUT, READY_TO_SUBMIT, SUBMITTING, WAITING_FOR_COOLDOWN, VERIFIED, BLOCKED, FAILED, SKIPPED |
| previously_completed | bool | completed on the account before this run (FR-033) |
| tests_passed | bool | success level 1 |
| candidate_answer | text? | success level 2 |
| accepted_answer | text? | success level 3 (only from CORRECT / reconciliation) |
| attempts_used | int | |
| submissions_used | int | distinct submissions |
| current_model | text? | logical model key `workhorse` / `escalation` |
| escalated | bool | |
| status_reason | text? | e.g. "Part 1 failed", "infra_error", "needs 49 stars" |
| understanding | JSON? | latest summary/algorithm (displayable) |
| updated_at | datetime | |

Calendar UI state derivation: VERIFIED+previously_completed → "previously completed";
VERIFIED → "verified"; SUBMITTING/WAITING_FOR_COOLDOWN or candidate submitted not yet accepted →
"submitted"; tests_passed & not verified → "tests passed"; active states → "solving"; FAILED,
BLOCKED, SKIPPED as named; else "unsolved".

## Attempt

| Field | Type | Notes |
|-------|------|-------|
| id | int PK | |
| part_id | FK PartProgress | |
| number | int | 1-based per part |
| kind | enum `initial` \| `repair` \| `escalation` \| `post_rejection` | |
| model_key | text | `workhorse` / `escalation` |
| effort | text | reasoning effort requested |
| summary, algorithm, diagnosis | text? | model-visible explanation (no chain-of-thought) |
| outcome | enum | `pending`, `tests_failed`, `tests_passed`, `exec_failed`, `candidate`, `rejected_duplicate`, `infra_error` |
| started_at, finished_at | datetime | |

## CodeRevision

| Field | Type | Notes |
|-------|------|-------|
| id | int PK | |
| attempt_id | FK Attempt | one per attempt |
| part_id | FK PartProgress | |
| revision | int | sequential per part |
| code | text | generated Python (untrusted; display only) |
| sha256 | text | dedupe identical code |
| created_at | datetime | |

## ExecutionResult (covers example tests and real input)

| Field | Type | Notes |
|-------|------|-------|
| id | int PK | |
| revision_id | FK CodeRevision | |
| kind | enum `examples` \| `input` \| `probe` | |
| status | enum `ok`, `error`, `timeout`, `infra_error` | |
| cases | JSON | per case: `{index, expected, actual, passed, error, duration_ms, reliable}` (no input text) |
| answer | text? | for `input` |
| stdout, stderr | text | truncated (8 KiB stored) |
| duration_ms | int | |
| timed_out | bool | |
| correlation_id | text | session identifier |
| created_at | datetime | |

## ExampleCase (per part, from extraction)

| Field | Type | Notes |
|-------|------|-------|
| id | int PK | |
| part_id | FK | |
| index | int | |
| input_ref | text | hash of verbatim input; text kept in cache dir `examples.json` |
| expected | text? | null when unreliable |
| reliable | bool | expected verified to appear in article |
| note | text? | e.g. "uses smaller grid" |

## ModelInvocation

| Field | Type | Notes |
|-------|------|-------|
| id | int PK | |
| run_id, part_id, attempt_id | FK | |
| model_key | text | |
| deployment | text | |
| provider | enum `responses` \| `messages` | |
| purpose | enum `analyze_generate`, `repair`, `escalate`, `diagnose_rejection`, `preflight` | |
| effort | text | |
| input_tokens, output_tokens, reasoning_tokens | int | reasoning null when unreported |
| latency_ms | int | |
| cost_usd | numeric | from configured prices |
| status | enum `ok`, `infra_error`, `refusal`, `invalid_output` | |
| error | text? | redacted |
| created_at | datetime | |

## Submission

| Field | Type | Notes |
|-------|------|-------|
| id | int PK | |
| run_id, part_id | FK | |
| year, day, part | int | |
| answer | text | normalised (stripped) |
| outcome | enum `PENDING`, `UNCERTAIN`, `CORRECT`, `INCORRECT`, `TOO_HIGH`, `TOO_LOW`, `COOLDOWN`, `ALREADY_COMPLETED`, `LOCKED`, `AUTH_FAILED`, `UNEXPECTED` | |
| message | text? | normalised response text (public, no secrets) |
| wait_seconds | int? | |
| submitted_at, responded_at | datetime | |

Invariants: PENDING is written **before** the POST; at most one PENDING/UNCERTAIN per part; an
answer with outcome INCORRECT/TOO_HIGH/TOO_LOW for `(year, day, part)` is never posted again
(ledger is account-wide across runs).

## AccountState (singleton per year)

| Field | Type | Notes |
|-------|------|-------|
| year | int PK | |
| cooldown_until | datetime? | next eligible submission (FR-020) |
| stars | JSON | day → 0/1/2 from last calendar read |
| last_calendar_fetch | datetime? | |

## Event

| Field | Type | Notes |
|-------|------|-------|
| id | int PK autoincrement | global sequence; SSE `id` (FR-031) |
| run_id | FK Run | |
| type | text | see `contracts/events.md` |
| day, part | int? | |
| level | enum `info`, `success`, `warning`, `error` | |
| message | text | human readable, from real action |
| data | JSON | typed payload, never secrets or input text |
| replay | bool | true for replayed events |
| created_at | datetime | |

## Relationships

Run 1─* PartProgress 1─* Attempt 1─1 CodeRevision 1─* ExecutionResult; PartProgress 1─* Submission;
Run 1─* Event; Attempt 1─* ModelInvocation.
