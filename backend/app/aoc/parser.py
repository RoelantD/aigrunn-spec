"""HTML parsing for Advent of Code pages (research.md R1-R3, R5).

All page content is untrusted data; parsing never executes or follows anything.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, NavigableString, Tag

_TITLE_RE = re.compile(r"---\s*Day\s+(\d+):\s*(.*?)\s*---")


@dataclass
class PartArticle:
    index: int  # 1-based part number
    html: str
    text: str  # model-facing rendering with verbatim code blocks
    pre_blocks: list[str]
    emphasized: list[str]


@dataclass
class DayPage:
    day: int | None
    title: str | None
    parts: list[PartArticle]
    completed_answers: dict[int, str | None] = field(default_factory=dict)
    logged_in: bool = True
    form_level: int | None = None
    form_hidden_answer: str | None = None

    @property
    def completed_parts(self) -> set[int]:
        return set(self.completed_answers)


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def is_logged_in(html: str, year: int | None = None) -> bool:
    soup = _soup(html)
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.fullmatch(r"/\d{4}/auth/login", href) or "[Log In]" in a.get_text():
            return False
    return True


def _inline(node) -> str:
    if isinstance(node, NavigableString):
        return str(node)
    if not isinstance(node, Tag):
        return ""
    inner = "".join(_inline(c) for c in node.children)
    if node.name == "code":
        return f"`{inner}`"
    if node.name == "em":
        return f"**{inner}**" if "star" not in (node.get("class") or []) else inner
    if node.name == "br":
        return "\n"
    return inner


def _render_block(node, out: list[str]) -> None:
    if isinstance(node, NavigableString):
        t = str(node).strip()
        if t:
            out.append(t + "\n\n")
        return
    if not isinstance(node, Tag):
        return
    if node.name == "h2":
        out.append("## " + node.get_text().strip() + "\n\n")
    elif node.name == "pre":
        text = node.get_text()
        out.append("```text\n" + text.rstrip("\n") + "\n```\n\n")
    elif node.name in ("ul", "ol"):
        for li in node.find_all("li", recursive=False):
            out.append("- " + _inline(li).strip() + "\n")
        out.append("\n")
    elif node.name == "p":
        out.append(_inline(node).strip() + "\n\n")
    else:
        for c in node.children:
            _render_block(c, out)


def render_article(article: Tag) -> str:
    out: list[str] = []
    for c in article.children:
        _render_block(c, out)
    return "".join(out).strip() + "\n"


def emphasized_values(article: Tag) -> list[str]:
    vals: list[str] = []
    for em in article.find_all("em"):
        t = em.get_text().strip()
        if t:
            vals.append(t)
    for code in article.find_all("code"):
        if code.find("em") is not None:
            t = code.get_text().strip()
            if t:
                vals.append(t)
    return vals


def parse_day_page(html: str) -> DayPage:
    soup = _soup(html)
    articles = soup.select("article.day-desc")
    parts: list[PartArticle] = []
    day = title = None
    for i, art in enumerate(articles, start=1):
        if i == 1:
            h2 = art.find("h2")
            if h2:
                m = _TITLE_RE.search(h2.get_text())
                if m:
                    day, title = int(m.group(1)), m.group(2)
        parts.append(
            PartArticle(
                index=i,
                html=str(art),
                text=render_article(art),
                pre_blocks=[pre.get_text() for pre in art.find_all("pre")],
                emphasized=emphasized_values(art),
            )
        )
    completed: dict[int, str | None] = {}
    n = 0
    for p in soup.select("main p"):
        if p.get_text().strip().startswith("Your puzzle answer was"):
            n += 1
            code = p.find("code")
            completed[n] = code.get_text().strip() if code else None
    text = soup.get_text(" ")
    if "Both parts of this puzzle are complete" in text:
        for k in (1, 2):
            completed.setdefault(k, None)
    elif "The first half of this puzzle is complete" in text:
        completed.setdefault(1, None)

    form_level = form_hidden_answer = None
    form = soup.find("form", attrs={"method": re.compile("post", re.I)})
    if form is not None:
        lvl = form.find("input", attrs={"name": "level"})
        if lvl is not None and str(lvl.get("value", "")).isdigit():
            form_level = int(lvl["value"])
        ans = form.find("input", attrs={"name": "answer"})
        if ans is not None and (ans.get("type") or "").lower() == "hidden":
            form_hidden_answer = str(ans.get("value", ""))
    return DayPage(
        day=day,
        title=title,
        parts=parts,
        completed_answers=completed,
        logged_in=is_logged_in(html),
        form_level=form_level,
        form_hidden_answer=form_hidden_answer,
    )


def parse_calendar_stars(html: str) -> dict[int, int]:
    """Day -> stars (0, 1, 2) from the year calendar classes."""
    soup = _soup(html)
    stars: dict[int, int] = {}
    for a in soup.find_all("a"):
        classes = a.get("class") or []
        day = None
        for c in classes:
            m = re.fullmatch(r"calendar-day(\d+)", c)
            if m:
                day = int(m.group(1))
        if day is None:
            continue
        if "calendar-verycomplete" in classes:
            stars[day] = 2
        elif "calendar-complete" in classes:
            stars[day] = 1
        else:
            stars[day] = 0
    return stars


def main_article_text(html: str) -> str:
    soup = _soup(html)
    node = soup.select_one("main article") or soup.find("article") or soup.find("main") or soup
    return " ".join(node.get_text(" ").split())
