"""Build the presenter walkthrough branches 00-start ... 10-working.

Each branch is one commit on a linear chain. Its tree is the exact tree of a real development stage
(tag or commit, see SOURCES), plus:
  * NEXT_STEP.md - the prompt that leads to the next step (scripts/walkthrough/next_steps.py)
  * the Copilot Spec Kit skills (.github/skills/speckit-*) on steps that predate their installation

Uses git plumbing with a temporary index: the working tree and the current branch are never touched.
Re-running rebuilds the branches (e.g. after main changed). Run from anywhere:

    python scripts/walkthrough/build_walkthrough.py            # main = source for 10-working
    python scripts/walkthrough/build_walkthrough.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
from next_steps import FOOT, STEPS  # noqa: E402

SOURCES = {  # step branch -> real stage it reproduces
    "01-install": "demo/00-initial",
    "02-constitution": "demo/01-constitution",
    "03-specify": "demo/02-specify",
    "04-clarify": "demo/03-clarify",
    "05-plan": "demo/04-plan",
    "06-tasks": "66357b8",            # tasks commit (checklist + tasks), before analyze
    "07-analyze": "demo/05-tasks",
    "08-implement": "demo/06-implement",
    "09-converge": "demo/07-complete",
    "10-working": "main",
}
ORDER = ["00-start", *SOURCES]
COPILOT_PATHS = (".github/skills/", ".specify/integrations/copilot.manifest.json", ".specify/integration.json")


def git(*args: str, env: dict | None = None, input: bytes | None = None) -> str:
    r = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, env=env, input=input, check=False)
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {r.stderr.decode(errors='replace')}")
    return r.stdout.decode().strip()


def blob(text: str) -> str:
    return git("hash-object", "-w", "--stdin", input=text.replace("\r\n", "\n").encode("utf-8"))


def ls_tree(ref: str, prefix: str = "") -> list[tuple[str, str, str]]:
    out = git("ls-tree", "-r", "--full-tree", ref, *( [prefix] if prefix else []))
    rows = []
    for line in out.splitlines():
        meta, path = line.split("\t", 1)
        mode, _type, sha = meta.split()
        rows.append((mode, sha, path))
    return rows


def build_tree(base: str | None, files: dict[str, str], extra: list[tuple[str, str, str]]) -> str:
    with tempfile.TemporaryDirectory() as td:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(td) / "index")}
        if base:
            git("read-tree", base, env=env)
        else:
            git("read-tree", "--empty", env=env)
        for mode, sha, path in extra:
            git("update-index", "--add", "--cacheinfo", f"{mode},{sha},{path}", env=env)
        for path, text in files.items():
            git("update-index", "--add", "--cacheinfo", f"100644,{blob(text)},{path}", env=env)
        return git("write-tree", env=env)


def next_step_md(step: str) -> str:
    title, source, body = STEPS[step]
    return body.strip() + "\n" + FOOT.format(branch=step, source=source)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    copilot = [r for p in COPILOT_PATHS for r in ls_tree("main", p)]
    if not copilot:
        raise SystemExit("main has no Copilot integration files to overlay")
    gitignore = git("show", "demo/00-initial:.gitignore")

    parent = None
    for step in ORDER:
        title = STEPS[step][0]
        files = {"NEXT_STEP.md": next_step_md(step)}
        if step == "00-start":
            files["README.md"] = (HERE / "README-00-start.md").read_text(encoding="utf-8")
            files[".gitignore"] = gitignore + "\n"
            tree = build_tree(None, files, [])
            source = "new root"
        else:
            source = SOURCES[step]
            src_paths = {p for _, _, p in ls_tree(source)}
            overlay = [] if ".github/skills/speckit-specify/SKILL.md" in src_paths else copilot
            tree = build_tree(source, files, overlay)
        msg = (f"{step}: {title}\n\nWalkthrough step. Content = {source}"
               + ("" if step == "00-start" else " (+ NEXT_STEP.md, Copilot skills where missing)")
               + ".\nBuilt by scripts/walkthrough/build_walkthrough.py\n")
        commit = git("commit-tree", tree, *(["-p", parent] if parent else []), "-m", msg)
        if args.dry_run:
            print(f"{step:16} {commit[:8]} <- {source}")
        else:
            git("update-ref", f"refs/heads/{step}", commit)
            print(f"{step:16} {commit[:8]} <- {source}")
        parent = commit
    if not args.dry_run:
        print("\nIf aps-walkthrough has one of these branches checked out, run: "
              "git -C ..\\aps-walkthrough reset --hard  (or switch with show-checkpoint.ps1 -Force)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
