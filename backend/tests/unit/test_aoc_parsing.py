"""Parser and response-classification tests (T015, T016)."""

import pytest

from app.aoc.parser import is_logged_in, parse_calendar_stars, parse_day_page
from app.aoc.responses import classify_submission
from app.persistence.tables import SubmissionOutcome
from tests.fixtures.fake_aoc import FakeAoc, synthetic_day1


def _site(done=None):
    s = FakeAoc()
    s.puzzles[1] = synthetic_day1()
    s.puzzles[25] = synthetic_day1()
    s.completed = done or {}
    return s


def test_day_page_part1_only():
    page = parse_day_page(_site().day_html(1))
    assert page.day == 1 and page.title == "Lantern Ledger"
    assert len(page.parts) == 1 and page.completed_answers == {}
    assert page.parts[0].pre_blocks == ["3 5\n10 4\n7 7\n"]
    assert "8" in page.parts[0].emphasized
    assert "```text\n3 5\n10 4\n7 7\n```" in page.parts[0].text
    assert "**8**" in page.parts[0].text or "`**8**`" in page.parts[0].text
    assert page.form_level == 1 and page.form_hidden_answer is None


def test_day_page_both_parts_complete():
    page = parse_day_page(_site({1: {1, 2}}).day_html(1))
    assert len(page.parts) == 2
    assert page.completed_answers == {1: "18", 2: "287"}


def test_day_page_part1_complete_shows_part2_and_form():
    page = parse_day_page(_site({1: {1}}).day_html(1))
    assert len(page.parts) == 2 and page.completed_parts == {1}
    assert page.form_level == 2


def test_day25_hidden_answer():
    page = parse_day_page(_site({25: {1}}).day_html(25))
    assert page.form_level == 2 and page.form_hidden_answer == "0"


def test_login_detection():
    s = _site()
    assert is_logged_in(s.calendar_html())
    s.logged_in = False
    assert not is_logged_in(s.calendar_html())


def test_calendar_stars():
    stars = parse_calendar_stars(_site({1: {1, 2}, 3: {1}}).calendar_html())
    assert stars[1] == 2 and stars[3] == 1 and stars[2] == 0 and len(stars) == 25


def _resp(text, logged_in=True):
    s = FakeAoc()
    s.logged_in = logged_in
    return s.answer_html(text)


@pytest.mark.parametrize(("text", "outcome", "wait"), [
    ("That's the right answer! You are one gold star closer. [Continue to Part Two]", "CORRECT", None),
    ("That's not the right answer; your answer is too high. If you're stuck... Please wait one minute before "
     "trying again. [Return to Day 1]", "TOO_HIGH", 60),
    ("That's not the right answer; your answer is too low. Because you have guessed incorrectly 4 times on this "
     "puzzle, please wait 5 minutes before trying again.", "TOO_LOW", 300),
    ("That's not the right answer. If you're stuck, make sure you're using the full input data.", "INCORRECT", None),
    ("You gave an answer too recently; you have to wait after submitting an answer before trying again.  "
     "You have 3m 30s left to wait. [Return to Day 1]", "COOLDOWN", 210),
    ("You gave an answer too recently; you have to wait after submitting an answer before trying again. "
     "You have 34s left to wait.", "COOLDOWN", 34),
    ("You don't seem to be solving the right level.  Did you already complete it? [Return to Day 1]",
     "ALREADY_COMPLETED", None),
    ("You don't seem to be solving the right level. [Return to Day 1]", "LOCKED", None),
    ("Congratulations! You've finished every puzzle in Advent of Code 2024!", "CORRECT", None),
    ("Something entirely new.", "UNEXPECTED", None),
])
def test_classification(text, outcome, wait):
    r = classify_submission(_resp(text))
    assert r.outcome == SubmissionOutcome(outcome)
    assert r.wait_seconds == wait


def test_classification_auth_failure():
    assert classify_submission(_resp("anything", logged_in=False)).outcome == SubmissionOutcome.AUTH_FAILED
    assert classify_submission("", 302).outcome == SubmissionOutcome.AUTH_FAILED


def test_http_200_alone_is_not_acceptance():
    assert classify_submission("<html><main><article><p>OK</p></article></main></html>", 200).outcome \
        == SubmissionOutcome.UNEXPECTED
