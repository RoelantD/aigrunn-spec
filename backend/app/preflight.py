"""Connection checks shared by the API and the preflight CLI (FR-005, FR-046).

None of these checks submit answers or request locked puzzle parts.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass

from app.models.base import ModelInfraError, ModelOutputError, ModelRequest
from app.services import Services

PING_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["reply"],
    "properties": {"reply": {"type": "string"}},
}

SANDBOX_SOLVE = "def solve(input_text):\n    return str(sum(int(x) for x in input_text.split()))\n"

EGRESS_PROBE = """
import socket
results = []
for host, port in (("1.1.1.1", 443), ("adventofcode.com", 443)):
    try:
        s = socket.create_connection((host, port), timeout=4)
        s.close()
        results.append(f"{host}:allowed")
    except Exception as e:
        results.append(f"{host}:blocked({type(e).__name__})")
print("EGRESS:" + ",".join(results))
"""


@dataclass
class CheckResult:
    name: str
    status: str  # pass | fail | skipped
    detail: str
    latency_ms: int = 0

    def dict(self) -> dict:
        return asdict(self)


async def check_aoc(svc: Services, year: int = 2024) -> CheckResult:
    t0 = time.monotonic()
    if not svc.aoc.has_session:
        return CheckResult("aoc", "fail", "AOC_SESSION is not configured")
    if not svc.settings.aoc_contact:
        contact_note = " (warning: AOC_CONTACT is empty; set it for the User-Agent)"
    else:
        contact_note = ""
    try:
        st = await svc.aoc.validate_session(year)
    except Exception as exc:  # noqa: BLE001
        return CheckResult("aoc", "fail", f"{type(exc).__name__}: {exc}", int((time.monotonic() - t0) * 1000))
    if not st.logged_in:
        return CheckResult("aoc", "fail", st.detail, int((time.monotonic() - t0) * 1000))
    stars = await svc.aoc.calendar(year)
    await svc.store.set_stars(year, stars)
    total = sum(stars.values())
    unsolved = [d for d in range(1, 26) if stars.get(d, 0) < 2]
    return CheckResult("aoc", "pass", f"logged in; {total} stars in {year}; days with unsolved parts: "
                       f"{unsolved[:10]}{'…' if len(unsolved) > 10 else ''}{contact_note}",
                       int((time.monotonic() - t0) * 1000))


async def check_model(svc: Services, key: str) -> CheckResult:
    if not svc.router.has(key):
        return CheckResult(key, "skipped", "not configured")
    p = svc.router.get(key)
    req = ModelRequest(system="You are a connectivity check. Reply with JSON.",
                       user='Return {"reply": "pong"}.', schema=PING_SCHEMA, schema_name="ping",
                       effort="low", max_output_tokens=2048, purpose="preflight")
    t0 = time.monotonic()
    try:
        resp = await p.generate(req)
    except (ModelInfraError, ModelOutputError) as exc:
        return CheckResult(key, "fail", f"{p.display_name} ({p.deployment}): {exc}", int((time.monotonic() - t0) * 1000))
    except Exception as exc:  # noqa: BLE001 - e.g. credential errors
        return CheckResult(key, "fail", f"{p.display_name}: {type(exc).__name__}: {str(exc)[:300]}",
                           int((time.monotonic() - t0) * 1000))
    return CheckResult(key, "pass", f"{p.display_name} ({p.deployment}) replied {resp.data.get('reply')!r}; "
                       f"tokens in/out {resp.usage.input_tokens}/{resp.usage.output_tokens}", resp.latency_ms)


async def check_sandbox(svc: Services) -> CheckResult:
    if svc.executor is None:
        return CheckResult("sandbox", "skipped", "SESSIONS_POOL_ENDPOINT not configured")
    ex = svc.executor
    sid = ex.new_session_id()
    t0 = time.monotonic()
    try:
        out = await ex.run_cases(SANDBOX_SOLVE, ["1 2 3\n"], 30, sid)
        if out.status != "ok" or not out.results or out.results[0].output != "6":
            return CheckResult("sandbox", "fail", f"unexpected result: status={out.status} "
                               f"stderr={out.stderr[:200]!r}", int((time.monotonic() - t0) * 1000))
        probe = await ex.run_raw(EGRESS_PROBE, 30, sid)
        line = next((ln for ln in probe.stdout.splitlines() if ln.startswith("EGRESS:")), "")
        if "allowed" in line:
            return CheckResult("sandbox", "fail", f"code executes, but outbound network is ALLOWED ({line}); "
                               "configure the pool with EgressDisabled", int((time.monotonic() - t0) * 1000))
        if not line:
            return CheckResult("sandbox", "fail", f"egress probe produced no output: {probe.stderr[:200]!r}",
                               int((time.monotonic() - t0) * 1000))
        return CheckResult("sandbox", "pass", f"executed solve() correctly; egress blocked ({line[7:]})",
                           int((time.monotonic() - t0) * 1000))
    except Exception as exc:  # noqa: BLE001
        return CheckResult("sandbox", "fail", f"{type(exc).__name__}: {str(exc)[:300]}",
                           int((time.monotonic() - t0) * 1000))
    finally:
        await ex.release(sid)


async def check_storage(svc: Services) -> CheckResult:
    try:
        d = svc.settings.aps_data_dir
        d.mkdir(parents=True, exist_ok=True)
        probe = d / ".write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return CheckResult("storage", "pass", f"data directory writable: {d}")
    except OSError as exc:
        return CheckResult("storage", "fail", f"data directory not writable: {exc}")


async def run_checks(svc: Services, names: list[str] | None = None, year: int = 2024) -> list[CheckResult]:
    names = names or ["storage", "aoc", "workhorse", "escalation", "sandbox"]
    out: list[CheckResult] = []
    for n in names:
        if n == "storage":
            out.append(await check_storage(svc))
        elif n == "aoc":
            out.append(await check_aoc(svc, year))
        elif n in ("workhorse", "escalation"):
            out.append(await check_model(svc, n))
        elif n == "sandbox":
            out.append(await check_sandbox(svc))
    return out
