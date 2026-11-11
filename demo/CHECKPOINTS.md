# Development checkpoints

Each tag points at the genuine commit created when that Spec Kit stage finished. They are listed in
order with `git log --oneline --decorate`. Switch worktree B with `scripts\show-checkpoint.ps1 <name>`.

| Name | Tag | Spec Kit step | Open these | Talking point |
|------|-----|---------------|------------|---------------|
| initial | `demo/00-initial` | `specify init --integration claude --script ps` | `.specify/`, `.claude/skills/speckit-*` | Spec Kit 1.4.0 adds templates, scripts and agent skills. There is no code yet. |
| constitution | `demo/01-constitution` | `/speckit-constitution` | `.specify/memory/constitution.md` | Seven non-negotiables, such as "stars only on server-confirmed acceptance" and "generated code never runs on the host". They govern everything after this point. |
| specify | `demo/02-specify` | `/speckit-specify` | `specs/001-agentic-aoc-solver/spec.md`, `checklists/requirements.md` | Seven user stories, 48 FRs and success criteria, with no technology named. The agent took the tech stack out of the brief on purpose. |
| clarify | `demo/03-clarify` | `/speckit-clarify` | `spec.md` → `## Clarifications` | Five decisions: request pacing, failure progression, the submission cap, cooldown behaviour and Day 25. The provenance note says these were the agent's own decisions; no stakeholder meeting was invented. |
| plan | `demo/04-plan` | `/speckit-plan` | `plan.md`, `research.md`, `data-model.md`, `contracts/*` | The technical plan: Foundry Responses vs Claude Messages, the Dynamic Sessions harness, the state machine and the Constitution Check gate. |
| tasks | `demo/05-tasks` | `/speckit-checklist`, `/speckit-tasks`, `/speckit-analyze` | `tasks.md`, `checklists/submission-safety.md`, `analysis.md` | 83 tasks grouped by user story. Analyze found 2 HIGH issues (an infra outage would have cascaded BLOCKED; there was no guard against hard-coded answers), and both were fixed before any code existed. |
| implement | `demo/06-implement` | `/speckit-implement` | `backend/app/agents/orchestrator.py`, `frontend/src/pages/Presentation.tsx`, `tasks.md` `[X]` | The working app, with 75 backend tests and 5 frontend tests at this point. The checklist gate showed 0/26 reviewer items checked; the commit message records that implementation went ahead anyway. |
| complete | `demo/07-complete` | `/speckit-converge` → `/speckit-implement` | `tasks.md` Phase 11, `traceability.md`, `docs/adr/`, `demo/`, `.github/skills/` | Converge added 7 tasks covering gaps it found (one was a contract mismatch). They were implemented, and a second converge pass came back clean. The Copilot integration was added here. |

Commits without a tag, between checkpoints, are intermediate steps of the same stage (for example the
checklist and tasks commits before `demo/05-tasks`). They show the history is genuine and was not
squashed.

Spec Kit tracks the active feature in `.specify/feature.json`, separately from the branch. That file
is git-ignored per checkout, so `show-checkpoint.ps1` writes
`{"feature_directory": "specs/001-agentic-aoc-solver"}` whenever the checkpoint contains the spec, and
removes the file at `initial` and `constitution`.
