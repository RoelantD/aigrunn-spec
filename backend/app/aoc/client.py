"""The only component allowed to contact adventofcode.com (contracts/aoc-client.md).

Rules: sequential (one lock), paced (min interval), identified (User-Agent with contact),
cached (inputs forever, pages until a state change), redirects never followed, POSTs never
retried automatically.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx

from app.aoc.parser import DayPage, is_logged_in, parse_calendar_stars, parse_day_page
from app.aoc.responses import SubmitResult, classify_submission
from app.config import APP_VERSION
from app.logsetup import get_logger
from app.persistence.tables import SubmissionOutcome
from app.security import AOC_ORIGIN

log = get_logger("aoc")

GET_MAX_TRIES = 5
BACKOFF_CAP_S = 120.0


class AocError(Exception):
    pass


class AocAuthError(AocError):
    pass


class AocLockedError(AocError):
    pass


class AocNotSentError(AocError):
    """The POST never left the machine (connection could not be established)."""


class AocUncertainError(AocError):
    """The POST may have reached the server but no response was received."""


@dataclass
class SessionStatus:
    logged_in: bool
    detail: str


FetchListener = Callable[[str, bool], Awaitable[None]]


def _retry_after_seconds(resp: httpx.Response) -> float | None:
    ra = resp.headers.get("Retry-After")
    if not ra:
        return None
    try:
        return max(0.0, float(ra))
    except ValueError:
        try:
            dt = parsedate_to_datetime(ra)
            return max(0.0, (dt - datetime.now(UTC)).total_seconds())
        except (TypeError, ValueError):
            return None


class AocClient:
    def __init__(
        self,
        session_token: str | None,
        cache_dir: Path,
        *,
        contact: str = "",
        repo_url: str = "",
        min_interval_s: float = 5.0,
        min_interval_floor_s: float = 1.0,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._token = session_token
        self.cache_dir = cache_dir
        self.min_interval_s = max(min_interval_s, min_interval_floor_s)
        self._floor = min_interval_floor_s
        self._lock = asyncio.Lock()
        self._last_request: float | None = None
        self._sleep = sleep
        self._clock = clock
        ua = f"agentic-puzzle-solver/{APP_VERSION} (+{repo_url or 'local'}; contact: {contact or 'unset'})"
        self.user_agent = ua
        headers = {"User-Agent": ua}
        cookies = {"session": session_token} if session_token else None
        self._http = httpx.AsyncClient(
            base_url=AOC_ORIGIN,
            headers=headers,
            cookies=cookies,
            follow_redirects=False,
            timeout=httpx.Timeout(30.0, connect=10.0),
            transport=transport,
        )
        self.request_log: list[tuple[float, str, str]] = []  # (t, method, path) for tests/metrics
        self.on_fetch: FetchListener | None = None

    def set_min_interval(self, seconds: float) -> None:
        self.min_interval_s = max(seconds, self._floor)

    @property
    def has_session(self) -> bool:
        return bool(self._token)

    async def aclose(self) -> None:
        await self._http.aclose()

    # ------------------------------------------------------------------ low level
    async def _pace(self) -> None:
        if self._last_request is not None:
            wait = self._last_request + self.min_interval_s - self._clock()
            if wait > 0:
                await self._sleep(wait)

    async def _send(self, method: str, path: str, **kw) -> httpx.Response:
        assert path.startswith("/") and "//" not in path and ".." not in path
        await self._pace()
        try:
            return await self._http.request(method, path, **kw)
        finally:
            self._last_request = self._clock()
            self.request_log.append((self._last_request, method, path))

    async def _get(self, path: str) -> httpx.Response:
        async with self._lock:
            delay = 2.0
            for attempt in range(1, GET_MAX_TRIES + 1):
                try:
                    resp = await self._send("GET", path)
                except httpx.TransportError as exc:
                    if attempt == GET_MAX_TRIES:
                        raise AocError(f"network error fetching {path}: {type(exc).__name__}") from exc
                    log.warning("aoc.get.retry", path=path, error=type(exc).__name__, retry_in=delay)
                    await self._sleep(delay)
                    delay = min(delay * 2, BACKOFF_CAP_S)
                    continue
                if resp.status_code == 429 or resp.status_code >= 500:
                    if attempt == GET_MAX_TRIES:
                        raise AocError(f"server error {resp.status_code} fetching {path}")
                    wait = _retry_after_seconds(resp) or delay
                    log.warning("aoc.get.retry", path=path, status=resp.status_code, retry_in=wait)
                    await self._sleep(wait)
                    delay = min(delay * 2, BACKOFF_CAP_S)
                    continue
                return resp
            raise AocError("unreachable")  # pragma: no cover

    async def _notify(self, what: str, cached: bool) -> None:
        if self.on_fetch:
            await self.on_fetch(what, cached)

    # ------------------------------------------------------------------ cache
    def _day_dir(self, year: int, day: int) -> Path:
        d = self.cache_dir / str(int(year)) / f"{int(day):02d}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ------------------------------------------------------------------ public API
    async def validate_session(self, year: int) -> SessionStatus:
        if not self._token:
            return SessionStatus(False, "AOC_SESSION is not configured")
        resp = await self._get(f"/{int(year)}")
        await self._notify("calendar", False)
        if resp.status_code != 200:
            return SessionStatus(False, f"calendar returned HTTP {resp.status_code}")
        if not is_logged_in(resp.text, year):
            return SessionStatus(False, "session cookie is not logged in (expired or invalid)")
        (self.cache_dir / str(year)).mkdir(parents=True, exist_ok=True)
        (self.cache_dir / str(year) / "calendar.html").write_text(resp.text, encoding="utf-8")
        return SessionStatus(True, "logged in")

    async def calendar(self, year: int, *, refresh: bool = False) -> dict[int, int]:
        path = self.cache_dir / str(int(year)) / "calendar.html"
        if path.exists() and not refresh:
            await self._notify("calendar", True)
            return parse_calendar_stars(path.read_text(encoding="utf-8"))
        resp = await self._get(f"/{int(year)}")
        await self._notify("calendar", False)
        if resp.status_code != 200:
            raise AocError(f"calendar returned HTTP {resp.status_code}")
        if self._token and not is_logged_in(resp.text, year):
            raise AocAuthError("session is not logged in")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(resp.text, encoding="utf-8")
        return parse_calendar_stars(resp.text)

    async def day_page(self, year: int, day: int, *, refresh: bool = False) -> DayPage:
        path = self._day_dir(year, day) / "page.html"
        if path.exists() and not refresh:
            await self._notify("page", True)
            return parse_day_page(path.read_text(encoding="utf-8"))
        resp = await self._get(f"/{int(year)}/day/{int(day)}")
        await self._notify("page", False)
        if resp.status_code == 404:
            raise AocLockedError(f"day {day} is not available")
        if resp.status_code in (301, 302, 303, 307, 308):
            raise AocAuthError("redirected while fetching puzzle page")
        if resp.status_code != 200:
            raise AocError(f"puzzle page returned HTTP {resp.status_code}")
        page = parse_day_page(resp.text)
        if self._token and not page.logged_in:
            raise AocAuthError("session is not logged in")
        path.write_text(resp.text, encoding="utf-8")
        (path.parent / "meta.json").write_text(
            json.dumps({"fetched_at": datetime.now(UTC).isoformat(), "parts": len(page.parts)}), encoding="utf-8"
        )
        return page

    async def input(self, year: int, day: int) -> str:
        path = self._day_dir(year, day) / "input.txt"
        if path.exists():
            await self._notify("input", True)
            return path.read_text(encoding="utf-8")
        resp = await self._get(f"/{int(year)}/day/{int(day)}/input")
        await self._notify("input", False)
        if resp.status_code == 400 or resp.status_code in (301, 302, 303, 307, 308):
            raise AocAuthError("input requires a valid session")
        if resp.status_code == 404:
            raise AocLockedError(f"input for day {day} is not available")
        if resp.status_code != 200:
            raise AocError(f"input returned HTTP {resp.status_code}")
        path.write_text(resp.text, encoding="utf-8")
        return resp.text

    async def submit(self, year: int, day: int, level: int, answer: str) -> SubmitResult:
        """POST an answer exactly once. Never retried here (constitution III, FR-021)."""
        if level not in (1, 2):
            raise ValueError("level must be 1 or 2")
        async with self._lock:
            try:
                resp = await self._send(
                    "POST",
                    f"/{int(year)}/day/{int(day)}/answer",
                    data={"level": str(level), "answer": answer},
                )
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                raise AocNotSentError(type(exc).__name__) from exc
            except httpx.TransportError as exc:
                raise AocUncertainError(type(exc).__name__) from exc
        if resp.status_code == 429:
            return SubmitResult(SubmissionOutcome.COOLDOWN, "HTTP 429 Too Many Requests",
                                int(_retry_after_seconds(resp) or 60))
        return classify_submission(resp.text, resp.status_code)
