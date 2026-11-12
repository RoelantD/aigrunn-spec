# 25-minute demo script

Before going on stage, finish [PREFLIGHT_CHECKLIST.md](PREFLIGHT_CHECKLIST.md). Have these windows
ready:

1. **Browser**, tab 1: the dashboard at `http://127.0.0.1:5175`. Tab 2: `/present`, fullscreen.
2. **VS Code** on `aps-walkthrough`, with Copilot Chat open.
3. **Terminal** in the development clone, for `show-checkpoint.ps1`.

Nothing in this script is staged. If something does not happen live, say so.

---

## 0:00–2:00 · The challenge, then start the solver

- *"Advent of Code: 25 days of two-part programming puzzles. Part 2 only unlocks after the website
  accepts Part 1. Today an agent tries to earn real stars while I show you how it was built."*
- Mention the author's position: AI solving is discouraged. These are **past puzzles**, run for an
  educational demo.
- Dashboard → **New live run**. Set the days to the first unsolved day through 25.
- Turn on **automatic submission**, tick **authorize**, click **Verify connections**, then **Start live run**.
- Switch to `/present`. Point at the first events: *Loading puzzle… → Analyzing requirements using
  GPT-6.1 Sol.* Click the 25:00 clock.

## 2:00–5:00 · Constitution and specification

- `.\scripts\show-checkpoint.ps1 constitution` → `.specify/memory/constitution.md`.
  - Principle I: a star only after the website confirms.
  - Principle II: model code never runs on this laptop.
  - Principle III: be kind to the website.
- `show-checkpoint.ps1 specify` → `spec.md`. Walk through the user stories and their priorities.
  - *"Notice there is no React, no FastAPI, no model names. The spec is what and why."*
  - Ask Copilot: `#file:specs/001-agentic-aoc-solver/spec.md which requirement stops duplicate wrong answers?` (FR-019)

## 5:00–8:00 · Clarification

- `show-checkpoint.ps1 clarify` → `## Clarifications`.
- Call out the requirements that are easy to miss:
  - authenticated access: the session cookie stays in the backend only
  - **real submission is mandatory**, because Part 2 depends on it
  - the cap on wrong answers
  - cooldown behaviour
  - Day 25
  - sandboxing
  - escalation
  - persistence
  - reconciling after a lost connection
- Point out the provenance note: these decisions were made by the agent, and the spec says so.

## 8:00–12:00 · Architecture and planning

- `show-checkpoint.ps1 plan` → `plan.md`: the architecture diagram and the state machine.
- `research.md`:
  - R7: GPT-6.1 Sol uses the Responses API.
  - R8: Claude Opus 5.5 uses the Messages API.
  - R9: Dynamic Sessions, with egress disabled.
- `contracts/aoc-client.md`: how responses are classified. *"HTTP 200 does not mean accepted."*
- The Constitution Check table: a gate in the plan.
- **Check the live run**: glance at `/present` (10 seconds), then go back.

## 12:00–14:00 · Tasks and implementation

- `show-checkpoint.ps1 tasks` → `tasks.md`: tasks grouped by user story, with [P] markers.
- `analysis.md`: two HIGH findings were fixed before any code was written.
- `show-checkpoint.ps1 implement` → `orchestrator.py`, `_submit()`. Show PENDING being written before
  the POST, and the reconcile path.
- `show-checkpoint.ps1 complete` → Phase 11 convergence tasks and `traceability.md`.

## 14:00–23:00 · The live agentic solver

Back on `/present`, show what happened while you talked:

- **Stars**: the large number counts only server-confirmed stars. Dim stars mean previously completed.
- **Activity feed**: scroll back to a *Test failed: expected X, received Y → Generating revised
  solution* sequence, if one happened.
- **Dashboard → Code inspector**: click a solved cell. Show revisions r1→r2, the example-test table,
  the real-input answer and the sandbox session id.
- **Submissions**: *Submitting candidate answer → Advent of Code accepted the answer → Unlocking Part 2.*
- **Escalation** (if it happened): the purple banner and its reason; the code inspector tab in purple.
- **Metrics**: calls, tokens including reasoning tokens, latency, estimated cost.
- If something you wanted to show did not happen, say so. Then open the recorded run as a
  **REPLAY** ([REPLAY_GUIDE.md](REPLAY_GUIDE.md)); it is clearly labelled.

## 23:00–25:00 · Conclusion

- The specification made explicit the things a quick prototype would have missed: submission
  integrity, cooldowns and Part 2 dependencies.
- The same artifacts drove Claude Code during development and GitHub Copilot today.
- Verification and retry loops are what turn "the model wrote code" into "the website accepted
  the answer".
- Spec Kit made the build traceable: tags, artifacts, and FR → code → test.
- Leave the solver running, or click **Pause** (safe at any point).
