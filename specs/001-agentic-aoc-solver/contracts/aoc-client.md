# Advent of Code Client Contract

`AocClient` is the only component allowed to contact `https://adventofcode.com`.

```python
class AocClient:
    async def validate_session(year) -> SessionStatus          # GET /{year}; logged_in = no "/{year}/auth/login" link
    async def calendar(year, *, refresh=False) -> dict[int, int] # day -> stars (0..2), cached in AccountState
    async def day_page(year, day, *, refresh=False) -> DayPage  # cached page.html; refresh only after acceptance/reconcile
    async def input(year, day) -> str                          # cached input.txt forever
    async def submit(year, day, level, answer) -> SubmitResult # POST, never retried automatically
```

`DayPage`: `title`, `parts: list[PartArticle(index, html, text)]`, `completed_answers: dict[part, str|None]`,
`completed_parts: set[int]`, `form_level: int|None`, `form_hidden_answer: str|None`.

`SubmitResult`: `outcome` (see data-model Submission), `message` (normalised article text, max 1000
chars), `wait_seconds: int|None`.

## Behavioral rules

1. Requests are serialised by one `asyncio.Lock`; consecutive requests are ≥ `min_interval_s`
   apart (default 5 s, floor 1 s).
2. Headers: `User-Agent: agentic-puzzle-solver/<ver> (+<repo>; contact: <AOC_CONTACT>)`,
   `Cookie: session=<secret>` (never logged).
3. `follow_redirects=False`. A 3xx is treated as AUTH_FAILED for authenticated endpoints.
4. 429/503 honor `Retry-After` (seconds or HTTP date); 5xx/network errors on GET: exponential
   backoff 2^n s (cap 120 s, 5 tries). POST: no automatic retry; network error after send →
   `UNCERTAIN`.
5. Classification precedence (whitespace-normalised `main article` text):
   login prompt → AUTH_FAILED; "That's the right answer" → CORRECT;
   "You've finished every puzzle" → CORRECT; "Did you already complete it" → ALREADY_COMPLETED;
   "You gave an answer too recently" → COOLDOWN (`You have (?:(\d+)m )?(\d+)s left to wait`);
   "That's not the right answer" → TOO_HIGH ("answer is too high") / TOO_LOW ("answer is too low")
   / INCORRECT, `wait_seconds` from `please wait (one|\d+) minutes?`;
   "You don't seem to be solving the right level" → LOCKED; else UNEXPECTED.
6. Input with HTTP 400 "Puzzle inputs differ by user" → AUTH_FAILED; 404 → LOCKED.
7. Part 2 description is only requested via `day_page(refresh=True)` after a CORRECT /
   ALREADY_COMPLETED for Part 1, or when the calendar shows ≥1 star.
