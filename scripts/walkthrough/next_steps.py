"""NEXT_STEP.md content per walkthrough branch. Key = the branch the file lives on.

Kept deliberately lean: where you are, the raw command or prompt for the next step, and the plain
`git switch` that shows its recorded result. Provenance is documented in demo/CHECKPOINTS.md.
"""

FOOT = ""

STEPS = {
"00-start": ("an empty repository with only an intent", "a fresh root commit (title page only)", """
# You are here: 00 · start

An empty repository with an intent and no code yet.

## Next → 01-install

```powershell
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@v1.4.0
specify init --here --integration claude --script ps
specify integration install copilot --script ps --force
```

```powershell
git switch 01-install
```
"""),

"01-install": ("Spec Kit initialized", "tag `demo/00-initial`", """
# You are here: 01 · install

Spec Kit templates and agent skills are installed. There is no code yet.

## Next → 02-constitution

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

```powershell
git switch 02-constitution
```
"""),

"02-constitution": ("constitution ratified", "tag `demo/01-constitution`", """
# You are here: 02 · constitution

Seven non-negotiable principles. Every later step is checked against them.

## Next → 03-specify

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

```powershell
git switch 03-specify
```
"""),

"03-specify": ("feature specification written", "tag `demo/02-specify`", """
# You are here: 03 · specify

The spec covers what and why, but not how.

## Next → 04-clarify

```text
/speckit-clarify
```

```powershell
git switch 04-clarify
```
"""),

"04-clarify": ("ambiguities resolved", "tag `demo/03-clarify`", """
# You are here: 04 · clarify

Five decisions that were missing from the brief are now in the spec.

## Next → 05-plan

```text
/speckit-plan Python 3.12 FastAPI backend with Pydantic, SQLAlchemy on SQLite and Server-Sent
Events; React + TypeScript + Vite + Tailwind dashboard with a fullscreen presentation view. Models
on Microsoft Foundry: GPT-6.1 Sol as workhorse via the OpenAI Responses API, Claude Opus 5.5 for
escalation via the Claude Messages API, Entra ID auth. Generated Python runs only in Azure Container
Apps Dynamic Sessions with egress disabled. Custom orchestration loop, no agent framework. Bicep +
azd for infrastructure; the app runs locally. Research the current APIs before designing.
```

```powershell
git switch 05-plan
```
"""),

"05-plan": ("technical plan and design artifacts", "tag `demo/04-plan`", """
# You are here: 05 · plan

The how is written down, gated by the constitution.

## Next → 06-tasks

```text
/speckit-checklist Submission integrity and security: real answer submission, recovery after
crashes, isolation and secret handling.
```

```text
/speckit-tasks
```

```powershell
git switch 06-tasks
```
"""),

"06-tasks": ("checklist and task list", "commit `66357b8`", """
# You are here: 06 · tasks

83 traceable tasks. There is still no code.

## Next → 07-analyze

```text
/speckit-analyze
```

```powershell
git switch 07-analyze
```
"""),

"07-analyze": ("analysis completed and remediated", "tag `demo/05-tasks`", """
# You are here: 07 · analyze

Two HIGH issues were fixed as text, before any code existed.

## Next → 08-implement

```text
/speckit-implement
```

```powershell
git switch 08-implement
```
"""),

"08-implement": ("implemented application", "tag `demo/06-implement`", """
# You are here: 08 · implement

The app exists and its tests pass. Does it keep every promise in the spec?

## Next → 09-converge

```text
/speckit-converge
```

```powershell
git switch 09-converge
```
"""),

"09-converge": ("converged, tested, documented", "tag `demo/07-complete`", """
# You are here: 09 · converge

The spec and the code agree. Every requirement traces to code and to a test.

## Next → 10-working

```powershell
azd provision
cd backend
uv run python cli.py preflight --days 1-5
uv run pytest -m live_azure tests/live
```

```powershell
git switch 10-working
```
"""),

"10-working": ("working, verified against real services", "branch `main`", """
# You are here: 10 · working

The solver runs live against the real models, the real sandbox and the real website.

## Run it

```powershell
cd backend; uv run uvicorn app.main:get_app --factory --port 8765
cd frontend; npm run dev
```
"""),
}
