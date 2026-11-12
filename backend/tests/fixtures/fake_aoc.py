"""A stateful fake Advent of Code website for tests (synthetic puzzles only; no real content)."""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from urllib.parse import parse_qs

import httpx


@dataclass
class FakePuzzle:
    title: str
    part1_html: str
    part2_html: str
    input: str
    answers: dict[int, str]


@dataclass
class FakeAoc:
    year: int = 2024
    puzzles: dict[int, FakePuzzle] = field(default_factory=dict)
    completed: dict[int, set[int]] = field(default_factory=dict)
    logged_in: bool = True
    wrong_wait_text: str = ""  # e.g. "Please wait one minute before trying again."
    cooldown_responses: int = 0  # next N POSTs answer "too recently"
    cooldown_seconds: int = 1
    drop_next_post_after_processing: bool = False  # simulate connection lost after the server processed it
    unexpected_next_post: bool = False
    requests: list[tuple[str, str]] = field(default_factory=list)
    posts: list[tuple[int, int, str]] = field(default_factory=list)

    # ------------------------------------------------------------------ html
    def _nav(self) -> str:
        if self.logged_in:
            return '<header><div class="user">Synthetic Tester <span class="star-count">0*</span></div></header>'
        return f'<header><a href="/{self.year}/auth/login">[Log In]</a></header>'

    def calendar_html(self) -> str:
        links = []
        for d in range(1, 26):
            n = len(self.completed.get(d, set()))
            cls = f"calendar-day{d}" + (" calendar-verycomplete" if n >= 2 else " calendar-complete" if n == 1 else "")
            links.append(f'<a aria-label="Day {d}" href="/{self.year}/day/{d}" class="{cls}">Day {d}</a>')
        return f"<html><body>{self._nav()}<main><pre class=\"calendar\">{''.join(links)}</pre></main></body></html>"

    def day_html(self, day: int) -> str:
        pz = self.puzzles[day]
        done = self.completed.get(day, set())
        body = [f'<article class="day-desc"><h2>--- Day {day}: {html.escape(pz.title)} ---</h2>{pz.part1_html}</article>']
        if 1 in done:
            body.append(f"<p>Your puzzle answer was <code>{html.escape(pz.answers[1])}</code>.</p>")
            if day != 25:
                body.append(f'<article class="day-desc"><h2 id="part2">--- Part Two ---</h2>{pz.part2_html}</article>')
            if 2 in done:
                if day != 25:
                    body.append(f"<p>Your puzzle answer was <code>{html.escape(pz.answers[2])}</code>.</p>")
                body.append("<p class=\"day-success\">Both parts of this puzzle are complete! They provide two gold "
                            "stars: **</p>")
            else:
                if day == 25:
                    body.append('<form method="post" action="25/answer"><input type="hidden" name="level" value="2"/>'
                                '<input type="hidden" name="answer" value="0"/></form>')
                else:
                    body.append(f'<form method="post" action="{day}/answer"><input type="hidden" name="level" '
                                f'value="2"/><input type="text" name="answer"/></form>')
                body.append("<p>The first half of this puzzle is complete! It provides one gold star: *</p>")
        else:
            body.append(f'<form method="post" action="{day}/answer"><input type="hidden" name="level" value="1"/>'
                        f'<input type="text" name="answer"/></form>')
        return f"<html><body>{self._nav()}<main>{''.join(body)}</main></body></html>"

    def answer_html(self, text: str) -> str:
        return f"<html><body>{self._nav()}<main><article><p>{text}</p></article></main></body></html>"

    # ------------------------------------------------------------------ handler
    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.requests.append((request.method, path))
        cookie = request.headers.get("cookie", "")
        authed = "session=" in cookie and self.logged_in
        parts = [p for p in path.split("/") if p]
        if request.method == "GET" and parts == [str(self.year)]:
            return httpx.Response(200, text=self.calendar_html())
        if len(parts) >= 3 and parts[1] == "day":
            day = int(parts[2])
            if day not in self.puzzles:
                return httpx.Response(404, text="Not found")
            if request.method == "GET" and len(parts) == 3:
                return httpx.Response(200, text=self.day_html(day))
            if request.method == "GET" and parts[3:] == ["input"]:
                if not authed:
                    return httpx.Response(400, text="Puzzle inputs differ by user.  Please log in to get your puzzle input.")
                return httpx.Response(200, text=self.puzzles[day].input)
            if request.method == "POST" and parts[3:] == ["answer"]:
                return self._answer(day, request)
        return httpx.Response(404, text="Not found")

    def _answer(self, day: int, request: httpx.Request) -> httpx.Response:
        form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
        level, answer = int(form.get("level", "0")), form.get("answer", "")
        self.posts.append((day, level, answer))
        if not self.logged_in:
            return httpx.Response(302, headers={"location": f"/{self.year}/auth/login"})
        if self.unexpected_next_post:
            self.unexpected_next_post = False
            return httpx.Response(200, text=self.answer_html("Something odd happened."))
        if self.cooldown_responses > 0:
            self.cooldown_responses -= 1
            return httpx.Response(200, text=self.answer_html(
                "You gave an answer too recently; you have to wait after submitting an answer before trying again. "
                f"You have {self.cooldown_seconds}s left to wait. [Return to Day {day}]"))
        done = self.completed.setdefault(day, set())
        if level in done:
            return httpx.Response(200, text=self.answer_html(
                "You don't seem to be solving the right level. Did you already complete it? "
                f"[Return to Day {day}]"))
        if level == 2 and 1 not in done:
            return httpx.Response(200, text=self.answer_html(
                f"You don't seem to be solving the right level. [Return to Day {day}]"))
        expected = self.puzzles[day].answers[level]
        if answer.strip() == expected:
            done.add(level)
            text = ("That's the right answer! You are <span class=\"day-success\">one gold star</span> closer. "
                    "[Continue to Part Two]")
            resp = httpx.Response(200, text=self.answer_html(text))
            if self.drop_next_post_after_processing:
                self.drop_next_post_after_processing = False
                raise httpx.ReadError("connection reset after server processed request", request=request)
            return resp
        hint = ""
        try:
            hint = "; your answer is too high" if int(answer) > int(expected) else "; your answer is too low"
        except ValueError:
            pass
        text = (f"That's not the right answer{hint}. If you're stuck, make sure you're using the full input data. "
                f"{self.wrong_wait_text} (You guessed <span style=\"white-space:nowrap;\"><code>{html.escape(answer)}"
                f"</code>.)</span> [Return to Day {day}]")
        return httpx.Response(200, text=self.answer_html(text))

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handler)


def synthetic_day1() -> FakePuzzle:
    return FakePuzzle(
        title="Lantern Ledger",
        part1_html=(
            "<p>Each line of the ledger lists two lantern readings. The <em>drift</em> of a line is the absolute "
            "difference between them.</p><p>For example:</p><pre><code>3 5\n10 4\n7 7\n</code></pre>"
            "<p>The drifts are 2, 6 and 0, so the total drift is <code><em>8</em></code>.</p>"
            "<p>What is the total drift of your ledger?</p>"
        ),
        part2_html=(
            "<p>Now multiply the readings on each line and add the products.</p>"
            "<p>In the example, the products are 15, 40 and 49, for a total of <code><em>104</em></code>.</p>"
            "<p>What is the sum of products?</p>"
        ),
        input="1 4\n9 2\n5 5\n12 20\n",
        answers={1: "18", 2: "287"},
    )


def synthetic_day2() -> FakePuzzle:
    return FakePuzzle(
        title="Moss Grid",
        part1_html=(
            "<p>Count the moss tiles (<code>#</code>) in the grid.</p><pre><code>#.#\n.#.\n...\n</code></pre>"
            "<p>This grid contains <code><em>3</em></code> moss tiles.</p><p>How many moss tiles are there?</p>"
        ),
        part2_html=(
            "<p>Count moss tiles that have at least one moss tile directly above, below, left or right.</p>"
            "<pre><code>##.\n.#.\n..#\n</code></pre><p>Here <code><em>3</em></code> tiles qualify.</p>"
        ),
        input="#..#\n##..\n....\n.###\n",
        answers={1: "7", 2: "6"},
    )
