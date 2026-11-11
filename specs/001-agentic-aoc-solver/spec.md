# Feature Specification: Agentic Advent of Code Solver

**Feature Branch**: `001-agentic-aoc-solver` (specification directory; development continues on `main`)

**Created**: 2026-11-11

**Status**: Draft

**Input**: User description: "Build an Agentic Advent of Code Solver: given a calendar URL such as
https://adventofcode.com/2024, the application autonomously solves the selected days in order using
cloud-hosted AI models — it reads each puzzle, writes a program, tests it on the puzzle's examples in
a secure sandbox, repairs failures, escalates hard problems to a stronger model, runs the program on
the user's real input, submits the answer to the real Advent of Code website with run-level
authorization, interprets the response, unlocks Part 2, and advances until the range is complete or
a limit is reached. A conference-ready live dashboard shows real progress, generated code, model
escalations, submissions, stars and costs. Progress persists and resumes safely. Recorded runs can
be replayed (clearly labelled). The presenter must be able to show historical development
checkpoints without interrupting the running solver. It is for historical puzzles and education
only, and must treat Advent of Code respectfully."

## Clarifications

### Session 2026-11-11

> Provenance: `/speckit-clarify` was run by the implementing agent (Claude Code). The operator
> instructed the agent not to re-ask decisions already made in the feature brief and to make
> remaining reasonable decisions independently. No stakeholder conversation took place. Each answer
> below is the agent's recommended option, chosen on the basis noted in brackets.

- Q: What minimum interval should separate consecutive automated requests to the Advent of Code
  website? → A: 5 seconds by default (configurable, lower bound 1 s), strictly sequential; a
  `Retry-After` or cooldown always takes precedence. [Agent decision: the website publishes no
  interval for puzzle/input/answer requests; the 15-minute guidance applies only to private
  leaderboard JSON; 5 s keeps a full day at ~10 requests well under a minute of overhead.]
- Q: When a part exhausts its attempts or is otherwise unsolvable, should the run stop or move on?
  → A: Mark the part FAILED, mark that day's dependent Part 2 BLOCKED, and continue with the next
  day. [Agent decision: historical days are independent, so stopping would waste the demo.]
- Q: How many real answer submissions may the agent make for a single part? → A: At most 3 distinct
  submissions per part by default (configurable); after the limit the part becomes FAILED and
  needs an operator retry. [Agent decision: prevents using the website as a guessing oracle while
  allowing recovery from a genuine misreading.]
- Q: While a submission cooldown is active, should the agent start work on other parts? → A: No. It
  continues diagnosis of the same part only (local work is allowed), then waits for the deadline
  before submitting; it does not jump ahead. [Agent decision: keeps progress strictly chronological
  and the dashboard easy to follow.]
- Q: How should Day 25's second star be handled? → A: After Day 25 Part 1 is accepted, the agent
  claims the second star automatically only if the account then holds all 49 other stars;
  otherwise Part 2 is marked SKIPPED with the reason. [Agent decision: mirrors the website's rule
  and avoids a pointless submission.]

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Autonomous live solving with real submission (Priority: P1)

The operator (the conference presenter) configures their Advent of Code account session, chooses a
calendar year (2024) and a day range containing unsolved puzzles, explicitly authorizes automatic
answer submission for the run, and starts it. For each part in order, the agent fetches the puzzle
and the personal input, interprets the problem, writes a program, tests it against the worked
examples in an isolated sandbox, repairs it when tests fail, runs it on the real input, submits the
answer, and interprets the website's reply. An accepted Part 1 unlocks Part 2, which the agent
fetches and solves using what it learned in Part 1. An accepted Part 2 moves the agent to the next
day. The run continues without further operator interaction.

**Why this priority**: This is the product. Without genuine solving and genuine submission the
demonstration has no substance, and Part 2 is unreachable without an accepted Part 1.

**Independent Test**: Against a mocked puzzle website serving a synthetic two-part puzzle, start a
run with submission authorized and observe: example tests executed in the sandbox, an answer
submitted, an "accepted" reply parsed, Part 2 fetched and solved, and the run advancing to the next
day. Separately, against the real website with a valid session, solve one previously unsolved part
and observe the server-confirmed star.

**Acceptance Scenarios**:

1. **Given** a valid account session and an unsolved Day N, **When** the operator starts a run with
   automatic submission authorized, **Then** the agent fetches Part 1 and the input, generates and
   tests a program, submits the computed answer, and on acceptance marks Part 1 as verified.
2. **Given** Part 1 was just accepted, **When** the agent continues, **Then** it retrieves the newly
   unlocked Part 2 description, solves and submits it, and on acceptance advances to Day N+1.
3. **Given** a generated program fails an example test, **When** the failure is observed, **Then**
   the agent records the expected and actual output (or error) and produces a revised program that
   is tested again, up to the configured attempt limit.
4. **Given** the website rejects a submitted answer (including "too high"/"too low" hints),
   **When** the agent retries, **Then** it records the rejection, never submits the identical answer
   again, and uses the hint to revise the solution before any new submission.
5. **Given** the account has already completed Part 1 of a day, **When** the run reaches that day,
   **Then** Part 1 is marked "previously completed" (distinct from newly solved) and the agent
   proceeds directly to Part 2.
6. **Given** automatic submission is disabled for a run, **When** the operator starts it, **Then**
   the system explains that progression to locked Part 2 puzzles will stop, and candidate answers
   wait for manual approval.

---

### User Story 2 - Live conference dashboard and presentation mode (Priority: P1)

While the run proceeds, the presenter and audience watch a dashboard on a large screen: a 25-day
calendar with independent Part 1 and Part 2 status, a count of verified stars, the current day and
part, the model currently working, a live activity feed of real events, the current generated
program with its revision history, execution results, attempts, elapsed time and estimated cost. A
dedicated presentation view shows the essentials in large type with minimal configuration clutter.

**Why this priority**: The audience experiences the agent through the dashboard; it must be
accurate, legible from the back of a room, and visually rewarding when a star is earned.

**Independent Test**: Feed a recorded or mocked run's events to the dashboard and verify every
calendar state, the activity feed, code inspector and metrics update without a page refresh, and that
a star appears only after an "accepted" event.

**Acceptance Scenarios**:

1. **Given** a run in progress, **When** the agent emits events, **Then** the dashboard shows them
   within a few seconds without page refresh and in the order they occurred.
2. **Given** the browser connection drops and reconnects, **When** the dashboard reconnects, **Then**
   the full event timeline is restored without gaps or duplicates.
3. **Given** a part has passed tests and a candidate was submitted but not yet accepted, **When**
   viewing the calendar, **Then** it shows a distinct "submitted" state and no star.
4. **Given** the operator opens the presentation view, **When** viewed fullscreen, **Then** the
   calendar, star count, current activity, current model and a compact code/execution window are
   visible without scrolling.

---

### User Story 3 - Escalation to a stronger model (Priority: P2)

Most parts are attempted by a fast, economical primary model. When repeated attempts fail (or the
failure signals algorithmic complexity such as timeouts), the agent escalates to a stronger model and
asks it to reassess the approach, handing over a concise summary of requirements, prior approaches,
the current program, failures and any submission feedback. The escalation is obvious on the dashboard
with a short reason.

**Why this priority**: It demonstrates cost-aware multi-model routing and materially improves solve
rates on harder days, but basic solving works without it.

**Independent Test**: With a scripted primary model that always produces a failing program, verify
that after the configured number of failures the stronger model is invoked with the handover
context, that its program is tested normally, and that an escalation event with a reason is shown.

**Acceptance Scenarios**:

1. **Given** the primary model has failed the configured number of attempts on a part, **When** the
   agent decides the next attempt, **Then** it uses the escalation model and records an escalation
   event with the reason.
2. **Given** an attempt timed out in the sandbox, **When** escalation policy allows early escalation
   for complexity failures, **Then** the agent may escalate before the normal threshold.
3. **Given** the total attempt limit for a part is reached, **When** no attempt succeeded, **Then**
   the part becomes FAILED, the same day's Part 2 (if not yet accessible) becomes BLOCKED, and the
   run continues with the next day.

---

### User Story 4 - Safe control, persistence and recovery (Priority: P2)

The operator can pause, resume and stop a run, retry a blocked part, and view previous runs. All
progress is persisted. If the application restarts, it resumes at a safe point without losing
confirmed work. Website cooldowns after a submission are recorded and honored: the agent waits until
the deadline before submitting again, but does not otherwise stall. If the outcome of a submission
is uncertain (for example the connection dropped after sending), the agent checks the account's
completion state before considering any resubmission. Budgets (attempts, spend) stop the run cleanly
when exhausted.

**Why this priority**: The solver is left running unattended during a talk; it must be trustworthy
when interrupted, but the core value exists without polished recovery.

**Independent Test**: Kill the application mid-run (including between sending a submission and
receiving the reply), restart it, and verify it resumes, reconciles the uncertain submission against
account state, and never double-submits.

**Acceptance Scenarios**:

1. **Given** a submission returns a cooldown message, **When** the agent processes it, **Then** the
   next eligible time is persisted and no submission for any part occurs before it.
2. **Given** the network failed immediately after sending an answer, **When** the agent recovers,
   **Then** it re-reads the day's completion state before deciding to resubmit.
3. **Given** the application is restarted mid-run, **When** it starts, **Then** previously
   verified parts remain verified and the run can be resumed from the interrupted part.
4. **Given** the configured maximum spend for a run is reached, **When** the next model call would
   be made, **Then** the run stops with a clear "budget exhausted" status.
5. **Given** the model service returns a rate-limit or outage error, **When** the agent handles it,
   **Then** it retries the infrastructure call with backoff without counting it as a failed
   solving attempt.
6. **Given** the operator resets local run data, **When** the reset completes, **Then** the UI
   states that Advent of Code account progress is unaffected.

---

### User Story 5 - Labelled replay of a recorded run (Priority: P3)

If something interesting (an escalation, a rejected answer) did not occur during the live session,
the presenter can open a previously recorded genuine run and replay its event timeline in the
dashboard. Replay never contacts Advent of Code or the models and is labelled as a replay
everywhere it appears.

**Why this priority**: A safety net for the talk; it does not add solving capability.

**Independent Test**: Record a run, disconnect all external services, replay it, and verify the
dashboard reproduces the timeline with a persistent "REPLAY" label and zero outbound requests.

**Acceptance Scenarios**:

1. **Given** a completed recorded run, **When** the presenter starts a replay, **Then** events are
   shown in recorded order (optionally time-compressed) with a visible replay label.
2. **Given** a replay is running, **When** a live run is also running, **Then** the two are never
   visually confused.

---

### User Story 6 - Preflight and connection verification (Priority: P3)

Before the talk, the presenter runs a preflight that verifies the account session is valid, both
models respond, the sandbox can execute code and has no outbound network access, the selected day
range contains unsolved parts, storage is writable, and the development checkpoints exist. Preflight
never submits an answer and never consumes an unsolved puzzle. The presenter may preload public
metadata and inputs that are already legitimately accessible.

**Why this priority**: Reduces live-demo risk; the solver works without it.

**Independent Test**: Run preflight with a deliberately invalid session and verify it fails that
check with a clear message while reporting the others, and that no answer request was made.

**Acceptance Scenarios**:

1. **Given** all services are configured, **When** preflight runs, **Then** each check reports pass,
   fail or skipped with a reason, and the overall result is shown.
2. **Given** preflight runs, **When** it finishes, **Then** no answer has been submitted and no
   locked Part 2 was requested.

---

### User Story 7 - Development checkpoint walkthrough alongside the live solver (Priority: P3)

During the talk the presenter shows how the application was built by switching a separate working
copy between historical development checkpoints (constitution, specification, clarification, plan,
tasks, implementation, completed) and inspecting artifacts with an AI coding assistant, while the
finished application keeps running from its own working copy and storage.

**Why this priority**: Central to the talk's narrative about Spec-Driven Development, but
independent of the solver's functionality.

**Independent Test**: With the solver running, switch the walkthrough copy through every checkpoint
and back; verify the solver's event stream continues uninterrupted and its data is untouched.

**Acceptance Scenarios**:

1. **Given** the live solver is running, **When** the presenter switches the walkthrough copy to any
   checkpoint, **Then** the solver is unaffected.
2. **Given** the walkthrough copy has uncommitted changes, **When** the presenter switches
   checkpoints, **Then** they are warned and nothing is discarded without confirmation.

---

### Edge Cases

- Day 25 has a single puzzle; its second star is granted only when all other 49 stars are earned and
  is claimed rather than solved. The agent claims it only when the account holds the other 49
  stars; otherwise Day 25 Part 2 is SKIPPED with that reason.
- Puzzles whose examples have no reliably identifiable expected output: the agent proceeds with
  sanity checks only and records that example validation was unavailable.
- Multiple examples per part, examples with different parameters than the real input (e.g., grid
  size or step count), whitespace-sensitive or trailing-newline-sensitive input.
- Generated program loops forever, exhausts memory, prints excessively, or attempts network or file
  access: the sandbox contains it and the backend remains stable.
- The website returns an unexpected page, a login page (expired session), or a server error.
- A part becomes accessible unexpectedly (completed elsewhere during the run): the agent reconciles
  state and skips it.
- Repeated cooldowns: waiting time grows; the agent continues diagnosis of the same part only and
  then waits for the deadline; it never starts a later part while a cooldown is pending.
- The selected range starts at a day whose earlier days are incomplete (Advent of Code historical
  days are all open, so this is allowed).
- Budget is exhausted mid-attempt; a model call is in flight when the operator pauses.
- The answer is non-numeric (strings, coordinates, comma-separated values).

## Requirements *(mandatory)*

### Functional Requirements

**Run configuration and authorization**

- **FR-001**: Operators MUST be able to start a run from a calendar URL (e.g.
  `https://adventofcode.com/2024`) or a year, with a selectable day range (default 1–25).
- **FR-002**: Starting a live run MUST require explicit operator authorization for automatic answer
  submission, shown clearly at start; once granted it applies to the whole run without per-answer
  prompts.
- **FR-003**: The system MUST offer a manual-approval mode in which candidate answers wait for the
  operator, and MUST explain that disabling submission halts progression to locked Part 2 puzzles.
- **FR-004**: Operators MUST be able to configure limits: attempts per part (default 6), failures
  before escalation (default 3), distinct submissions per part (default 3), execution timeout
  (default 30 s, with a configurable maximum), maximum spend per run, and the website request
  pacing (default minimum interval 5 s, never below 1 s).
- **FR-005**: The system MUST validate the account session before a live run begins and refuse to
  start a live run with an invalid session.

**Puzzle acquisition**

- **FR-006**: The system MUST discover, for the selected year, each day's title, accessible parts,
  and parts already completed by the account.
- **FR-007**: The system MUST retrieve the puzzle description of each accessible part and the
  account's personal input, and cache both locally so they are not fetched again while unchanged.
- **FR-008**: The system MUST NOT request a Part 2 description before Part 1 is accepted for the
  account.
- **FR-009**: The system MUST extract worked examples and, where reliably identifiable, their
  expected outputs, preserving exact whitespace and formatting.
- **FR-010**: The system MUST retain useful Part 1 context (understanding, program, answer) when
  solving Part 2.

**Solving loop**

- **FR-011**: For each part the system MUST perform, and record as distinct steps: acquire,
  understand (a structured summary of the problem and proposed algorithm), generate a program,
  test it against examples, repair on failure, escalate on repeated failure, execute on the real
  input, submit, and interpret the response.
- **FR-012**: Generated programs MUST expose a single consistent entry point that receives the input
  text and returns the answer as text, and MUST compute the answer from the input (no hardcoded
  answers).
- **FR-013**: Repair attempts MUST be given the failing example, expected and actual output, error
  messages and timeout information.
- **FR-014**: The system MUST route most work to a primary model and escalate to a stronger model
  after a configurable number of failed attempts or on complexity signals (e.g. timeouts), passing a
  concise handover summary rather than the full conversation.
- **FR-015**: The system MUST track three distinct success levels per part — tests passed, candidate
  generated, accepted by Advent of Code — and only the last counts as earned progress.
- **FR-016**: The system MUST mark a part FAILED when its attempt or submission limit is reached and
  BLOCKED when it cannot proceed for an external reason (e.g. Part 1 failed, session invalid); after
  a FAILED or BLOCKED part the run MUST continue with the next day.

**Submission**

- **FR-017**: The system MUST submit answers to the real website for the correct day and part and
  classify the response as: correct, incorrect, too high, too low, cooldown (with wait time), already
  completed, locked/unavailable, authentication failure, or unexpected.
- **FR-018**: Acceptance MUST be determined only from the website's response or reconciled account
  state, never from the HTTP status alone.
- **FR-019**: The system MUST NEVER submit an answer identical to one already rejected for the same
  part, and MUST use too-high/too-low bounds to discard candidates outside known bounds.
- **FR-020**: The system MUST persist cooldown deadlines and not submit before they expire;
  application retries MUST be independent of website cooldowns. During a cooldown the agent MAY
  continue local diagnosis of the same part but MUST NOT start a later part.
- **FR-021**: If a submission outcome is uncertain, the system MUST reconcile against the day's
  completion state before any further submission for that part.
- **FR-022**: On acceptance of Part 1 the system MUST fetch Part 2 and continue; on acceptance of
  Part 2 (or Day 25's final claim) it MUST advance to the next day. Day 25 Part 2 MUST be claimed
  only when the account holds the other 49 stars, otherwise marked SKIPPED with the reason.

**Execution sandbox**

- **FR-023**: Generated programs MUST run only in an isolated remote sandbox with no outbound network
  access, bounded CPU/memory/time/output, no access to host files or application secrets.
- **FR-024**: Each execution MUST return a structured result: answer, standard output, standard
  error, exception details, duration, timeout flag, and a correlation identifier.

**Run control and persistence**

- **FR-025**: Operators MUST be able to start, pause, resume, stop, reset local run data, retry a
  blocked or failed part, and view previous runs.
- **FR-026**: The system MUST persist runs, configuration, day and part progress, attempts, model
  invocations, program revisions, test results, execution results, candidate answers, submission
  outcomes, cooldowns, events, timings and costs.
- **FR-027**: After a restart, the system MUST restore all persisted state and allow the
  interrupted run to resume from a safe point without repeating confirmed work.
- **FR-028**: Resetting local data MUST clearly state that Advent of Code account progress is not
  reset.
- **FR-029**: Runs MUST continue until the range completes, the operator pauses/stops, a budget or
  limit is reached, an unrecoverable service error occurs, or a cooldown blocks submission; no
  artificial delays are added to reasoning, generation, testing or execution.

**Observability and dashboard**

- **FR-030**: Every significant action MUST emit a persisted, ordered event describing what actually
  happened; events MUST NOT contain secrets or personal input content.
- **FR-031**: Clients MUST receive events in real time and be able to reconnect without losing or
  duplicating events.
- **FR-032**: The dashboard MUST show year, range, run status, current day/part, verified stars,
  failed/blocked parts, current model, attempts, elapsed time and estimated cost.
- **FR-033**: The calendar MUST show all 25 days with independent Part 1/Part 2 states: unsolved,
  solving, tests passed, submitted, verified, previously completed, failed, blocked; a star appears
  only on server-confirmed acceptance, with a visually rewarding effect.
- **FR-034**: The dashboard MUST provide a code inspector with syntax highlighting, revision history
  and execution results per revision.
- **FR-035**: Escalations MUST be visually prominent (primary → escalation model) with the reason.
- **FR-036**: A presentation view MUST show large calendar, star count, current activity, current
  model and a compact code/execution panel, suitable for fullscreen.
- **FR-037**: The system MUST track per run and per part: model calls, input/output/reasoning tokens
  (when reported), latency, estimated cost (from configurable prices), and escalations.
- **FR-038**: The system MUST expose model-provided summaries and actions but MUST NOT request or
  display hidden chain-of-thought.

**Replay**

- **FR-039**: Operators MUST be able to replay any recorded run's events without contacting external
  services; replays MUST be labelled as such in every view.

**Respectful automation and security**

- **FR-040**: All website requests MUST be sequential, paced by a configurable minimum interval, carry
  a descriptive identification string with operator contact information, honor rate-limit and
  retry-after responses, and use exponential backoff for transient server errors.
- **FR-041**: Outbound requests MUST be limited to an allowlist of hosts with redirect validation.
- **FR-042**: The account session and service credentials MUST remain in the backend only and MUST
  NOT appear in the sandbox, model prompts, client application, logs, events, or version control.
- **FR-043**: Puzzle content and model output MUST be treated as untrusted and kept separate from
  system instructions in model prompts.
- **FR-044**: Private puzzle text and personal inputs MUST be stored outside version control.
- **FR-045**: The project documentation MUST acknowledge the puzzle author's stance discouraging AI
  solving and explain the historical, educational purpose.

**Preflight and presentation support**

- **FR-046**: A preflight MUST verify session validity, model availability for both models, sandbox
  execution and isolation, writable storage, presence of unsolved parts in the selected range, and
  presence of development checkpoints — without submitting answers or fetching locked parts.
- **FR-047**: The presenter MUST be able to switch a separate working copy between development
  checkpoints without interrupting the live solver, with warnings before any uncommitted change
  could be lost, and return to the completed state.
- **FR-048**: Presenter documentation MUST describe preparation, the 25-minute demo script,
  checkpoint navigation, preflight, troubleshooting and replay.

### Key Entities

- **Run**: one execution over a year and day range; configuration, authorization mode, status
  (created/running/paused/stopped/completed/budget-exhausted/failed), live vs replay, timestamps,
  totals.
- **Day Progress**: a day within a run; title and per-part status.
- **Part Progress**: a part within a day; state (NOT_STARTED, FETCHING, ANALYZING, GENERATING,
  TESTING, REPAIRING, ESCALATING, EXECUTING_INPUT, READY_TO_SUBMIT, SUBMITTING,
  WAITING_FOR_COOLDOWN, VERIFIED, BLOCKED, FAILED, SKIPPED), whether previously completed, accepted
  answer, attempt counts.
- **Attempt**: one solving attempt for a part; model used, understanding summary, program revision,
  outcome.
- **Model Invocation**: one call to a model; purpose, model, tokens, latency, estimated cost,
  success/infra error.
- **Code Revision**: a version of a generated program, linked to its attempt.
- **Test Result / Execution Result**: outcome of running a revision on an example or the real input.
- **Submission**: a candidate answer sent for a part; outcome classification, message, wait time,
  timestamp, uncertainty flag.
- **Cooldown**: next eligible submission time for the account.
- **Event**: ordered, persisted record of an observable action, with sequence number and type.
- **Puzzle Cache Entry**: locally stored description/input for a year/day/part (private, not
  versioned).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a live run against the real website, at least one previously unsolved part is
  solved, submitted and accepted with no operator interaction after start, and its Part 2 is then
  unlocked and attempted automatically.
- **SC-002**: Across Advent of Code 2024 days 1–5, the agent earns at least 8 of 10 stars when run
  unattended (measured on a fresh account or recorded run).
- **SC-003**: Zero identical answers are ever resubmitted for the same part, and zero submissions
  occur before a recorded cooldown deadline (verified from persisted submission history).
- **SC-004**: Dashboard events appear within 2 seconds of occurring; after a reconnect, the
  timeline is complete with no duplicates.
- **SC-005**: After an unplanned restart, a run resumes with 100% of previously verified parts intact
  and without any duplicate submission.
- **SC-006**: Typical Advent of Code website traffic for a full day (both parts) is at most ~10
  requests, all spaced by the configured minimum interval.
- **SC-007**: The presenter can switch through all seven development checkpoints in under 2 minutes
  total while the live solver continues without interruption.
- **SC-008**: Preflight completes in under 2 minutes and reports a pass/fail result for every check.
- **SC-009**: No secret or personal input appears in any log, event, client payload or committed
  file (verified by automated scans in tests).
- **SC-010**: The presentation view is legible from 10 m on a 1080p projector (minimum ~24 px body
  text equivalent, star count readable at a glance).

## Assumptions

- Advent of Code 2024 is the primary supported calendar; other years may work but are untested.
- The operator obtains their account session by logging in normally in a browser and supplies it to
  the backend configuration; the application does not implement the website's third-party login.
- The operator provisions the cloud model deployments and the execution sandbox ahead of time and
  supplies their endpoints; the application never creates cloud resources itself.
- The solver is run only outside an active Advent of Code event; historical puzzles are open.
- A single operator uses the application on their own machine; multi-user access control is out of
  scope (the backend binds to the local machine only).
- Run data, cached puzzles and inputs are stored in a local data directory outside version control.
- A "cooldown" applies per account across parts, as the website enforces it per account.
- Model pricing changes; prices are configuration, not code.
- The presentation lasts 25 minutes; the full calendar is not expected to finish within it.
- The audience-facing AI coding assistant during the talk is GitHub Copilot; development uses Claude
  Code. Both use the same specification artifacts.
