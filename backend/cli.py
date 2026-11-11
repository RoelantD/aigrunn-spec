"""Operator CLI: preflight checks and safe preloading (FR-046, US6).

    uv run python cli.py preflight --year 2024 --days 1-5
    uv run python cli.py preflight --skip escalation --preload

Preflight never submits answers and never requests puzzle parts that are not yet available.
"""

from __future__ import annotations

import argparse
import asyncio
import subprocess  # noqa: S404 - only used for read-only `git` queries
import sys

from app.config import REPO_ROOT, get_settings
from app.logsetup import configure_logging
from app.preflight import CheckResult, run_checks
from app.services import build_services

CHECKPOINTS = [f"demo/0{i}-{n}" for i, n in enumerate(
    ["initial", "constitution", "specify", "clarify", "plan", "tasks", "implement", "complete"])]

ICON = {"pass": "PASS", "fail": "FAIL", "skipped": "SKIP"}


def _days(spec: str) -> tuple[int, int]:
    a, _, b = spec.partition("-")
    lo, hi = int(a), int(b or a)
    if not 1 <= lo <= hi <= 25:
        raise argparse.ArgumentTypeError("days must be within 1-25, e.g. 1-5")
    return lo, hi


def check_checkpoints() -> CheckResult:
    try:
        out = subprocess.run(["git", "-C", str(REPO_ROOT), "tag", "--list", "demo/*"],  # noqa: S603, S607
                             capture_output=True, text=True, timeout=20, check=True).stdout.split()
    except (OSError, subprocess.SubprocessError) as exc:
        return CheckResult("checkpoints", "fail", f"git not available: {exc}")
    missing = [t for t in CHECKPOINTS if t not in out]
    if missing:
        return CheckResult("checkpoints", "fail", f"missing tags: {', '.join(missing)}")
    return CheckResult("checkpoints", "pass", f"all {len(CHECKPOINTS)} checkpoint tags present")


async def preflight(args) -> int:
    settings = get_settings()
    configure_logging("WARNING", settings.secret_values())
    svc = build_services(settings)
    await svc.db.init()
    names = [n for n in ["storage", "aoc", "workhorse", "escalation", "sandbox"] if n not in args.skip]
    results = await run_checks(svc, names, args.year)
    if "checkpoints" not in args.skip:
        results.append(check_checkpoints())
    lo, hi = args.days
    if any(r.name == "aoc" and r.status == "pass" for r in results):
        stars = await svc.aoc.calendar(args.year)
        unsolved = [(d, p) for d in range(lo, hi + 1) for p in (1, 2) if stars.get(d, 0) < p and
                    not (d == 25 and p == 2)]
        results.append(CheckResult("range", "pass" if unsolved else "fail",
                                   f"days {lo}-{hi}: {len(unsolved)} unsolved part(s)" if unsolved else
                                   f"days {lo}-{hi} are already fully solved on this account; choose another range"))
        if args.preload and unsolved:
            n = 0
            for d in sorted({d for d, _ in unsolved}):
                await svc.aoc.day_page(args.year, d)   # only parts already accessible to this account
                await svc.aoc.input(args.year, d)      # cached permanently; not re-fetched later
                n += 1
            results.append(CheckResult("preload", "pass", f"cached public page + input for {n} day(s)"))
    pricing = [k for k, p in svc.router.prices.items() if not p.configured]
    if pricing:
        results.append(CheckResult("pricing", "skipped", f"no prices configured for {', '.join(pricing)}; cost "
                                   "estimates and the spend cap will show $0"))
    await svc.aclose()
    width = max(len(r.name) for r in results)
    print(f"\nPreflight for Advent of Code {args.year}, days {lo}-{hi} (no answers are submitted)\n")
    for r in results:
        ms = f" ({r.latency_ms} ms)" if r.latency_ms else ""
        print(f"  [{ICON[r.status]}] {r.name.ljust(width)}  {r.detail}{ms}")
    failed = [r for r in results if r.status == "fail"]
    print(f"\nOverall: {'FAIL' if failed else 'PASS'}\n")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cli.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    pf = sub.add_parser("preflight", help="validate the demo environment without submitting anything")
    pf.add_argument("--year", type=int, default=2024)
    pf.add_argument("--days", type=_days, default=(1, 25), help="day range, e.g. 1-5")
    pf.add_argument("--skip", nargs="*", default=[],
                    choices=["storage", "aoc", "workhorse", "escalation", "sandbox", "checkpoints"])
    pf.add_argument("--preload", action="store_true",
                    help="cache already-accessible puzzle pages and inputs for unsolved days (paced)")
    args = p.parse_args(argv)
    if args.cmd == "preflight":
        return asyncio.run(preflight(args))
    return 2


if __name__ == "__main__":
    sys.exit(main())
