"""AocClient behaviour against a mocked website (T017)."""

import httpx
import pytest

from app.aoc.client import AocAuthError, AocClient, AocNotSentError, AocUncertainError
from app.persistence.tables import SubmissionOutcome
from tests.fixtures.fake_aoc import FakeAoc, synthetic_day1


class Clock:
    def __init__(self):
        self.t = 0.0
        self.sleeps: list[float] = []

    def now(self):
        return self.t

    async def sleep(self, s):
        self.sleeps.append(s)
        self.t += s


def make(site_or_handler, tmp_path, interval=5.0, token="tok-123456"):
    clock = Clock()
    handler = site_or_handler.handler if isinstance(site_or_handler, FakeAoc) else site_or_handler
    c = AocClient(token, tmp_path, contact="ops@example.invalid", repo_url="https://example.invalid/repo",
                  min_interval_s=interval, transport=httpx.MockTransport(handler), sleep=clock.sleep, clock=clock.now)
    return c, clock


@pytest.fixture
def site():
    s = FakeAoc()
    s.puzzles[1] = synthetic_day1()
    return s


async def test_pacing_cache_and_headers(site, tmp_path):
    seen = []

    def handler(req):
        seen.append(req)
        return site.handler(req)

    c, clock = make(handler, tmp_path)
    await c.calendar(2024, refresh=True)
    await c.day_page(2024, 1)
    await c.input(2024, 1)
    await c.input(2024, 1)  # cached
    await c.day_page(2024, 1)  # cached
    assert len(seen) == 3
    assert clock.sleeps == [5.0, 5.0]  # sequential, spaced by the minimum interval
    ua = seen[0].headers["user-agent"]
    assert "agentic-puzzle-solver/" in ua and "ops@example.invalid" in ua
    assert "session=tok-123456" in seen[0].headers["cookie"]
    assert (tmp_path / "2024" / "01" / "input.txt").read_text() == site.puzzles[1].input


async def test_interval_floor(tmp_path, site):
    c, _ = make(site, tmp_path, interval=0.1)
    assert c.min_interval_s == 1.0


async def test_retry_after_and_backoff_for_get(tmp_path, site):
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "7"})
        if calls["n"] == 2:
            return httpx.Response(503)
        return site.handler(req)

    c, clock = make(handler, tmp_path)
    await c.calendar(2024, refresh=True)
    assert clock.sleeps[:2] == [7.0, 4.0] and calls["n"] == 3  # Retry-After honoured, then exponential backoff


async def test_redirects_are_not_followed(tmp_path):
    def handler(req):
        return httpx.Response(302, headers={"location": "https://evil.example/steal"})

    c, _ = make(handler, tmp_path)
    with pytest.raises(AocAuthError):
        await c.day_page(2024, 1)
    with pytest.raises(AocAuthError):
        await c.input(2024, 1)


async def test_unauthenticated_input(tmp_path, site):
    site.logged_in = False
    c, _ = make(site, tmp_path)
    st = await c.validate_session(2024)
    assert not st.logged_in


async def test_post_is_never_retried(tmp_path):
    posts = []

    def handler(req):
        posts.append(req)
        raise httpx.ReadTimeout("lost", request=req)

    c, _ = make(handler, tmp_path)
    with pytest.raises(AocUncertainError):
        await c.submit(2024, 1, 1, "18")
    assert len(posts) == 1

    def refuse(req):
        raise httpx.ConnectError("refused", request=req)

    c2, _ = make(refuse, tmp_path)
    with pytest.raises(AocNotSentError):
        await c2.submit(2024, 1, 1, "18")


async def test_submit_form_and_429(tmp_path, site):
    c, _ = make(site, tmp_path)
    r = await c.submit(2024, 1, 1, "18")
    assert r.outcome == SubmissionOutcome.CORRECT and site.posts == [(1, 1, "18")]

    def limited(req):
        return httpx.Response(429, headers={"Retry-After": "30"})

    c2, _ = make(limited, tmp_path)
    r2 = await c2.submit(2024, 1, 1, "1")
    assert r2.outcome == SubmissionOutcome.COOLDOWN and r2.wait_seconds == 30
