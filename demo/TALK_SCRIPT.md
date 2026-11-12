# Intent Before Code — talk flow and script (25 min)

**Working title:** *Intent Before Code: Spec-Driven Development, explained by an agent that earns
Advent of Code stars*

**What this talk is about:** Spec-Driven Development (SDD), meaning how intent, context and
verification are structured when AI agents write the software. It ends with where this is heading:
Hypervelocity Engineering (HVE).

**What it is not about:** how the solver works. The Advent of Code agent is only the **running
example**. Every SDD concept is shown with a real artifact from building it. The live solver gets
about 2 minutes in total, as quiet proof that the process produced something real.

Segment tags:

| Tag | Meaning | Screen |
|-----|---------|--------|
| **[S]** | Slide (see [CLAUDE_DESIGN_PROMPT.md](CLAUDE_DESIGN_PROMPT.md)) | Deck, fullscreen |
| **[C]** | Real artifact in VS Code on `aps-walkthrough`, often via Copilot Chat | VS Code, zoom 150–175 % |
| **[D]** | Glance at the running solver | Browser `/present` |

---

## The story in one breath

> AI agents made writing code cheap. They didn't make *knowing what to build* cheap. Spec-Driven
> Development moves the effort to where it now matters: intent, decisions and verification, written
> down as artifacts that people and agents can both work from. I'll show every step with one real
> project, an agent that solves Advent of Code puzzles, built spec-first with GitHub Spec Kit.
> Then we'll look at where this is going next.

Three takeaways:

1. **Specs are context engineering with a review step.** They are durable, versioned context that
   any agent can use, and that people can approve.
2. **Move the decisions left.** Clarify and analyze catch in text what would otherwise become bugs in
   code. Converge checks the code against the intent, not against the diff.
3. **Define "done" outside the model.** Every phase needs evidence, not confidence.

---

## Screen setup

- **Three virtual desktops**, switched with Ctrl+Win+←/→: (1) Slides, (2) VS Code on
  `..\aps-walkthrough` with Copilot Chat plus a terminal in the dev clone, (3) Browser on `/present`.
- **Before the talk**, `show-checkpoint.ps1 00-start` and `start-live-app.ps1`. Have a run
  *configured* but not started. Keep `aps-data\.env` closed.

---

## Act 1 · The problem and the running example (0:00 – 4:00)

### 0:00 [S1] Title — *Intent Before Code*

> "Raise your hand if an AI agent has written code for you this month. … Keep it up if that code
> did exactly what you meant the first time. … That gap is what this talk is about."

### 0:40 [S2] Code got cheap. Intent didn't.

The slide is a contrast. Left: *"Generating code: seconds."* Right: *"Knowing what to build, what
done means, what must never happen: still hard."* Bottom: *"Prompt → code → 'looks right' → ship →
surprise."*

> "With vibe coding, the knowledge lives in a chat window that is gone tomorrow. The agent guesses
> at everything you didn't say."

### 1:30 [S3] Our running example: an agent that earns Advent of Code stars

Keep this short. It is only context for the examples:

- Advent of Code has daily programming puzzles. Each has two parts, and each part earns a ⭐.
- **Only the website decides** whether you are right. Part 2 stays locked until Part 1 is accepted.
  Wrong answers cost waiting time.
- The goal: *given `adventofcode.com/2024`, earn real stars with no human in the loop.*

> "I picked this because it's unforgiving. The agent can't grade its own work. That makes it a good
> test of whether we specified the right things."

### 2:20 [S4] Playing fair

- The creator of Advent of Code discourages AI solving. So: **past puzzles only**, for education.
- The bot paces its requests, caches inputs, never brute-forces answers, and never publishes puzzle
  text.

> "This wasn't a footnote. It became a requirement in the spec. You'll see it again."

### 2:50 [D1] Start the solver, then leave it alone (≈ 30 s)

On Desktop 3, click **Start live run** (automatic submission already authorized), switch to
`/present` and click the talk clock.

> "It's going to run in the background while we talk. We'll check on it at the end. Now, how did
> we build it?"

### 3:20 [S5] Two ways to build this

| Prompt-and-pray | Spec-driven |
|-----------------|-------------|
| "Build me an Advent of Code solver" | Write down intent, decisions and "done", then build |
| Context lives in a chat | Context lives in versioned artifacts |
| Done = it runs | Done = **the website accepted the answer** |

> "A prototype gets Part 1 working. Then it quietly resubmits wrong answers, ignores cooldowns, and
> never unlocks Part 2. None of that is a coding problem. It's a specification problem."

---

## Act 2 · What Spec-Driven Development is (4:00 – 6:00)

### 4:00 [S6] The idea in one line

> **The specification is the source of truth. Code is its output.**

Three supporting points:

- **Intent is separated from implementation**: the *what and why* first, then the *how*.
- **Artifacts beat chat history.** They are reviewable, versioned, and usable by any agent.
- **Every step can be checked** against the step before it.

### 4:50 [S7] The Spec Kit flow

*(Optional, 30 s: switch to VS Code on `00-start` and show the ASCII title page, an empty repo with only
an intent. Then `-Next` to `01-install` and its `NEXT_STEP.md`, which holds the constitution prompt.)*

The slide is the pipeline, with each stage marked by its git tag:
`constitution → specify → clarify → plan → checklist → tasks → analyze → implement → converge`

- Each step is a command that turns one artifact into the next.
- Every step in this project is a real commit, tagged `demo/00` … `demo/07`.
- The project was **built with Claude Code** and is **walked through today with GitHub Copilot**,
  using the same artifacts.

> "Let's walk it. For each step I'll give you the concept, then show you what it actually produced."

---

## Act 3 · The concepts, one artifact at a time (6:00 – 17:00)

Pattern for each step: **[S] concept slide (≈ 40 s) → [C] the real artifact (≈ 60 s)**.

How each [C] stop works, cooking-show style:

1. You are on the previous step branch. Open `NEXT_STEP.md` and paste its prompt into Copilot Chat,
   **without sending it**.
2. Run `.\scripts\show-checkpoint.ps1 <next-step>` and say: *"this is what that prompt produced."*

Nothing is generated live. See [CHECKPOINTS.md](CHECKPOINTS.md). The solver keeps running.

### 6:00 [S8] Constitution = the rules every later step must obey

- **Concept:** principles that hold for the whole project, not for one feature. Later steps are
  checked against them as gates.
- **In our project:** 7 principles. Two of them:
  - *"A star appears only after the server confirms."*
  - *"Model-generated code never runs on this laptop."*

### 6:40 [C] `show-checkpoint.ps1 02-constitution` → `.specify/memory/constitution.md`

Highlight Principle I, then ask Copilot Chat:
`#file:.specify/memory/constitution.md Which principle would stop the dashboard from showing fake progress?`

> "This is the cheapest guardrail you will ever write. It's one sentence, and every later step is
> checked against it."

### 7:40 [S9] Specify = intent without implementation

- **Concept:** user stories, requirements you can test, measurable success criteria. **No tech
  stack.**
- **In our project:** 7 user stories, 48 requirements, 10 success criteria.
- The key move is **defining done**: *tests passed ≠ answer computed ≠ accepted by Advent of Code*.

### 8:20 [C] `show-checkpoint.ps1 03-specify` → `spec.md`

Show User Story 1 with its Given/When/Then scenarios. Then ask Copilot:
`#file:specs/001-agentic-aoc-solver/spec.md which requirement prevents submitting the same wrong answer twice?`
It should land on FR-019.

> "No React, no model names. That's on purpose: the spec has to outlive those choices."

### 9:10 [S10] Clarify = surface ambiguity before it becomes code

- **Concept:** a structured pass that looks for the decisions nobody made yet, asks about them, and
  writes the answers back into the spec.
- **In our project:** five decisions that weren't in the brief: request pacing, what happens when a
  part fails, at most 3 wrong answers, behaviour during a cooldown, Day 25.

> "Each of these would have been a bug in production. Here, each one is a single line of text."

### 9:50 [C] `show-checkpoint.ps1 04-clarify` → `## Clarifications`

Point at the provenance note: *the agent answered these itself, and says so*.

> "Be honest about who decided what. A spec that fakes a stakeholder sign-off is worse than no spec."

### 10:30 [S11] Plan = the *how*, grounded in research

- **Concept:** architecture, data model and contracts, plus **research** so the agent works from
  today's reality, not from its training data.
- **In our project:**
  - research found that the two models use **two different APIs**: the Responses API and the Claude
    Messages API
  - contracts define the website client's behaviour: *HTTP 200 ≠ accepted*
  - a Constitution Check table acts as a gate

### 11:10 [C] `show-checkpoint.ps1 05-plan` → `research.md` (R7/R8), then `contracts/aoc-client.md`

> "Research is context engineering at work. The model isn't guessing APIs. It reads what was
> verified and written down."

### 11:50 [S12] Tasks + analyze = decomposition and a consistency check

- **Concept:** break the plan into ordered, traceable tasks grouped by user story. Then check spec,
  plan and tasks against each other **before any code exists**.
- **In our project:** 83 tasks. Analyze found **2 HIGH issues**:
  - an outage would have cascaded into every remaining day
  - there was no guard against hard-coded answers
- Both were fixed with two text edits.

### 12:30 [C] `show-checkpoint.ps1 07-analyze` → `analysis.md`

Show the findings table and the coverage table, which maps each requirement to its tasks.

> "This is shift-left at its cheapest. The bug was a sentence, and fixing it was an edit."

### 13:10 [S13] Implement + converge = check the code against the intent

- **Concept:** implementation follows the tasks. **Converge** then asks *what does the spec promise
  that the code doesn't deliver yet?* and turns each gap into a new task.
- **In our project:** converge needed three passes. Pass 1 found 7 gaps (one contradicted a
  contract), pass 2 found 2, and pass 3 came back clean.

### 13:50 [C] `show-checkpoint.ps1 09-converge` → `tasks.md` Phase 11–12, then `traceability.md`

Pick one row: **FR-021** (reconcile before resubmitting) → `orchestrator.reconcile` → its test.

> "Every requirement points to code and to a test. That's what 'the spec is the source of truth'
> means in practice."

### 14:40 [S14] It's all context engineering

- Constitution, spec, plan and tasks are **curated, layered context**, loaded at the right moment
  for the right task.
- Because the artifacts are files, the work **doesn't depend on any one agent**. Claude Code built
  it, and Copilot reads the same files today.

### 15:10 [C] Copilot, at the final checkpoint (≈ 60 s)

In Copilot Chat, show the Spec Kit skills in `.github/skills/` (`/speckit-*`). Then ask:
`Using the spec, plan and tasks: if I wanted to add support for 2025, which artifacts change first?`

> "Same artifacts, different agent, and it still understands the project. That's the payoff of
> putting context in files instead of in a chat."

### 16:10 [S15] What it cost, and what still slipped through

Show both sides honestly:

- **Overhead:** a fair amount of text before the first line of code. It's worth it for anything
  you'll maintain or hand to agents. It's too much for a throwaway script.
- **Gates are only as good as the people using them.** The checklist gate was overridden, and the
  commit message says so.
- **Specs don't replace reality.** Every mocked test passed, yet the first real Azure call found a
  missing dependency. You still need evidence from the real system.

> "SDD doesn't make you right. It makes your assumptions visible, and that's how you find the
> wrong ones early."

---

## Act 4 · Where this is going: HVE (17:00 – 20:30)

### 17:00 [S16] The evolution

The slide is a timeline:

**Prompt engineering** (say it better) → **Context engineering** (give it the right information) →
**Spec-Driven Development** (put intent and decisions into versioned artifacts) →
**Hypervelocity Engineering** (govern the whole agentic lifecycle).

> "SDD taught us to stop treating the chat as the source of truth. It gave us a structure for
> context engineering, one feature at a time. The next step is to make that structure the way the
> whole team delivers."

### 17:50 [S17] Hypervelocity Engineering (HVE)

- Microsoft's practice for delivering software with AI agents under explicit governance. Its
  open-source reference implementation is **HVE Core** (`github.com/microsoft/hve-core`), built for
  GitHub Copilot.
- The guiding line: **"AI carries the rules, humans keep the judgment."**
- **The RPI loop:** Research → Plan → Implement → Review, with follow-ups routed back to the phase
  that owns them.
- **Decision ownership per phase** (user-owned, agent-owned, user-retained), and **autonomy as a
  separate setting**.
- **Durable tracking files** let a new session pick up without replaying the chat.
- **Organisational standards** are encoded as instructions and skills: security, architecture and
  compliance reviews.

### 18:50 [S18] From SDD to HVE

The slide maps the two side by side:

| | Spec-Driven Development | Hypervelocity Engineering |
|-|------------------------|---------------------------|
| Scope | One feature: spec → code | The whole delivery lifecycle |
| Artifacts | constitution · spec · plan · tasks | research · plan · implementation · review records |
| Humans | review artifacts at gates | own named decisions per phase; autonomy is set explicitly |
| Standards | the project constitution | organisation-wide instructions and skills |
| Shared idea | **Durable artifacts over chat. Evidence over confidence.** | |

> "You'll recognise our project in that table. The constitution and clarify step became decision
> ownership. Converge and analyze became Review. The authorization checkbox before a real submission
> is exactly 'humans keep the judgment'. SDD isn't replaced. It becomes one part of a governed
> lifecycle."

Honest caveat, said briefly:

> "HVE Core is young and moving fast. Its own advocates say to pin a version and measure your own
> baseline. Treat it as patterns to learn from, not a product to adopt blindly."

---

## Act 5 · Takeaways and close (20:30 – 25:00)

### 20:30 [S19] Takeaways

1. **Specs are context engineering with a review step.**
2. **Move decisions left**: constitution, clarify, analyze. Bugs are cheapest as sentences.
3. **Define done outside the model.** Converge against intent, and verify against reality.
4. **Next: govern the lifecycle**, with decision ownership and durable artifacts (HVE).

### 22:00 [D2] Back to the running example (≈ 60–90 s)

Switch to `/present`.

> "While we were talking about specs, the agent was working."

Read out the verified star count. Point at one line from the feed, such as a test failure followed
by a repair, or *Advent of Code accepted the answer*.

> "Every star there exists because Principle I said a star appears only after the server confirms.
> That rule came from the constitution, not from a clever prompt."

If nothing was earned yet, say so plainly. Show the work in progress, or a run labelled **REPLAY**.
Never present a replay as live.

### 23:30 [S20] Thank you

- Repository link and QR code. A pointer to `demo/CHECKPOINTS.md` so people can walk the tags
  themselves.
- Further reading: `github.com/github/spec-kit`, `github.com/microsoft/hve-core`.
- Footnote: past puzzles (2024) only; Advent of Code was created by Eric Wastl, who discourages AI
  solving.

Pause the run, or leave it running.

---

## Timing summary

| Block | Time | Slides | Code stops | Demo |
|-------|------|--------|-----------|------|
| Act 1 Problem + example | 0:00–4:00 | S1–S5 | — | D1 (30 s) |
| Act 2 What SDD is | 4:00–6:00 | S6–S7 | — | — |
| Act 3 Concepts | 6:00–17:00 | S8–S15 | 7 | — |
| Act 4 HVE | 17:00–20:30 | S16–S18 | — | — |
| Act 5 Close | 20:30–25:00 | S19–S20 | — | D2 (≈ 75 s) |

If you are running late, cut these, in this order:

1. The [C] stop at 12:30 (`analysis.md`); the slide covers it.
2. The [C] stop at 11:10 (`research.md`).
3. Shorten S15 to a single sentence.

**Never cut Act 4 or the takeaways.**

## Contingencies

| Situation | Move |
|-----------|------|
| Solver paused, or no stars yet at 22:00 | *"This is the system refusing to claim what it hasn't earned."* Show the reason or the work in progress. |
| Wi-Fi gone | Skip D2, or use a run clearly labelled REPLAY. The talk doesn't depend on the demo. |
| Copilot slow or unavailable | Open the file directly and read the highlighted line yourself. |

## Sources for the HVE section

- `github.com/microsoft/hve-core`: HVE Core repository and docs (`microsoft.github.io/hve-core`)
- PnP blog, *"Who keeps the judgment when AI carries the rules? Microsoft HVE Core in practice"*
  (`pnp.github.io/blog/post/microsoft-hve-core-governed-agentic-engineering/`)

Check the HVE slides against the current HVE Core docs shortly before the talk; the project changes
quickly.
