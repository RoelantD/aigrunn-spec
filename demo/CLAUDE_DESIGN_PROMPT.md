# Claude Design prompt — "From Spec to Stars" deck

Copy everything inside the fenced block below into Claude Design. The prompt is self-contained.
[TALK_SCRIPT.md](TALK_SCRIPT.md) holds the full spoken script. These slides only support it.

Tips:

- If Claude Design asks for references, attach two screenshots of the running app: the `/present`
  view and the dashboard with the code inspector open. The deck should look related to the app.
- Generate the deck in one go, then iterate per slide ("make S14 a cleaner state diagram").
- Export to PowerPoint or PDF as a backup, and present from the export if venue Wi-Fi is unreliable.

```text
Create a 22-slide, 16:9 conference deck for a 25-minute technical talk.

TITLE: "From Spec to Stars"
SUBTITLE: "Spec-Driven Development with an AI agent that earns real Advent of Code stars"
SPEAKER: [Your name] · [Your role / company] · [Event name, date]

AUDIENCE AND TONE
Developers and architects at a technical conference. Engineering-focused, confident, a little playful.
The talk mixes slides with live code and a live demo, so slides must be sparse: one idea per slide,
at most ~25 words of body text, big type readable from the back of a large room. No paragraphs. The
speaker tells the story; the slides anchor it.

VISUAL SYSTEM (match the live demo app, which uses this palette)
- Background: near-black navy #070B16, with very subtle radial glows (cyan top-left, violet top-right).
- Surfaces/cards: #0F162A with 1px border #1C2742, rounded corners 16px.
- Text: primary #E6EBF7, secondary #A8B3CF, muted #7F8DB0.
- Accent colors with fixed meaning, used consistently:
    Cyan   #38BDF8 = GPT-6.1 Sol (workhorse model) / "in progress"
    Violet #C4A1FF = Claude Opus 5.5 (escalation model)
    Gold   #FBBF24 = stars / verified success
    Green  #34D399 = tests passed / OK
    Red    #F87171 = failure / wrong answer
    Orange #FB923C = warnings, cooldowns, REPLAY label
- Typography: clean geometric sans (Segoe UI Variable / Inter style) for text; monospace
  (Cascadia Code / JetBrains Mono style) for code, states, file names and tags.
- Headings ~54-64pt, body ~28-32pt, code ~24pt minimum.
- Motif: a five-pointed gold star used sparingly as a reward symbol, plus thin "circuit/flow" lines
  for diagrams. Diagrams are flat, line-based, no 3D, no stock photos, no clip-art robots.
- Small footer on content slides: "From Spec to Stars" left, slide number right, muted color.

HARD CONSTRAINTS
- Do NOT imitate the Advent of Code website: no green-on-black terminal look, no ASCII-art
  Christmas tree calendar, no Advent of Code logo or typography. Our own visual identity only.
- Do NOT include any real Advent of Code puzzle text. Use only the synthetic example given on S4.
- No fabricated metrics. Use exactly the numbers provided below.
- Mark slides that the speaker will switch away from with a tiny corner tag:
  "→ CODE" (cyan) or "→ LIVE DEMO" (gold). These are cues for the presenter, keep them small.

SLIDES

S1 — Title
"From Spec to Stars" (very large), subtitle line, speaker line. A single gold star with a faint
trail, as if just earned. Dark, minimal.

S2 — "Two AIs in this talk"
Split layout, two cards.
Left card (cyan accent): "AI builds the software" — "GitHub Spec Kit · Claude Code (built it) ·
GitHub Copilot (today)".
Right card (violet accent): "AI solves the problems" — "GPT-6.1 Sol + Claude Opus 5.5 on Microsoft
Foundry · Python in Azure".
Bottom center line: "Both only work if 'correct' is defined first."

S3 — "Advent of Code in 30 seconds"
Three large stat-like tiles: "Since 2015" · "25 days · 2 parts each" · "Up to 50 ⭐ per year".
Caption: "Daily programming puzzles every December, created by Eric Wastl."

S4 — "Anatomy of a puzzle"
Four stacked or left-to-right blocks with icons:
1 "A story" — quote card: "Each line of the ledger lists two lantern readings. The drift of a line
  is the difference between them."
2 "A worked example" — monospace block:
      3 5
      10 4
      7 7
  with "→ total drift = 8" highlighted in gold.
3 "Your personal input" — "1,000+ lines · different for every player".
4 "One answer box" — a simple input field with a "Submit" button.
Footer note (small): "Synthetic example created for this talk."

S5 — "The rules that make it hard"
Four rows with icons:
🔒 "Part 2 stays hidden until Part 1 is accepted"
⏳ "Wrong answers trigger growing waits"
👤 "Every player gets a different input"
⚖️ "Only the server decides — HTTP 200 ≠ correct"
Emphasize the last row.

S6 — "Playing fair"
Calm, respectful slide. Left: "The creator discourages using AI to solve the puzzles."
Right, a checklist: "Past puzzles only (2024) · Never during a live event · Paced requests (≥ 5 s) ·
Identified traffic · Cached inputs · Never resubmit a wrong answer · No puzzle text or inputs published".

S7 — "The mission"   [→ LIVE DEMO]
Big statement: "Given adventofcode.com/2024, earn real stars. No human in the loop. No cheating."
Below, a circular loop diagram: Read → Plan → Code → Test → Run → Submit → (gold ⭐ | red ↻ back to Plan).

S8 — "Prompt-and-pray vs spec-driven"
Two-column comparison table:
Prompt-and-pray: "'Build me a solver'" · "Done = it runs" · "Assumptions hide in code"
Spec-driven: "Define 'correct', then build" · "Done = the website accepted it" ·
"Assumptions become reviewable text"
Spec-driven column highlighted.

S9 — "The Spec Kit pipeline"
Horizontal timeline of 9 steps, each a pill with its git tag beneath:
constitution (demo/01) → specify (demo/02) → clarify (demo/03) → plan (demo/04) → checklist →
tasks → analyze (demo/05) → implement (demo/06) → converge (demo/07).
Caption: "Every step is a real commit. Built with Claude Code · walked through today with GitHub Copilot."

S10 — "Constitution: the non-negotiables"   [→ CODE]
Small label "7 principles". Three large numbered cards:
I "Authentic verification — a star only after the server confirms"
II "Isolation — model code never runs on this laptop"
III "Respectful automation — paced, cached, no brute force"

S11 — "Specify: what & why, never how"   [→ CODE]
Three stat tiles: "7 user stories" · "48 requirements" · "10 success criteria".
Below, a three-step ladder graphic with increasing emphasis:
"Tests passed" (green) → "Answer computed" (cyan) → "Accepted by Advent of Code" (gold, largest).
Caption: "No frameworks or model names in the spec."

S12 — "Clarify: the questions that matter"   [→ CODE]
Five question/answer cards in a grid:
"How fast may we hit the site?" → "≥ 5 s between requests"
"A part fails — stop or move on?" → "Mark FAILED, block its Part 2, continue"
"Wrong answers per part?" → "Max 3"
"Work ahead during a cooldown?" → "No — diagnose, then wait"
"Day 25's final star?" → "Only with all 49 others"
Caption: "None of these were in the original brief."

S13 — "Plan: architecture"
Clean architecture diagram, left to right:
Browser "React dashboard" ⇄ (SSE) "FastAPI + Orchestrator" → three external boxes:
"Microsoft Foundry: GPT-6.1 Sol (cyan) · Claude Opus 5.5 (violet)",
"Azure Container Apps Dynamic Sessions — no network",
"adventofcode.com — paced & cached".
Below the orchestrator: "SQLite + event log". Label the sandbox arrow "code + input only, no secrets".

S14 — "Plan: one part, one state machine"
State diagram (monospace state names):
FETCHING → ANALYZING → GENERATING → TESTING → EXECUTING_INPUT → SUBMITTING → VERIFIED (gold)
Loop from TESTING back via REPAIRING; branch to ESCALATING (violet) back to GENERATING.
Side states: WAITING_FOR_COOLDOWN (orange), FAILED (red), BLOCKED (grey), SKIPPED (grey).
Caption: "Every box on the dashboard is one of these states."

S15 — "Analyze: bugs caught before code existed"   [→ CODE]
Stat tile "83 tasks". Two red-bordered finding cards labelled HIGH:
"An Azure outage would have blocked every remaining day"
"No guard against hard-coded answers"
Caption: "Fixed in the plan — two edits instead of two bugs."

S16 — "Implement → Converge"   [→ CODE]
Three stacked pass rows: "Pass 1 — 7 gaps" · "Pass 2 — 2 gaps" · "Pass 3 — clean ✓".
Side note card: "Live Azure check found 1 more bug no mock could catch."
Caption: "Converge checks the code against the spec, not against the diff."

S17 — "How the agent solves a part"
Five-step horizontal flow with icons:
Understand (puzzle = untrusted data) → Generate solve(input_text) → Test in sandbox (examples must
be verbatim from the puzzle) → Repair with real errors → Run & Submit.

S18 — "Two models, one budget"
Left (cyan): "GPT-6.1 Sol — workhorse · effort medium → high".
Arrow labelled "after 3 failures or a timeout".
Right (violet): "Claude Opus 5.5 — reassess, don't patch · gets a concise handover".
Bottom strip: "Every call metered: tokens · reasoning tokens · latency · cost · spend cap".

S19 — "Guardrails"
Four icon tiles:
"Sandbox with no network" · "Secrets never leave the backend" ·
"Personal input never sent to models" · "Never submit the same wrong answer twice".

S20 — "What the spec made explicit"   [→ LIVE DEMO precedes this slide]
Checklist with green checks:
Real submission defines done · Part 2 depends on Part 1 · No duplicate wrong answers ·
Cooldowns ≠ retries · Reconcile before resubmitting · Model code never runs locally ·
Replays always labelled.

S21 — "Lessons"
Four numbered statements, large:
1 "Define done outside the model."
2 "Specs are where assumptions get reviewed."
3 "Generation is cheap. Verification is the product."
4 "Be honest in the UI."

S22 — "Thank you"   [→ LIVE DEMO]
Large gold star, "Thank you", repository URL placeholder [REPO URL] with a QR-code placeholder.
Line: "GitHub Spec Kit · Claude Code · GitHub Copilot · Microsoft Foundry · Azure Container Apps".
Small footnote: "Past puzzles (2024) only. Advent of Code was created by Eric Wastl, who discourages
AI solving. Puzzle text and inputs are not redistributed."

SPEAKER NOTES
Add 1–3 short speaker-note bullets per slide summarizing the talking point. Do not put them on the
slide itself.
```
