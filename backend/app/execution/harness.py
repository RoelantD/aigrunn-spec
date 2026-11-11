"""Harness protocol (contracts/code-execution.md).

`build_harness` produces Python source that is executed ONLY inside the remote sandbox. The backend
never executes generated code; it only builds this string and decodes the result marker.
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass

MARKER_START = "@@APS_RESULT@@"
MARKER_END = "@@END@@"
OUTPUT_LIMIT = 65536

_TEMPLATE = r'''
import base64 as _b64, json as _json, time as _time, traceback as _tb, io as _io, contextlib as _cl, sys as _sys
_sys.setrecursionlimit(20000)
_SRC = _b64.b64decode("{src}").decode("utf-8")
_CASES = _json.loads(_b64.b64decode("{cases}").decode("utf-8"))
_LIMIT = {limit}

def _aps_err(e):
    lines = _tb.format_exc().splitlines(True)[-20:]
    return (type(e).__name__ + ": " + str(e))[:2000] + "\n" + "".join(lines)[-4000:]

def _aps_run():
    buf = _io.StringIO()
    ns = {{"__name__": "solution"}}
    try:
        with _cl.redirect_stdout(buf):
            exec(compile(_SRC, "solution.py", "exec"), ns)
    except (Exception, SystemExit) as e:
        return {{"load_error": _aps_err(e), "results": [], "stdout": buf.getvalue()[-_LIMIT:]}}
    solve = ns.get("solve")
    if not callable(solve):
        return {{"load_error": "solve(input_text) is not defined", "results": [], "stdout": buf.getvalue()[-_LIMIT:]}}
    results = []
    for i, case in enumerate(_CASES):
        t0 = _time.perf_counter()
        try:
            with _cl.redirect_stdout(buf):
                out = solve(case)
            out = "" if out is None else str(out)
            results.append({{"index": i, "output": out[:_LIMIT], "error": None,
                             "duration_ms": int((_time.perf_counter() - t0) * 1000)}})
        except (Exception, SystemExit) as e:
            results.append({{"index": i, "output": None, "error": _aps_err(e),
                             "duration_ms": int((_time.perf_counter() - t0) * 1000)}})
    return {{"load_error": None, "results": results, "stdout": buf.getvalue()[-_LIMIT:]}}

_aps_result = _aps_run()
print("{start}" + _b64.b64encode(_json.dumps(_aps_result).encode("utf-8")).decode("ascii") + "{end}")
'''


def _b64(s: str) -> str:
    return base64.b64encode(s.encode("utf-8")).decode("ascii")


def build_harness(code: str, cases: list[str]) -> str:
    return _TEMPLATE.format(
        src=_b64(code), cases=_b64(json.dumps(cases)), limit=OUTPUT_LIMIT, start=MARKER_START, end=MARKER_END
    )


@dataclass
class CaseResult:
    index: int
    output: str | None
    error: str | None
    duration_ms: int


@dataclass
class HarnessResult:
    load_error: str | None
    results: list[CaseResult]
    program_stdout: str


_MARKER_RE = re.compile(re.escape(MARKER_START) + r"([A-Za-z0-9+/=]+)" + re.escape(MARKER_END))


def decode_harness_output(stdout: str) -> HarnessResult | None:
    m = _MARKER_RE.search(stdout or "")
    if not m:
        return None
    payload = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
    return HarnessResult(
        load_error=payload.get("load_error"),
        results=[CaseResult(**r) for r in payload.get("results", [])],
        program_stdout=payload.get("stdout", ""),
    )


def strip_marker(stdout: str) -> str:
    return _MARKER_RE.sub("", stdout or "").strip()
