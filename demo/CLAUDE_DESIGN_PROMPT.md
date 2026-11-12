# Claude Design prompt — "Intent Before Code" deck

Copy everything inside the fenced block below into Claude Design. It is self-contained. The spoken
script is in [TALK_SCRIPT.md](TALK_SCRIPT.md); the slides only support it.

Tips:

- Attach one screenshot of the running app's `/present` view. The deck should look related to it,
  but the deck is about the method, not the app.
- Generate the deck in one go, then iterate per slide (for example, "make S16 a cleaner horizontal
  timeline").
- Export to PowerPoint or PDF as a backup.
- Re-check the HVE slides (S16–S18) against `github.com/microsoft/hve-core` shortly before the talk.

```text
Create a 20-slide, 16:9 conference deck for a 25-minute talk.

TITLE: "Intent Before Code"
SUBTITLE: "Spec-Driven Development, explained by an agent that earns Advent of Code stars"
SPEAKER: [Your name] · [Role / company] · [Event, date]

WHAT THE TALK IS ABOUT
The subject is Spec-Driven Development (SDD) with AI coding agents (GitHub Spec Kit), and the
evolution toward Hypervelocity Engineering (HVE). An Advent of Code puzzle-solving agent is only the
running example that illustrates each concept; it must never dominate the visuals. Concept first,
example second, on every slide.

AUDIENCE AND TONE
Developers, architects and engineering leads. Thoughtful, practical, honest about trade-offs. The
speaker switches to live code (VS Code + GitHub Copilot) often, so slides are sparse: one idea per
slide, at most ~30 words of body text, large type for a big room, no paragraphs.

VISUAL SYSTEM
- Background near-black navy #070B16 with very subtle radial glows (cyan top-left, violet top-right).
- Cards #0F162A, 1px border #1C2742, 16px radius.
- Text #E6EBF7 primary, #A8B3CF secondary, #7F8DB0 muted.
- Accent meanings (consistent across the deck):
    Cyan   #38BDF8 = intent / specification artifacts
    Violet #C4A1FF = agents / automation
    Gold   #FBBF24 = verified outcome ("done", stars)
    Green  #34D399 = checks passing
    Red    #F87171 = problems caught
    Orange #FB923C = caveats / honesty notes
- Typography: clean geometric sans (Inter / Segoe UI Variable style) for text; monospace (JetBrains Mono /
  Cascadia Code style) for file names, commands and git tags. Headings ~54-64pt, body ~28-32pt.
- Recurring motif: a "document card" icon for artifacts (constitution.md, spec.md, plan.md,
  tasks.md) and a small gold star used only for verified outcomes.
- Diagrams are flat and line-based. No 3D, no stock photos, no clip-art robots.
- Footer on content slides: "Intent Before Code" left, slide number right, muted.

HARD CONSTRAINTS
- Do not imitate the Advent of Code website: no green-on-black terminal style, no ASCII Christmas
  tree, no Advent of Code logo. No real puzzle text.
- Use only the numbers given below. Do not invent statistics.
- Put a tiny corner cue on slides where the speaker switches screens: "→ CODE" (cyan) or
  "→ LIVE" (gold). Keep the cue small.
- Add 1-3 speaker-note bullets per slide (in notes, not on the slide).

SLIDES

S1 — Title
"Intent Before Code" (very large), subtitle, speaker line. Visual: a document card on the left with
a thin line flowing right into a code bracket "{ }", ending in a small gold star.

S2 — "Code got cheap. Intent didn't."
Two-sided contrast. Left, small and fast: "Generating code: seconds". Right, large: "Knowing what to
build, what 'done' means, what must never happen". Bottom strip: "prompt → code → 'looks right' →
ship → surprise".

S3 — "Our running example"
Small label "Running example". Three compact points with icons:
"Daily programming puzzles · two parts each · a ⭐ per part"
"Only the website decides — Part 2 unlocks after Part 1 is accepted"
"Goal: given adventofcode.com/2024, earn real stars, no human in the loop"
Keep the visual light: one small star and a lock icon.

S4 — "Playing fair"
Short, respectful. "The creator discourages AI solving → past puzzles (2024) only, for education."
Small checklist: "Paced requests · cached inputs · no brute force · no puzzle text published".
Caption in orange: "This became a requirement, not a footnote."

S5 — "Two ways to build it"   [→ LIVE]
Comparison table, spec-driven column highlighted:
Prompt-and-pray: "'Build me a solver'" · "Context lives in a chat" · "Done = it runs"
Spec-driven: "Write intent, decisions and 'done' first" · "Context lives in versioned artifacts" ·
"Done = the website accepted it" (gold)

S6 — "The idea"
One large statement: "The specification is the source of truth. Code is its output."
Three small supporting chips: "Intent ≠ implementation" · "Artifacts > chat history" ·
"Every step checkable against the last".

S7 — "The Spec Kit flow"
Horizontal pipeline of document cards, each with its git tag below:
constitution (demo/01) → specify (demo/02) → clarify (demo/03) → plan (demo/04) → checklist →
tasks → analyze (demo/05) → implement (demo/06) → converge (demo/07).
Caption: "Built with Claude Code · walked through today with GitHub Copilot · same artifacts."

S8 — "Constitution: the rules every step obeys"   [→ CODE]
Concept line: "Project-wide principles; later steps are gated against them."
Example card (label "In our project · 7 principles"):
"A star appears only after the server confirms."
"Model-generated code never runs on this laptop."

S9 — "Specify: intent without implementation"   [→ CODE]
Concept line: "User stories, testable requirements, measurable success — no tech stack."
Three stat tiles: "7 user stories" · "48 requirements" · "10 success criteria".
Highlighted ladder defining done: "Tests passed" (green) → "Answer computed" (cyan) →
"Accepted by Advent of Code" (gold, largest).

S10 — "Clarify: find the decisions nobody made"   [→ CODE]
Concept line: "Surface ambiguity, decide, write it back into the spec."
Five small cards ("In our project"): "Request pacing ≥ 5 s" · "A part fails → move on" ·
"Max 3 wrong answers" · "Cooldown → wait, don't skip ahead" · "Day 25's final star rule".
Caption: "Each would have been a production bug. Here, each is one line of text."

S11 — "Plan: the how, grounded in research"   [→ CODE]
Concept line: "Architecture, data model and contracts — plus research so agents use today's facts,
not training data."
Example: two model cards side by side, "Responses API" (cyan) and "Messages API" (violet), labelled
"Two models, two different APIs — found in research". A small contract chip: "HTTP 200 ≠ accepted".
A small badge: "Constitution Check gate".

S12 — "Tasks + Analyze: decompose, then cross-check"   [→ CODE]
Concept line: "Ordered, traceable tasks — checked against spec and plan before any code exists."
Stat tile "83 tasks". Two red-bordered cards labelled HIGH:
"An outage would cascade into every remaining day"
"No guard against hard-coded answers"
Caption: "Fixed with two edits. Bugs are cheapest as sentences."

S13 — "Implement + Converge: check the code against the intent"   [→ CODE]
Concept line: "Converge asks: what does the spec promise that the code doesn't deliver yet?"
Three stacked rows: "Pass 1 — 7 gaps" · "Pass 2 — 2 gaps" · "Pass 3 — clean ✓".
Small traceability chain: "FR-021 → reconcile() → test".

S14 — "It's all context engineering"   [→ CODE]
Layered diagram: stacked cards constitution → spec → plan → tasks feeding into two agent icons
labelled "Claude Code (built it)" and "GitHub Copilot (today)".
Caption: "Curated, versioned context. The agent can change; the intent stays."

S15 — "What it cost, and what still slipped through"
Honest two-column slide with orange accents.
Costs: "Upfront text before the first line of code" · "Too heavy for throwaway scripts".
Slipped through: "A gate was overridden (and recorded)" · "Mocked tests passed; the first real
Azure call found a missing dependency".
Bottom line: "SDD doesn't make you right. It makes your assumptions visible."

S16 — "The evolution"
Horizontal timeline with four stages, each slightly larger than the last:
"Prompt engineering — say it better" → "Context engineering — give it the right information" →
"Spec-Driven Development — intent & decisions as versioned artifacts" →
"Hypervelocity Engineering — govern the whole agentic lifecycle" (highlighted).

S17 — "Hypervelocity Engineering (HVE)"
Header quote, large: "AI carries the rules, humans keep the judgment."
A circular loop diagram: Research → Plan → Implement → Review, with a "Follow-up" arrow routing back
to the owning phase.
Four small chips around it: "Decision ownership per phase" · "Autonomy set explicitly" ·
"Durable tracking files across sessions" · "Org standards as instructions & skills".
Small source line: "HVE Core · github.com/microsoft/hve-core (open source, GitHub Copilot)".

S18 — "From SDD to HVE"
Two-column comparison table:
Scope: "One feature: spec → code" | "The whole delivery lifecycle"
Artifacts: "constitution · spec · plan · tasks" | "research · plan · implementation · review records"
Humans: "Review artifacts at gates" | "Own named decisions; autonomy set explicitly"
Standards: "Project constitution" | "Organisation-wide instructions & skills"
Full-width bottom row in gold: "Shared idea: durable artifacts over chat. Evidence over confidence."
Small orange caveat: "Young and fast-moving — pin a version, measure your own baseline."

S19 — "Takeaways"   [→ LIVE]
Four numbered statements, large:
1 "Specs are context engineering with a review step."
2 "Move decisions left — bugs are cheapest as sentences."
3 "Define done outside the model — and verify against reality."
4 "Next: govern the lifecycle (HVE)."

S20 — "Thank you"
Large "Thank you", one gold star. Placeholders: [REPO URL] + QR code placeholder.
"Walk the checkpoints yourself: demo/CHECKPOINTS.md"
Further reading: "github.com/github/spec-kit · github.com/microsoft/hve-core"
Small footnote: "Past puzzles (2024) only. Advent of Code was created by Eric Wastl, who discourages
AI solving."
```
