# Presenter Guide

This guide covers preparing and running the 25-minute Spec-Driven Development talk. The minute-by-minute
script is in [DEMO_SCRIPT_25_MIN.md](DEMO_SCRIPT_25_MIN.md).

**The model:** the finished app runs from worktree **A** (`aps-live`) and keeps solving real puzzles.
Meanwhile you walk through the Spec Kit history in worktree **B** (`aps-walkthrough`). The two never
interfere. Run data lives in `aps-data`, outside both worktrees.

```text
<parent>\agentic-puzzle-solver   development clone (main)
<parent>\aps-live                A: demo/07-complete  -> backend :8765, dashboard :5175
<parent>\aps-walkthrough         B: demo/00 … demo/07 -> open in VS Code + GitHub Copilot
<parent>\aps-data                .env (secrets), solver.db, cache\ (puzzle text + inputs)
```

## 1. One-time prerequisites

| Need | How |
|------|-----|
| Windows 11, Git, Python 3.12 + `uv`, Node 22 + npm, Azure CLI, `azd`, VS Code + GitHub Copilot | `winget install astral-sh.uv OpenJS.NodeJS.LTS Microsoft.AzureCLI Microsoft.Azd` |
| Spec Kit CLI 1.4.0+ | `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@v1.4.0` |
| Azure subscription | Pay-as-you-go in a billing country eligible for Claude in Foundry (the Marketplace terms are accepted at deployment) |

## 2. Provision Azure (once)

Run this from the development clone. Review `infra/` first: it creates billable resources.

```powershell
az login
azd auth login
azd env new aps-demo
azd env set AZURE_LOCATION eastus2
azd env set CLAUDE_ORGANIZATION_NAME "<your legal organization>"
azd env set CLAUDE_COUNTRY_CODE NL
azd provision
azd env get-values      # FOUNDRY_OPENAI_BASE_URL, FOUNDRY_ANTHROPIC_BASE_URL, SESSIONS_POOL_ENDPOINT
```

This creates the following:

- An AIServices account with deployments `gpt-6.1-sol` (Global Standard) and `claude-opus-5-5`
  (Global Standard).
- A Dynamic Sessions pool (PythonLTS, **EgressDisabled**).
- Role assignments for you: *Cognitive Services OpenAI User*, *Cognitive Services User* and
  *Azure ContainerApps Session Executor*.

Authentication uses Entra ID, through your `az login`. No API keys are needed.

Optional pieces:

- If the Claude deployment fails because of subscription eligibility, run
  `azd env set DEPLOY_CLAUDE false`. The app still runs with the workhorse model only, but
  escalation is then disabled.
- If you already have deployments, skip `azd` and put their endpoints and deployment names in `.env`.

## 3. Prepare the worktrees

```powershell
cd <parent>\agentic-puzzle-solver
.\scripts\setup-demo.ps1
```

The script creates `aps-live`, `aps-walkthrough` and `aps-data`, installs dependencies, and copies
`.env.example` to `aps-data\.env`.

## 4. Configure `aps-data\.env`

1. **Advent of Code session.**
   1. Log in at https://adventofcode.com in your browser.
   2. Open DevTools → Application → Cookies → `session` and copy its value.
   3. Set `AOC_SESSION=<value>`.

   The cookie stays in the backend only. It never reaches the models, the sandbox, the browser app,
   the logs or Git.
2. `AOC_CONTACT=<your email or URL>`. It goes into the User-Agent, as the site's automation
   guidance asks.
3. Endpoints and deployment names from `azd env get-values`.
4. Prices in USD per 1M tokens. Check current Foundry pricing; if you leave them at 0, cost shows
   $0 and the spend cap does nothing.

## 5. Check connectivity (no submissions)

```powershell
.\scripts\preflight.ps1 -Days 1-5            # -Preload also caches accessible pages + inputs
```

Preflight checks the following:

- Storage.
- The Advent of Code session, and how many unsolved parts are in the range.
- **Foundry** for both models: one tiny JSON call each.
- **Dynamic Sessions**: it runs `solve()` and probes egress, which must be *blocked*.
- The checkpoint tags.

The same checks are behind the **Verify connections** button in the app.

## 6. Choose the day range

Choose days the account has **not** solved. Preflight lists them. For a 25-minute talk, start at the
first unsolved day and set the end to 25. The solver does not need to finish. Days 1–10 of 2024
usually go fastest.

Never run during an active Advent of Code event (December 1–25, or the event's days for later years).

## 7. Start the live app

```powershell
.\scripts\start-live-app.ps1
```

This opens a backend window (:8765) and a dashboard window (:5175).

- Dashboard: http://127.0.0.1:5175
- Presentation view: http://127.0.0.1:5175/present. Press the expand button for fullscreen. Click
  the 25:00 clock to start the talk timer.

## 8. Start automatic solving and submission

1. In the dashboard, click **New live run**.
2. Leave the calendar URL as `https://adventofcode.com/2024`.
3. Set the first and last day.
4. Leave **Automatic answer submission** on.
5. Tick the authorization checkbox. It covers the whole run.
6. Optionally click **Verify connections**.
7. Click **Start live run**.

The run continues until the range is done, you pause or stop it, the budget runs out, or a cooldown
or service problem pauses it.

## 9. Switch Spec Kit checkpoints (worktree B)

```powershell
.\scripts\show-checkpoint.ps1 -List
.\scripts\show-checkpoint.ps1 constitution     # specify, clarify, plan, tasks, implement, complete
code ..\aps-walkthrough                          # open once; VS Code follows the checkout
.\scripts\return-to-complete.ps1
```

- The script refuses to discard uncommitted changes in B until you type `discard`, and even then it
  stashes them first.
- It never touches A or `aps-data`.
- [CHECKPOINTS.md](CHECKPOINTS.md) lists what to show at each checkpoint.

## 10. Inspect artifacts with GitHub Copilot

At every checkpoint, open Copilot Chat in the walkthrough window and reference files, for example
`#file:specs/001-agentic-aoc-solver/spec.md What did clarification change?`.

The official Spec Kit **Copilot integration** is installed alongside the Claude integration at
`demo/07-complete`:

- Copilot skills live in `.github/skills/speckit-*`. Invoke them in Copilot Chat as `/speckit-plan`
  and so on.
- Claude Code skills live in `.claude/skills/`.
- The default integration stays `claude`.

To make Copilot the default in the walkthrough only, run `specify integration use copilot` there.
This edits the tracked `.specify/integration.json`, so `return-to-complete.ps1` will ask before
discarding the change.

How it was installed (reproducible):

```powershell
specify integration install copilot --script ps --force   # --force = install alongside claude; default unchanged
specify integration status
```

`specify integration status` reports `unsafe-multi-install` because the copilot integration is not
declared multi-install safe. The Claude files are unchanged ("Modified managed files: 0").

Checkpoints 00–06 predate the Copilot install. Copilot Chat can still read and discuss every
artifact there, but the `/speckit-*` Copilot skills exist only from 07.

## 11. Return to the running application

Switch to the browser tab with `/present`. Everything that happened while you talked is in the
calendar, the activity feed (scroll up), the code inspector (dashboard → click a calendar cell) and
the metrics.

## 12. Inspect genuine agent activity

| Want to show | Where |
|--------------|-------|
| Generated Python and revisions | Dashboard → Code inspector (click a cell; tabs r1, r2, …; purple = escalation model) |
| Test failures and repairs | Activity feed: "Test failed: expected …, received …", then "Generating revised solution" |
| Real submissions and verdicts | Activity feed `Submitting candidate answer` → `Advent of Code accepted the answer`; also `GET /api/runs/<id>/submissions` |
| Part 2 unlock | "Unlocking Part 2" → "Day NN Part 2 unlocked" |
| Escalation | Purple banner "GPT-6.1 Sol → Claude Opus 5.5 — reason"; purple dot on the calendar cell |
| Metrics | Inference metrics panel (calls, tokens incl. reasoning, latency, cost) |

## 13. Resume interrupted runs

- After a pause, a cooldown pause, a backend restart or a laptop sleep, open the dashboard and click
  **Resume**.
- If an answer was sent just before an interruption, the app re-reads the day page before it
  submits again (reconciliation). It never repeats a submission blindly.
- If a backend window was closed, rerun `.\scripts\start-live-app.ps1`. The run shows as *paused
  (interrupted)*; then click **Resume**.

## 14. Use replay when necessary

See [REPLAY_GUIDE.md](REPLAY_GUIDE.md). Replays are always labelled **REPLAY** and contact nothing.

## Notes on honesty

- Stars appear only when Advent of Code accepted an answer, or when the account had already solved
  that part ("previously completed", shown dimmer).
- Nothing in the app inserts fake events, delays inference, or scripts errors.
- If something you want to show did not happen live, say so and use a labelled replay.
