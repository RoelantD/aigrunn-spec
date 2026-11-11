#!/usr/bin/env bash
# Bash equivalents of the PowerShell demo scripts (macOS/Linux/Git Bash).
#   scripts/demo.sh setup | start | show <checkpoint> [--force] | return | list | preflight [days]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEMO_ROOT="${APS_DEMO_ROOT:-$(dirname "$REPO_ROOT")}"
LIVE="$DEMO_ROOT/aps-live"; WALK="$DEMO_ROOT/aps-walkthrough"; DATA="$DEMO_ROOT/aps-data"; ENVF="$DATA/.env"
FINAL=demo/07-complete
declare -A CP=([initial]=demo/00-initial [constitution]=demo/01-constitution [specify]=demo/02-specify
  [clarify]=demo/03-clarify [plan]=demo/04-plan [tasks]=demo/05-tasks [implement]=demo/06-implement [complete]=$FINAL)
ORDER=(initial constitution specify clarify plan tasks implement complete)

step() { printf '\033[36m==> %s\033[0m\n' "$*"; }

cmd_setup() {
  mkdir -p "$DATA"; [ -f "$ENVF" ] || { cp "$REPO_ROOT/.env.example" "$ENVF"; echo "Created $ENVF - fill it in."; }
  cd "$REPO_ROOT"
  if [ -d "$LIVE" ]; then git -C "$LIVE" checkout --quiet --detach main; else git worktree add --detach "$LIVE" main; fi
  [ -d "$WALK" ] || git worktree add --detach "$WALK" "$(git tag --list demo/00-initial | grep -q . && echo demo/00-initial || echo HEAD)"
  (cd "$LIVE/backend" && uv sync --quiet); (cd "$LIVE/frontend" && npm ci --no-fund --no-audit --loglevel=error)
  step "Ready: $LIVE (live), $WALK (walkthrough), $DATA (data)"
}

cmd_start() {
  export APS_ENV_FILE="$ENVF" APS_DATA_DIR="$DATA"
  (cd "$LIVE/backend" && nohup uv run uvicorn app.main:get_app --factory --host 127.0.0.1 --port 8765 >"$DATA/backend.log" 2>&1 &)
  (cd "$LIVE/frontend" && nohup npm run dev >"$DATA/frontend.log" 2>&1 &)
  step "Backend :8765 (log $DATA/backend.log), dashboard http://127.0.0.1:5175/ , presentation /present"
}

cmd_list() { for k in "${ORDER[@]}"; do printf '  %-13s %-22s %s\n' "$k" "${CP[$k]}" "$(git -C "$REPO_ROOT" log -1 --format=%s "${CP[$k]}" 2>/dev/null)"; done; }

cmd_show() {
  local name="${1:?checkpoint name}" force="${2:-}" tag="${CP[$1]:-}"
  [ -n "$tag" ] || { echo "unknown checkpoint: $name"; cmd_list; exit 1; }
  if [ -n "$(git -C "$WALK" status --porcelain)" ]; then
    git -C "$WALK" status --short
    if [ "$force" != "--force" ]; then
      read -r -p "Discard these changes (they are stashed first)? type 'discard': " a; [ "$a" = discard ] || { echo cancelled; exit 0; }
    fi
    git -C "$WALK" stash push --include-untracked -m "show-checkpoint backup $(date -Is)" >/dev/null
  fi
  git -C "$WALK" checkout --quiet --detach "$tag"
  if [ -d "$WALK/specs/001-agentic-aoc-solver" ]; then
    printf '{\n  "feature_directory": "specs/001-agentic-aoc-solver"\n}\n' > "$WALK/.specify/feature.json"
  else rm -f "$WALK/.specify/feature.json"; fi
  step "Walkthrough at $tag: $(git -C "$WALK" log -1 --format=%s)"
}

cmd_preflight() {
  export APS_ENV_FILE="$ENVF" APS_DATA_DIR="$DATA"
  local dir="$LIVE"; [ -d "$dir" ] || dir="$REPO_ROOT"
  (cd "$dir/backend" && uv run python cli.py preflight --days "${1:-1-25}")
}

case "${1:-}" in
  setup) cmd_setup ;; start) cmd_start ;; list) cmd_list ;; return) cmd_show complete "${2:-}" ;;
  show) shift; cmd_show "$@" ;; preflight) shift; cmd_preflight "$@" ;;
  *) echo "usage: $0 setup|start|list|show <checkpoint> [--force]|return|preflight [days]"; exit 2 ;;
esac
