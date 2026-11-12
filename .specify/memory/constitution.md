# Agentic Advent of Code Solver Constitution

## Core Principles

### I. Authentic Verification (NON-NEGOTIABLE)

- Progress MUST be reported only from real events. The system MUST distinguish three levels of
  success and never conflate them: *tests passed* (local examples/regressions), *candidate
  generated* (an answer computed from the real input), and *accepted* (the Advent of Code website
  confirmed the answer, or reconciled account state shows the part complete).
- A star or "verified" status MUST appear only after server-confirmed acceptance.
- The primary product path MUST NOT simulate puzzle solving, model reasoning, code execution, or
  server acceptance. Mocks and synthetic puzzles are permitted only in automated tests.
- Recorded runs MAY be replayed for presentation, but a replay MUST be labelled as replay in every
  view and MUST NOT contact Advent of Code or pretend to be live.
- Generated solutions MUST compute answers from the input; hardcoding known answers is forbidden.

Rationale: the application exists to demonstrate genuine AI problem solving. Any fabricated signal
destroys the value of the demonstration and misleads the audience.

### II. Isolation of Untrusted Code and Content (NON-NEGOTIABLE)

- Model-generated code MUST execute only in an isolated remote sandbox with outbound network access
  disabled, bounded CPU, memory, time and output size. It MUST NEVER run in the backend process or
  on the host.
- Session cookies, model credentials, and Azure tokens MUST live only in the backend. They MUST NOT
  reach the sandbox, model prompts, the frontend, logs, events, persisted run data, or Git.
- Puzzle HTML and model output are untrusted data. External content MUST be clearly separated from
  system instructions in every prompt, and outbound HTTP MUST be restricted to an allowlist of
  hosts with redirect validation.

Rationale: the system routinely runs code written by a model against content fetched from the
internet; isolation is the only safe default.

### III. Respectful Automation

- The solver is for historical puzzles and educational demonstration. It MUST NOT be positioned or
  used for competing during an active Advent of Code event.
- All traffic to Advent of Code MUST be sequential, paced, identified by a descriptive User-Agent
  with maintainer contact information, and minimized through caching. Inputs and puzzle pages MUST
  be cached and not re-fetched while unchanged.
- Server cooldowns, rate limits and Retry-After MUST be honored; they MUST NOT be circumvented.
- An identical rejected answer MUST NEVER be resubmitted; answer submission MUST NOT be used as a
  brute-force oracle.
- Puzzle text and personal inputs MUST NOT be redistributed through the repository.

Rationale: the puzzles are a free community resource whose author has asked automation to be
gentle; the project must respect that while acknowledging the author discourages AI solving.

### IV. Observable and Honest Agent Behavior

- Every significant agent action (fetch, model call, code revision, execution, test, submission,
  escalation, state change) MUST emit a persisted, ordered event derived from what actually
  happened.
- The system MUST expose observable summaries, actions, outputs, model choices and usage metrics
  (tokens, latency, estimated cost) but MUST NOT expose or request hidden model chain-of-thought.
- Integrations that have not been exercised against real services MUST be explicitly reported as
  unverified.

Rationale: observability is what makes an autonomous agent trustworthy and demonstrable.

### V. Bounded, Recoverable Autonomy

- Autonomy MUST be bounded: attempts per part, model escalations, execution time, tokens and spend
  per run are configurable limits, and every retry loop has a finite bound.
- Infrastructure failures (rate limits, outages, network errors) MUST be distinguished from
  problem-solving failures and handled by independent retry mechanisms; application retries and
  website cooldowns are separate concerns.
- All orchestration state MUST be persisted so that a restart resumes from a safe point without
  losing confirmed work. A submission whose outcome is uncertain MUST be reconciled against server
  state before any further submission for that part.
- Local reasoning, generation and execution MUST NOT be artificially delayed.

Rationale: an agent left running during a live talk must be safe to leave alone and safe to restart.

### VI. Test-Backed Delivery

- Behavior MUST be covered by automated unit, integration and end-to-end tests using synthetic puzzle
  content and mocked HTTP. Automated tests MUST NEVER submit real answers or require real secrets.
- Every functional requirement MUST be traceable to implementing code and at least one test.
- Tests that need real cloud resources MUST be opt-in, clearly marked, and reported as executed or
  not executed.

Rationale: correctness of the orchestration (especially submission handling) cannot be verified by
watching a live demo.

### VII. Simplicity and Clear Boundaries

- Prefer the simplest design that satisfies the specification; abstractions MUST be justified by a
  concrete need (e.g. two model providers, a replaceable execution backend).
- Orchestration, model inference, puzzle access, answer verification, sandbox execution,
  persistence and event delivery MUST be separate modules with explicit interfaces.
- The agent loop is custom code; external agent frameworks are not used.

Rationale: a conference audience must be able to follow the architecture, and a small team must be
able to maintain it.

## Security and Data Handling Constraints

- Secrets are supplied via environment variables or an ignored local file and redacted from all
  logs and error messages. Entra ID authentication is preferred where the service supports it.
- Private puzzle descriptions, personal inputs, SQLite state and run recordings are stored in a
  runtime data directory outside the source tree or excluded by `.gitignore`.
- The application MUST NOT create cloud resources, publish content, or submit answers without
  explicit authorization: infrastructure is provisioned by the operator; answer submission requires
  run-level authorization given when the live run starts.
- Resetting local state MUST NOT be presented as resetting Advent of Code account progress.

## Development Workflow and Quality Gates

- Development follows Spec-Driven Development with GitHub Spec Kit: constitution → specify →
  clarify → plan → checklist → tasks → analyze → implement → converge. Artifacts are generated by
  the Spec Kit commands, not written by hand around them, and are preserved in `specs/`.
- Each stage is captured by a genuine Git commit and checkpoint tag (`demo/NN-stage`) created at the
  time the stage completes; history is never rewritten to fabricate checkpoints.
- Clarification decisions are recorded truthfully, including who or what made each decision.
- A change is complete when its tests pass, linters pass, and the requirements it touches remain
  traceable.

## Governance

- This constitution supersedes other practices in this repository. Plans MUST include a
  Constitution Check gate, and `/speckit-analyze` findings that conflict with a MUST principle are
  treated as critical.
- Amendments are made through `/speckit-constitution`, documented in the commit message, and
  versioned semantically: MAJOR for removed or redefined principles, MINOR for new principles or
  materially expanded guidance, PATCH for clarifications.
- Complexity that violates Principle VII MUST be justified in the plan's Complexity Tracking table.
- Runtime development guidance for agents lives in `CLAUDE.md` (Claude Code) and
  `.github/copilot-instructions.md` (GitHub Copilot) once those integrations generate them.

**Version**: 1.0.0 | **Ratified**: 2026-11-11 | **Last Amended**: 2026-11-11
