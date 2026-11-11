# Phase 0 Research: Agentic Advent of Code Solver

**Date**: 2026-11-11. Research was done by two parallel research agents dispatched during
`/speckit-plan` (one for the website, one for Azure services), plus local environment checks.
Sources are listed per topic. Items marked **UNVERIFIED** were not confirmed against live
services or official docs and must be validated by the opt-in integration tests.

## R1. Advent of Code routes and HTTP behavior

- **Decision**: Use `GET /{year}` (calendar: per-day star classes), `GET /{year}/day/{d}` (puzzle
  articles), `GET /{year}/day/{d}/input` (personal input, `text/plain`) and
  `POST /{year}/day/{d}/answer` (form-encoded `level`, `answer`). Send the session as
  `Cookie: session=<token>`. Never follow redirects automatically.
- **Rationale**: Verified live without logging in (2026-11-11): input returns HTTP 400 with "Puzzle
  inputs differ by user" when unauthenticated; puzzle page returns 200 with only Part 1 and a login
  prompt. The calendar marks days with `calendar-complete` (one star) and `calendar-verycomplete`
  (two stars) classes (from the aoc-cli client source). Both reference clients (aocd, aoc-cli)
  use form-encoded POSTs.
- **Alternatives**: Using the `/leaderboard/self` stats page for completion state — rejected as the
  primary source because the calendar provides the same per-day star info in one request; kept as a
  fallback for the Day 25 49-star check only if the calendar is ambiguous.
- Sources: adventofcode.com (2024, /about, /day/1, /day/25, /day/1/input); github.com/wimglenn/
  advent-of-code-data (`aocd/models.py`, tests); github.com/scarvalhojr/aoc-cli.

## R2. Authentication and session validation

- **Decision**: Operator supplies the `session` cookie value obtained from a normal browser login
  via the `AOC_SESSION` environment variable (or ignored `.env`). Validate by fetching the year
  calendar and checking that the `[Log In]` link (`href="/{year}/auth/login"`) is absent.
- **Rationale**: Login is OAuth-only through GitHub/Google/Twitter/Reddit; there is no API token
  and no supported third-party login flow. The `[Log In]` check is what both reference clients use.
  The logged-in `<div class="user">` markup is **UNVERIFIED**, so we do not rely on it.
- **Alternatives**: Implementing the OAuth flow — rejected (not supported for third parties,
  constitution forbids).

## R3. Puzzle HTML structure and example extraction

- **Decision**: Parse `article.day-desc` elements (one per accessible part). Title from
  `<h2>--- Day N: Title ---</h2>`. Completed parts from paragraphs starting
  "Your puzzle answer was" with the answer in `<code>`. Convert article HTML to a
  whitespace-faithful text representation (keeping `<pre><code>` blocks verbatim and marking
  `<em>` emphasis) for the model. Example extraction is done by the model in the analysis step, and
  every extracted example input is **accepted only if it occurs verbatim in one of the article's
  `<pre><code>` blocks**; expected outputs are accepted only if the value appears in the article
  text (typically `<code><em>X</em></code>`). Otherwise the example is kept as
  "no reliable expectation" (executed for crash detection only).
- **Rationale**: The "last `<code><em>` is the answer" heuristic is a convention, not a guarantee;
  model extraction handles prose-described examples, while the verbatim checks prevent hallucinated
  tests.
- **Alternatives**: Pure heuristic parsing (aocd-style) — rejected as primary because it fails on
  multi-example puzzles; retained as unit-tested helpers (`pre_blocks`, `emphasized_codes`) used
  for verification.

## R4. Answer response classification

- **Decision**: Normalize whitespace of `main article` text, then classify in this order:
  login page → AUTH_FAILED; "That's the right answer" → CORRECT; "Did you already complete it" →
  ALREADY_COMPLETED; "You gave an answer too recently" + `You have (?:(\d+)m )?(\d+)s left to wait`
  → COOLDOWN; "That's not the right answer" → INCORRECT / TOO_HIGH ("your answer is too high") /
  TOO_LOW ("your answer is too low"), with the follow-up wait parsed from
  `please wait (one|\d+) minutes?`; "You've finished every puzzle" → CORRECT (Day 25 claim);
  "You don't seem to be solving the right level" without completion → LOCKED; otherwise
  UNEXPECTED. HTTP status alone is never treated as acceptance.
- **Rationale**: Strings verified against aocd tests and advent-of-code-api fixtures. Wait after a
  wrong answer grows (1 min → 5 min after 4 wrong → 10 min after 7).
- **Alternatives**: none viable.

## R5. Day 25

- **Decision**: After Day 25 Part 1 is accepted, re-read the calendar; if the account has exactly
  49 stars from other days plus Day 25 Part 1, POST `level=2` with the hidden `answer` value parsed
  from the page's form (fallback `0`; aocd uses `done`); expect "You've finished every puzzle".
  Otherwise mark Part 2 SKIPPED.
- **Rationale**: Day 25 Part 2 is a button that works only with all other stars. The exact hidden
  value is **UNVERIFIED**; reading it from the form avoids guessing.

## R6. Respectful automation policy

- **Decision**: One AoC HTTP client per process, guarded by an async lock, with a minimum interval
  between requests (default 5 s, floor 1 s), User-Agent
  `agentic-puzzle-solver/<version> (+<repo URL>; contact: <AOC_CONTACT>)`, permanent local caching of
  inputs and pages (page re-fetched only after an acceptance changes it), `Retry-After` honored,
  exponential backoff (2, 4, 8 … max 120 s, 5 tries) for 5xx/network errors on GETs only. POSTs are
  never retried automatically; uncertain outcomes are reconciled via GET of the day page.
- **Rationale**: The community automation guidance (r/adventofcode wiki — fetched via mirrors,
  wording **UNVERIFIED**) asks for an identifying User-Agent, throttled requests and cached inputs;
  the "15 minutes" figure applies to private leaderboard JSON only. The puzzle author discourages
  using AI to solve puzzles and asks that puzzle text and inputs not be redistributed — documented
  in README; runtime data lives outside Git.
- **Alternatives**: aocd-style burst backoff (0.16 s) — rejected as unnecessarily aggressive for a
  demo where model latency dominates anyway.

## R7. Workhorse model: GPT-6.1 Sol via Foundry Responses API

- **Decision**: `POST {FOUNDRY_OPENAI_BASE_URL}/responses` where base is
  `https://<resource>.openai.azure.com/openai/v1` (v1 API, no `api-version`). Body:
  `model` = deployment name (configurable, default `gpt-6.1-sol`), `instructions`, `input`,
  `reasoning: {effort}`, `max_output_tokens`, `text.format` = JSON schema (strict). Read
  `output_text` (or concatenate `output[].content[].text` of `message` items),
  `usage.input_tokens`, `usage.output_tokens`, `usage.output_tokens_details.reasoning_tokens`,
  and `incomplete_details`. Do not send `temperature`/`top_p`. Auth: Entra token for scope
  `https://ai.azure.com/.default` (role Cognitive Services OpenAI User), or `api-key` header.
- **Rationale**: Microsoft Learn documents gpt-6.1-sol (version 2026-09-29) with Responses API,
  structured outputs and reasoning effort. Which effort values it accepts is **UNVERIFIED** —
  effort levels are configurable and we use `medium` → `high` → `xhigh`.
- **Implementation choice**: call the REST API with `httpx` rather than the `openai` SDK. This keeps
  request shapes explicit, lets both providers share one HTTP/retry/metrics layer, and makes tests
  straightforward with mocked transports.
- **Alternatives**: `openai` SDK with `base_url` + token provider (documented, viable); Chat
  Completions (rejected: Responses is the recommended API for reasoning models).

## R8. Escalation model: Claude Opus 5.5 via Claude in Microsoft Foundry

- **Decision**: `POST https://<resource>.services.ai.azure.com/anthropic/v1/messages` with headers
  `anthropic-version: 2023-06-01` and either `Authorization: Bearer <Entra token, scope
  https://ai.azure.com/.default>` or `x-api-key`. Body: `model` (deployment name, default
  `claude-opus-5-5`), `max_tokens`, `system`, `messages`, `thinking: {type: "adaptive"}`,
  `output_config: {effort: "high"}`. Structured output is requested via
  `output_config.format` JSON schema; if a deployment rejects it, the adapter falls back to an
  instruction to answer in a fenced JSON block (parsed tolerantly). Do not send `temperature`,
  `top_p`, `top_k` or `budget_tokens`. Check `stop_reason == "refusal"`. Thinking blocks are
  ignored (never displayed); usage from `usage.input_tokens/output_tokens`.
- **Rationale**: Microsoft Learn + Azure-Samples/claude. Opus 5.5 defaults to `medium` effort, so
  effort is set explicitly. Support for `output_config.format` on the Foundry endpoint is
  **UNVERIFIED**, hence the fallback.
- **Alternatives**: `anthropic` SDK `AnthropicFoundry` (exists; viable) — not used for the same
  reasons as R7.

## R9. Sandbox: Azure Container Apps Dynamic Sessions (PythonLTS code interpreter)

- **Decision**: `POST {POOL_ENDPOINT}/executions?api-version=2025-10-02-preview&identifier=<id>`
  with flat body `{codeInputType: "Inline", executionType: "Synchronous", code, timeoutInSeconds}`;
  read `status`, `result.stdout`, `result.stderr`, `result.executionResult`,
  `result.executionTimeInMilliseconds`, `error`. Token scope `https://dynamicsessions.io/.default`,
  role "Azure ContainerApps Session Executor". Pool: `containerType: PythonLTS`,
  `sessionNetworkConfiguration.status: EgressDisabled`, Timed lifecycle (cooldown 300 s). A fresh
  random identifier per execution (`aps-<uuid4 hex>`), so no state leaks between runs. The
  generated program and input are embedded into a harness (input as base64 literal) that calls
  `solve(input_text)` per test case and prints one sentinel-delimited JSON result line; harness
  truncates outputs (64 KiB) and reports exceptions with tracebacks. Max per-execution timeout is
  220 s; we default to 30 s with configurable maximum ≤ 220 s.
- **Rationale**: Official REST reference. Whether the body must be wrapped in `properties` is
  **UNVERIFIED** (docs disagree); the adapter sends the flat body and retries once with the wrapped
  form on HTTP 400, recording which variant worked.
- **Alternatives**: File upload of input to `/mnt/data` (rejected: extra round-trip; inputs are
  small); custom container sessions (future, behind the `CodeExecutionService` interface).
- **Isolation verification**: the preflight runs a probe that attempts an outbound connection and
  expects failure.

## R10. Backend stack

- **Decision**: Python 3.12 (uv-managed), FastAPI, Pydantic v2 + pydantic-settings, SQLAlchemy 2
  (async) on SQLite via aiosqlite, httpx (async), azure-identity (async `DefaultAzureCredential`),
  BeautifulSoup4 for HTML parsing, structlog (JSON logs with a redaction processor),
  sse-starlette for Server-Sent Events. Tests: pytest, pytest-asyncio, respx (HTTP mocking).
  Lint: ruff.
- **Rationale**: Matches the requested stack; async end-to-end lets the orchestrator, SSE and HTTP
  clients share one event loop in a single process (the operator's laptop).
- **Alternatives**: background worker process / queue (rejected: unnecessary for one operator).

## R11. Frontend stack

- **Decision**: React + TypeScript + Vite, Tailwind CSS, Radix UI primitives (accessible dialogs,
  switches, tabs, tooltips) styled in shadcn-style local components, lucide-react icons,
  prism-react-renderer for Python highlighting, native `EventSource` for SSE with `Last-Event-ID`
  resume. Tests: Vitest + Testing Library.
- **Rationale**: Accessible primitives without a heavy design system; everything themable for a
  dark, large-type presentation view. No Advent of Code design elements are copied (own palette,
  own typography, no ASCII-art calendar).

## R12. Infrastructure

- **Decision**: Bicep + `azure.yaml` (azd) provisioning: AIServices account (`kind: AIServices`),
  deployments `gpt-6.1-sol` (format OpenAI, version 2026-09-29, GlobalStandard) and
  `claude-opus-5-5` (format Anthropic, GlobalStandard, `modelProviderData` parameters supplied by
  the operator since they accept Marketplace terms), session pool
  (`Microsoft.App/sessionPools@2026-07-01`, PythonLTS, EgressDisabled), and role assignments for
  the operator principal. The app itself runs locally. Claude deployment regions/eligibility are
  **UNVERIFIED** and documented as operator prerequisites.
- **Current subscription state (read-only check)**: no gpt-6.x deployment, no Claude deployment and
  no session pool exist yet — real-service integration tests are blocked until provisioned.

## R13. Spec Kit + GitHub Copilot

- **Decision**: The repository is initialized with Spec Kit 1.4.0 (`claude` integration, PowerShell
  scripts). The Copilot integration is added with `specify integration install copilot` without
  changing the default integration; documented and tested in `demo/PRESENTER_GUIDE.md`.
- **Rationale**: `specify integration` manages multiple installed integrations
  (`.specify/integration.json`, `installed_integrations`).
