# From Spec to Stars — talk flow and script (25 min)

**Working title:** *From Spec to Stars: Spec-Driven Development with an AI agent that earns real
Advent of Code stars*

This is the master script. It mixes three kinds of segment:

| Tag | Meaning | Screen |
|-----|---------|--------|
| **[S]** | Slide (built in Claude Design, see [CLAUDE_DESIGN_PROMPT.md](CLAUDE_DESIGN_PROMPT.md)) | Slide deck, fullscreen |
| **[C]** | Code or artifact in VS Code on `aps-walkthrough`, with Copilot Chat | VS Code, zoom 150–175 % |
| **[D]** | Live demo in the running app | Browser: dashboard tab and `/present` tab |

[DEMO_SCRIPT_25_MIN.md](DEMO_SCRIPT_25_MIN.md) has demo-only cues. Setup is in
[PRESENTER_GUIDE.md](PRESENTER_GUIDE.md).

---

## The story in one breath

> Advent of Code is a puzzle game where **only the website decides whether you are right**, and
> Part 2 stays locked until it says yes. That makes it an honest test for an AI agent. A wrong
> answer counts against you, and nothing is proven until the server accepts it. I built that agent
> with Spec-Driven Development. In the next 25 minutes the agent tries to earn stars on stage. While
> it works, I show you the specification that told it, and the AI that wrote it, what "done" means.

Three ideas the audience should leave with:

1. **Define "done" before writing code.** Here, done is "the website accepted the answer", not
   "the tests passed".
2. **A spec turns hidden assumptions into reviewable decisions** (constitution → clarify →
   analyze → converge).
3. **Agents need verification loops**: tests, repair, escalation, an external oracle, and
   honest status reporting.

---

## Screen setup (before the talk)

Use three Windows virtual desktops and switch with **Ctrl+Win+←/→**:

1. **Desktop 1 – Slides** (fullscreen deck)
2. **Desktop 2 – VS Code** on `..\aps-walkthrough`, with Copilot Chat docked right, plus a terminal
   in the dev clone for `show-checkpoint.ps1`
3. **Desktop 3 – Browser** with tab 1 = dashboard `http://127.0.0.1:5175` and tab 2 =
   `/present/<run>` in fullscreen

Keep `aps-data\.env` closed. The session cookie must never appear on screen.

---

## Act 1 · Set the scene: what problem are we solving? (0:00 – 4:30)

### 0:00 [S1] Title — *From Spec to Stars*

> "Two things are happening in this room. One AI wrote the software. A second AI is about to use
> that software to solve programming puzzles, live, with real consequences. Let's start with the
> puzzles."

### 0:30 [S2] Two kinds of AI in this talk

- Left: **AI builds the software.** Spec Kit + Claude Code during development; GitHub Copilot on
  stage today.
- Right: **AI solves the problems.** GPT-6.1 Sol and Claude Opus 5.5 on Microsoft Foundry, running
  Python in Azure.

> "Both halves only work because of the same thing: being explicit about what correct means."

### 0:50 [S3] Advent of Code in 30 seconds

- A puzzle every day in December since 2015, made by Eric Wastl.
- Each day has two parts and gives up to two ⭐.
- Developers worldwide use it to learn, compete and have fun. Many solve it in a new language each
  year.

> "Who here has done Advent of Code? … Keep your hand up if you finished all 25 days. … Right."

### 1:20 [S4] Anatomy of a puzzle

Use **our own synthetic example** here. Never put real puzzle text on a slide.

- **A story.** For example: *"Each line of the ledger lists two lantern readings. The drift of a
  line is the difference between them."*
- **A worked example**, with the answer: `3 5 / 10 4 / 7 7` → total drift **8**.
- **Your personal input**: 1,000+ lines that differ for every player.
- **One answer box.** You type a number and submit it.

> "Notice there are no unit tests and no specification of edge cases. Just a story, one example
> and a box."

### 2:00 [S5] The rules that make it hard (for an agent)

- 🔒 Part 2 stays hidden until the website accepts Part 1.
- ❌ Wrong answers trigger growing waits: one minute, then five, then more.
- 👤 Everyone gets a different input, so you can't copy an answer.
- ⚖️ **Only the server decides.** An HTTP 200 does not mean you were right.

> "For an AI agent this is a great test. The agent can't grade its own homework, and every wrong
> guess counts against it."

### 2:40 [S6] Playing fair

- The creator of Advent of Code **discourages using AI to solve the puzzles**. They are made for
  people.
- So the agent works only on **past puzzles (2024)**, for education, and never during a live event.
- It is gentle with the site:
  - requests are sequential, at least 5 seconds apart
  - it identifies itself
  - inputs are cached
  - it never resubmits a wrong answer
  - puzzle text and inputs are never published

> "I want to be upfront about this. It shaped the requirements, as you'll see."

### 3:10 [S7] The mission

> **Given `adventofcode.com/2024`, earn real stars. No human in the loop, and no cheating.**

The diagram on the slide shows the agent loop: Read → Plan → Code → Test → Run → **Submit** → ⭐ or ↻.

> "Let's start it now, so it has time to work while we talk."

### 3:30 [D1] Start the live run (≈ 60 s) — Desktop 3, dashboard tab

1. Click **New live run**. The calendar URL is `https://adventofcode.com/2024`. Set the days from
   the first unsolved day to 25.
2. Point at the toggle. *"Automatic submission. I authorize it once, for the whole run, and it is
   on the record."* Tick the box.
3. Click **Verify connections**. Four green checks: website, two models, sandbox.
   *"The sandbox has no internet. We'll come back to why."*
4. Click **Start live run** and switch to the `/present` tab.
5. Read the first events aloud: *"Loading puzzle… Analyzing requirements using GPT-6.1 Sol."*
6. Click the **25:00** talk clock.

> "It's working. Let's leave it alone and look at how it was built."

---

## Act 2 · Why specs? (4:30 – 6:00)

### 4:30 [S8] Vibe coding meets a strict oracle

| Prompt-and-pray | Spec-driven |
|-----------------|-------------|
| "Build me an Advent of Code solver" | "Define what correct means, then build" |
| Done = it runs | Done = **the website accepted it** |
| Assumptions hide in the code | Assumptions become reviewable text |

> "A quick prototype would have gotten Part 1 working and then quietly broken the things that
> matter: duplicate wrong answers, cooldowns, Part 2 that never unlocks."

### 5:10 [S9] The Spec Kit pipeline

The slide is a timeline, with each stage labelled by its git tag:

`constitution → specify → clarify → plan → checklist → tasks → analyze → implement → converge`

- Every step produced an artifact and a real git commit, tagged `demo/00` … `demo/07`.
- It was developed with **Claude Code**. Today I walk through it with **GitHub Copilot**, using the
  same artifacts.

> "Each tag is a commit from the real development. The history hasn't been tidied up afterwards.
> Let's walk it."

---

## Act 3 · Walking the spec (6:00 – 14:00)

Walk the checkpoints in order. For each one, show **one slide [S], then the real file [C]**.
Switch the walkthrough worktree with
`.\scripts\show-checkpoint.ps1 <name>` (the live app is unaffected).

### 6:00 [S10] Constitution — the non-negotiables

Seven principles. The slide shows three:

1. **Authentic verification.** A star appears only after the server confirms. No simulated
   success.
2. **Isolation.** Model-written code never runs on this laptop. Secrets never leave the backend.
3. **Respectful automation.** Paced, cached, and never brute-forcing answers.

### 6:40 [C] `show-checkpoint.ps1 constitution` → `.specify/memory/constitution.md`

- Scroll to Principle I. Highlight *"A star or 'verified' status MUST appear only after
  server-confirmed acceptance."*
- In Copilot Chat: `#file:.specify/memory/constitution.md Which principle stops the dashboard from lying?`

### 7:20 [S11] Specify — what and why, not how

- 7 user stories, 48 functional requirements, 10 success criteria.
- **No technology is named.** No React, no FastAPI, no model names.
- The three success levels: **tests passed ≠ answer computed ≠ accepted by Advent of Code**.

### 7:50 [C] `show-checkpoint.ps1 specify` → `specs/001-agentic-aoc-solver/spec.md`

- Show User Story 1 and its acceptance scenarios.
- In Copilot Chat: `#file:specs/001-agentic-aoc-solver/spec.md which requirement prevents submitting the same wrong answer twice?`
  It should land on **FR-019**.

### 8:30 [S12] Clarify — the questions that matter

Show five cards, one per decision:

- **How fast may we hit the site?** At least 5 s between requests.
- **A part fails: stop, or move on?** Mark it FAILED, block that day's Part 2, and continue.
- **How many wrong answers per part?** At most 3.
- **Work ahead during a cooldown?** No. Diagnose the current part, then wait.
- **Day 25's final star?** Claim it only if the account holds the other 49.

> "None of these were in my original brief. Any of them would have become a 2 a.m. bug on
> December 25th."

### 9:10 [C] `show-checkpoint.ps1 clarify` → the `## Clarifications` section

Point at the provenance note.

> "The agent made these decisions and wrote down that it did. Nobody pretended there was a
> stakeholder meeting. That honesty is part of the spec."

### 9:40 [D2] Peek at the live run (≈ 30 s) — Desktop 3, `/present`

Look at whatever is happening right now: a test failing and the code being repaired, a submission,
or a star. Then switch back.

> "Hold that thought."

### 10:10 [S13] Plan — architecture

The slide shows the architecture diagram, from browser to backend to the external services:

```
React dashboard → FastAPI → Orchestrator → { Foundry: GPT-6.1 Sol | Claude Opus 5.5 }
                                         → Azure Dynamic Sessions (no egress)
                                         → adventofcode.com (paced, cached)
                          → SQLite + event stream → live dashboard
```

### 10:50 [S14] Plan — the state machine

The slide shows the per-part state machine:
`FETCHING → ANALYZING → GENERATING → TESTING → (REPAIRING / ESCALATING) → EXECUTING_INPUT →
SUBMITTING → VERIFIED`. Side exits lead to `WAITING_FOR_COOLDOWN`, `FAILED`, `BLOCKED` and
`SKIPPED`.

> "Every box you see on the dashboard is one of these states. Nothing on screen is decoration."

### 11:20 [C] `show-checkpoint.ps1 plan` → `research.md`

- Open R7 and R8: two models behind **two different APIs**. GPT-6.1 Sol uses the Responses API,
  and Claude Opus 5.5 uses the Messages API in Foundry.
- Then `contracts/aoc-client.md`: the response classification table. *"HTTP 200 does not mean
  accepted."*

### 12:00 [S15] Tasks + analyze — catching bugs before code exists

- 83 tasks, grouped by user story.
- `/speckit-analyze` checked spec, plan and tasks against each other, **before any code existed**.
  It found **2 HIGH issues**:
  - an Azure outage would have marked every remaining day as BLOCKED
  - there was no guard against hard-coded answers
- Both were fixed in the plan, at the cost of two edits instead of two bugs.

### 12:40 [C] `show-checkpoint.ps1 tasks` → `analysis.md`

Show the findings table, then scroll to the coverage table.

### 13:10 [S16] Implement + converge — closing the gap

- `/speckit-implement` built the app.
- `/speckit-converge` compared the code with the spec **three times**:
  - pass 1 found **7 gaps**, including a mismatch with the API contract
  - pass 2 found **2 more**
  - pass 3 came back clean
- Live verification against Azure found one more bug, a missing package, that no mocked test could
  catch.

> "Converge asks: what does the spec promise that the code doesn't deliver yet? It's checking
> against the requirements, not against the diff."

### 13:40 [C] `show-checkpoint.ps1 implement` → `backend/app/agents/orchestrator.py`, `_submit()`

Show three lines:

1. The submission is saved as PENDING **before** it is sent.
2. A lost connection marks it **UNCERTAIN**.
3. `reconcile()` re-reads the page instead of submitting again.

> "That is clarification number one and the constitution, turned into code."

Then run `return-to-complete.ps1`.

---

## Act 4 · The agent at work (14:00 – 22:30)

### 14:00 [S17] How the agent solves one part

The slide shows the solve loop:

1. **Understand.** The puzzle goes in as untrusted data. The model returns a summary, an approach
   and examples.
2. **Generate** `solve(input_text) -> str`.
3. **Test** in the sandbox. Example inputs must appear *verbatim* in the puzzle, which stops the
   model inventing tests.
4. **Repair** with the real error, the expected value and the actual value.
5. **Run** on the personal input, then **submit**, then read the website's reply.

### 14:40 [S18] Two models, one budget

- **GPT-6.1 Sol, the workhorse.** Medium effort, rising to high.
- After 3 failures, or a timeout: **escalate to Claude Opus 5.5**. It gets a short handover
  ("here's what was tried and why it failed") and is asked to *reassess*, not patch.
- Every call is metered: tokens, reasoning tokens, latency and cost, with a spend cap.

### 15:10 [S19] Guardrails

- 🧪 The code runs in **Azure Container Apps Dynamic Sessions**, with no network. The preflight
  proves it.
- 🔑 The session cookie and credentials stay in the backend. They are never in prompts, logs or the
  browser.
- 🔒 Your personal input never goes to the model. It sees only a 5-line preview.
- 🛑 No answer is ever submitted twice. Bounds from "too high / too low" are respected, and
  cooldowns are honoured.

### 15:40 [D3] The live run — the payoff (≈ 6 min) — Desktop 3

Go to `/present` first, then the dashboard for detail.

1. **Stars.** *"This big number only counts stars the website accepted during this run. Dim stars
   were already on my account."*
2. **Activity feed.** Scroll to a sequence like *Test failed: expected 4, received 3 → Analyzing
   failure → Generating revised solution → All example tests passed.*
3. **Submit and unlock.** *Submitting candidate answer → Advent of Code accepted the answer →
   Unlocking Part 2.* *"This is the moment the spec was written for."*
4. **Code inspector** (dashboard, click a solved cell):
   - revisions r1 → r2
   - the example table: expected vs actual
   - the real-input answer
   - the sandbox session id, proof that it ran remotely
5. **Escalation**, if it happened: the purple banner *GPT-6.1 Sol → Claude Opus 5.5* and its
   reason.
6. **Metrics.** Calls, tokens including reasoning tokens, latency, cost.
7. If a cooldown or wrong answer happened, show the hourglass, or the *rejected … too high* message.

If something did not happen live, say so, then open the recorded run on the **Runs** page →
**Replay**. It shows an orange **REPLAY** banner and contacts no external services.

> "This is a replay of a run from yesterday. The live one is still going in the other tab."

### 21:40 [S20] What the spec made explicit

The slide shows a checklist of things a prototype would have missed:

- ✅ Real submission is the definition of done.
- ✅ Part 2 depends on Part 1.
- ✅ Never resubmit a wrong answer.
- ✅ Cooldowns are separate from retries.
- ✅ Reconcile before resubmitting after a crash.
- ✅ Model code never runs locally.
- ✅ Replays are always labelled.

---

## Act 5 · Close (22:30 – 25:00)

### 22:30 [S21] Lessons

1. **Define done outside the model.** Here, the website is the judge.
2. **Specs are where assumptions get reviewed**, by people and by agents.
3. **Generation is cheap; verification is the product.** Tests, repair, escalation, reconcile.
4. **Be honest in the UI.** Three success levels, labelled replays, unverified things marked
   unverified.

### 23:30 [D4] Final scoreboard (≈ 30 s) — `/present`

Read out the star count and the elapsed time.

> "I'll leave it running — or pause it safely, right… now."

### 24:00 [S22] Thank you

- Repository link, with a QR code.
- "Built with GitHub Spec Kit · Claude Code · GitHub Copilot · Microsoft Foundry · Azure Container
  Apps".
- A small honest footnote: *Past puzzles (2024) only. Advent of Code was created by Eric Wastl, who
  discourages AI solving. Puzzle text and inputs are not redistributed.*

---

## Timing summary

| Block | Time | Slides | Code | Demo |
|-------|------|--------|------|------|
| Act 1 Scene + start run | 0:00–4:30 | S1–S7 | — | D1 |
| Act 2 Why specs | 4:30–6:00 | S8–S9 | — | — |
| Act 3 Walk the spec | 6:00–14:00 | S10–S16 | 6 stops | D2 |
| Act 4 Agent at work | 14:00–22:30 | S17–S20 | — | D3 |
| Act 5 Close | 22:30–25:00 | S21–S22 | — | D4 |

If you are running behind, cut these, in this order:

1. The [C] stop at 12:40 (`analysis.md`); the slide S15 covers it.
2. Slide S14 (state machine). Mention it during D3 instead.
3. D2 (peek).

**Never cut D3.**

## Contingencies

| Situation | Move |
|-----------|------|
| No star yet by minute 15 | Show the work in progress: the feed, the code inspector, a failing test and its repair. Then use a labelled replay for "a star being earned". |
| Run paused (cooldown/outage) | *"This is the system doing the right thing."* Show the reason in the dashboard, then **Resume**. |
| Wi-Fi gone | Use replay only. Say so out loud. |
| Laptop restarted | Run `start-live-app.ps1`, open the run, then **Resume**. Explain reconciliation as you do it. |
