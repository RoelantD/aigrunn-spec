"""NEXT_STEP.md content per walkthrough branch. Key = the branch the file lives on."""

FOOT = """
---

<sub>Branch `{branch}`. Its content is identical to the real development stage
({source}). The Copilot Spec Kit skills (`.github/skills/speckit-*`) are added to every branch from
`01-install`, so `/speckit-…` works in Copilot Chat during the walkthrough. In the original run they
were installed at the end. The stages ran in Claude Code; on stage you show the same prompts in
GitHub Copilot. A model will not reproduce the result byte for byte, so the next branch holds the
recorded output.</sub>
"""

STEPS = {
"00-start": ("an empty repository with only an intent", "a fresh root commit (title page only)", """
# You are here: 00 · start

Nothing exists yet except an idea: *an agent that earns real Advent of Code stars*.

## Next: install Spec Kit → `01-install`

Run in a terminal:

```powershell
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@v1.4.0
specify init --here --integration claude --script ps
specify integration install copilot --script ps --force   # second agent, default stays claude
```

**What appears:**
- `.specify/` holds the templates, scripts and an empty constitution template.
- `.claude/skills/speckit-*` and `.github/skills/speckit-*` hold the agent commands.

```powershell
.\\scripts\\show-checkpoint.ps1 01-install
```
"""),

"01-install": ("Spec Kit initialized", "tag `demo/00-initial`", """
# You are here: 01 · install

Spec Kit is installed. There are templates and agent skills, and still no code.

## Next: the constitution → `02-constitution`

Type in Copilot Chat:

```text
/speckit-constitution Principles for an autonomous agent that solves historical Advent of Code
puzzles and submits answers to the real website:
1. Authentic verification: only server-confirmed acceptance counts as progress. Distinguish tests
   passed / candidate generated / accepted. Never simulate solving, execution or acceptance. Replays
   must be labelled.
2. Isolation: model-generated code only runs in an isolated remote sandbox without network.
   Secrets never reach the sandbox, prompts, frontend, logs or git. Treat puzzle HTML and model
   output as untrusted.
3. Respectful automation: historical puzzles only, sequential paced and cached requests with an
   identifying User-Agent, honour cooldowns, never resubmit a rejected answer, never redistribute
   puzzle text or inputs.
4. Observable, honest agent behaviour: every action is a persisted event; show summaries, not
   chain-of-thought; mark unverified integrations.
5. Bounded, recoverable autonomy: configurable limits, infra retries separate from solving attempts,
   persist everything, reconcile uncertain submissions.
6. Test-backed delivery with synthetic puzzles and mocked HTTP; never submit in CI.
7. Simplicity and clear module boundaries; custom agent loop, no agent framework.
```

**What appears:** `.specify/memory/constitution.md`, version 1.0.0, with seven principles and a
governance section.

```powershell
.\\scripts\\show-checkpoint.ps1 02-constitution
```
"""),

"02-constitution": ("constitution ratified", "tag `demo/01-constitution`", """
# You are here: 02 · constitution

There are seven non-negotiable principles. Every later step is checked against them.

## Next: the specification → `03-specify`

Type in Copilot Chat:

```text
/speckit-specify Build an Agentic Advent of Code Solver: given a calendar URL such as
https://adventofcode.com/2024, the application autonomously solves the selected days in order using
cloud-hosted AI models — it reads each puzzle, writes a program, tests it on the puzzle's examples
in a secure sandbox, repairs failures, escalates hard problems to a stronger model, runs the program
on the user's real input, submits the answer to the real Advent of Code website with run-level
authorization, interprets the response, unlocks Part 2, and advances until the range is complete or
a limit is reached. A conference-ready live dashboard shows real progress, generated code, model
escalations, submissions, stars and costs. Progress persists and resumes safely. Recorded runs can
be replayed (clearly labelled). The presenter must be able to show historical development
checkpoints without interrupting the running solver. It is for historical puzzles and education
only, and must treat Advent of Code respectfully.
```

**What appears:** `specs/001-agentic-aoc-solver/spec.md` with 7 user stories, 48 functional
requirements and 10 success criteria, plus `checklists/requirements.md`. The spec names no technology.

```powershell
.\\scripts\\show-checkpoint.ps1 03-specify
```
"""),

"03-specify": ("feature specification written", "tag `demo/02-specify`", """
# You are here: 03 · specify

The spec says what and why. It doesn't say how.

## Next: clarify → `04-clarify`

Type in Copilot Chat:

```text
/speckit-clarify
```

The command asks up to five questions, one at a time. In the recorded run the agent picked its own
recommended option for each, and the spec records that.

**What appears:** a `## Clarifications` section with five decisions:
- request pacing of at least 5 s
- when a part fails: mark it FAILED, BLOCK its Part 2, and continue
- at most 3 submissions per part
- no working ahead during a cooldown
- the Day 25 final-star rule

The matching requirements are updated too.

```powershell
.\\scripts\\show-checkpoint.ps1 04-clarify
```
"""),

"04-clarify": ("ambiguities resolved", "tag `demo/03-clarify`", """
# You are here: 04 · clarify

Five decisions that weren't in the brief are now one line each in the spec.

## Next: the technical plan → `05-plan`

Type in Copilot Chat:

```text
/speckit-plan Python 3.12 FastAPI backend with Pydantic, SQLAlchemy on SQLite and Server-Sent
Events; React + TypeScript + Vite + Tailwind dashboard with a fullscreen presentation view. Models
on Microsoft Foundry: GPT-6.1 Sol as workhorse via the OpenAI Responses API, Claude Opus 5.5 for
escalation via the Claude Messages API, Entra ID auth. Generated Python runs only in Azure Container
Apps Dynamic Sessions with egress disabled. Custom orchestration loop, no agent framework. Bicep +
azd for infrastructure; the app runs locally. Research the current APIs before designing.
```

**What appears:**
- `plan.md` with the architecture, the state machine and the Constitution Check gate
- `research.md`, which found two models behind two different APIs
- `data-model.md`
- `contracts/`, including "HTTP 200 ≠ accepted"
- `quickstart.md`

```powershell
.\\scripts\\show-checkpoint.ps1 05-plan
```
"""),

"05-plan": ("technical plan and design artifacts", "tag `demo/04-plan`", """
# You are here: 05 · plan

The "how" now exists: architecture, contracts and research, gated by the constitution.

## Next: checklist + tasks → `06-tasks`

Type in Copilot Chat, one after the other:

```text
/speckit-checklist Submission integrity and security: real answer submission, recovery after
crashes, isolation and secret handling.
```

```text
/speckit-tasks
```

**What appears:**
- `checklists/submission-safety.md`: 26 questions that test the quality of the requirements. A
  reviewer owns them and ticks them off.
- `tasks.md`: 83 tasks grouped by user story, with parallel markers and dependencies.

```powershell
.\\scripts\\show-checkpoint.ps1 06-tasks
```
"""),

"06-tasks": ("checklist and task list", "commit `66357b8` (between `demo/04-plan` and `demo/05-tasks`)", """
# You are here: 06 · tasks

There are 83 traceable tasks. No code yet.

## Next: cross-artifact analysis → `07-analyze`

Type in Copilot Chat:

```text
/speckit-analyze
```

Then, after reading the report:

```text
Apply the suggested remediation for F1, D1, E1, E2, E3, B1 and F2 to plan.md and tasks.md.
```

**What appears:** `analysis.md` with 0 critical findings, **2 HIGH** and 98 % requirement
coverage:
- F1: an outage would have cascaded BLOCKED into every remaining day.
- D1: there was no guard against hard-coded answers.

Both are fixed in `plan.md` and `tasks.md`.

```powershell
.\\scripts\\show-checkpoint.ps1 07-analyze
```
"""),

"07-analyze": ("analysis completed and remediated", "tag `demo/05-tasks`", """
# You are here: 07 · analyze

Two HIGH issues were fixed as text edits, before any code existed.

## Next: implement → `08-implement`

Type in Copilot Chat:

```text
/speckit-implement
```

The command first checks the checklists. `submission-safety.md` has 0 of 26 items reviewed, so it
asks whether to proceed. **In the recorded run the agent proceeded under a standing "keep going"
instruction, and recorded that in the commit message.** That is the gate slide 15 talks about.

**What appears:** the full application.
- `backend/`: orchestrator, Advent of Code client, Foundry adapters, sandbox executor, API, 75 tests
- `frontend/`: dashboard and presentation view
- `infra/` and `scripts/`
- `tasks.md` with every completed task marked `[X]`

```powershell
.\\scripts\\show-checkpoint.ps1 08-implement
```
"""),

"08-implement": ("implemented application", "tag `demo/06-implement`", """
# You are here: 08 · implement

The application exists and its tests pass. Does it do everything the spec promised?

## Next: converge → `09-converge`

Type in Copilot Chat, and repeat until it reports nothing:

```text
/speckit-converge
```

```text
/speckit-implement
```

**What appears:**
- `tasks.md` gains Phase 11 (pass 1: 7 gaps, one of them contradicting a contract) and Phase 12
  (pass 2: 2 gaps). Pass 3 is clean.
- `traceability.md` maps every requirement to code and tests.
- Also: ADRs, presenter docs, and the Copilot integration.

```powershell
.\\scripts\\show-checkpoint.ps1 09-converge
```
"""),

"09-converge": ("converged, tested, documented", "tag `demo/07-complete`", """
# You are here: 09 · converge

The spec and the code agree, three passes later. Every requirement traces to code and to a test.

## Next: make it real → `10-working`

This step is about evidence, not a Spec Kit command. Run against the real services:

```powershell
azd provision                                  # session pool + role assignments
.\\scripts\\preflight.ps1 -Days 1-5               # real models, real sandbox, no submissions
cd backend; uv run pytest -m live_azure tests/live
```

Then type in Copilot Chat:

```text
The live tests failed. Diagnose using the spec and plan, fix the root cause, and record what was
verified against real services in docs/TESTING.md.
```

**What appears:**
- `aiohttp` added. Every mocked test had passed, but the first real Entra ID token call failed.
- Credential sessions are now closed on shutdown.
- Infra reuses an existing resource group and Foundry account.
- `docs/TESTING.md` lists what is verified live.
- The talk script and the Claude Design prompt.

```powershell
.\\scripts\\show-checkpoint.ps1 10-working
```
"""),

"10-working": ("working, verified against real services", "branch `main` at the time the walkthrough was built", """
# You are here: 10 · working

The real thing runs against GPT-6.1 Sol and Claude Opus 5.5 on Microsoft Foundry, in Azure
Dynamic Sessions, against the real Advent of Code website.

## Run it

```powershell
.\\scripts\\preflight.ps1 -Days 1-5
.\\scripts\\start-live-app.ps1
```

Then go to the dashboard → **New live run** → authorize submission → **Start**.

## Walk back through the journey

```powershell
.\\scripts\\show-checkpoint.ps1 -List
```

Every step from `00-start` to `10-working` has its own `NEXT_STEP.md` with the prompt that led to
the next step.
"""),
}
