# Agentic Advent of Code Solver

An autonomous agent that solves **historical** Advent of Code puzzles end to end. It reads a puzzle,
writes Python, tests it in an isolated cloud sandbox, repairs failures, escalates hard problems to a
stronger model, runs the program on the real input, submits the answer to the real website, and
moves on once the website accepts it. It was built with
[GitHub Spec Kit](https://github.com/github/spec-kit) as the central demo of a 25-minute talk on
Spec-Driven Development.

| Layer | What |
|-------|------|
| AI developing software | Spec Kit artifacts in [`specs/001-agentic-aoc-solver`](specs/001-agentic-aoc-solver), with checkpoint tags `demo/00-initial` … `demo/07-complete` |
| AI solving problems | GPT-6.1 Sol (workhorse) and Claude Opus 5.5 (escalation) on Microsoft Foundry; Python runs in Azure Container Apps Dynamic Sessions with egress disabled |

## Respectful use and the author's stance

- The creator of Advent of Code **discourages using AI to solve the puzzles**. The puzzles are made for
  people, and handing them to a machine skips the point. We agree with that. This project exists for
  a technical, educational demo on **puzzles from past years**. It must not be used to compete, and it
  must not run while an Advent of Code event is live.
- Puzzle text and personal inputs are **not redistributed**. They are cached under the runtime data
  directory, which lives outside the repository and is git-ignored. Synthetic puzzles are used in tests.
- Traffic policy:
  - Every website request is sequential and at least `AOC_MIN_INTERVAL_S` apart (default 5 s, minimum 1 s).
  - Requests carry a User-Agent with your contact details.
  - Inputs are cached permanently. A puzzle page is fetched again only after an accepted answer changes it.
  - `Retry-After` and cooldowns are honoured.
  - Failed GETs back off exponentially. A POST is never retried automatically.
  - An answer that was already rejected is never submitted again.
  - The private-leaderboard "15 minutes" guidance does not apply, because this app never reads leaderboards.
- Answers are submitted only after you authorize automatic submission for that run in the UI.

## Architecture

```text
React dashboard (Vite, :5175) ──SSE/REST──► FastAPI (:8765, localhost only)
                                              ├─ Orchestrator: state machine per part
                                              │   ├─ Solver: understand → generate → test → repair → escalate → run
                                              │   ├─ ModelRouter: ResponsesAdapter (GPT-6.1 Sol) | MessagesAdapter (Claude Opus 5.5)
                                              │   ├─ DynamicSessionsExecutor: harness + remote Python, no egress
                                              │   └─ Verification: verbatim examples, answer ledger, hardcode guard
                                              ├─ AocClient: paced, cached, allowlisted, no redirects
                                              ├─ EventBus: persisted events → SSE (Last-Event-ID resume)
                                              └─ SQLite in APS_DATA_DIR (outside the repo)
```

The full design is in [plan.md](specs/001-agentic-aoc-solver/plan.md), with decisions recorded in
[docs/adr](docs/adr).

## Quick start

```powershell
# 1. Provision Azure (Foundry deployments + session pool + roles). Review infra/ first.
azd provision
# 2. Configure: copy .env.example to ..\aps-data\.env and fill in the values (AOC_SESSION, endpoints)
# 3. Prepare the two worktrees, then run preflight and start the app
.\scripts\setup-demo.ps1
.\scripts\preflight.ps1 -Days 1-5
.\scripts\start-live-app.ps1
```

Open http://127.0.0.1:5175, the dashboard, or http://127.0.0.1:5175/present, the presentation view.
The presenter procedure is in [demo/PRESENTER_GUIDE.md](demo/PRESENTER_GUIDE.md).

## Development

```bash
cd backend && uv sync && uv run pytest && uv run ruff check .
cd frontend && npm install && npm test && npm run build
```

Tests that hit live cloud resources are opt-in and never submit answers:
`uv run pytest -m live_azure tests/live`. [docs/TESTING.md](docs/TESTING.md) records what has been
verified against real services.
