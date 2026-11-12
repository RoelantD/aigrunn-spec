<#
.SYNOPSIS
  Prepare the two-worktree conference setup.

.DESCRIPTION
  Creates, next to this repository:
    aps-live         worktree A (detached at main = demo/07-complete + post-checkpoint fixes) - runs the solver
    aps-walkthrough  worktree B (detached at demo/00-initial)  - checkpoint walkthrough
    aps-data         runtime data (SQLite, puzzle cache, .env) - never inside a worktree
  and installs backend/frontend dependencies in aps-live. Safe to re-run.

.EXAMPLE
  .\scripts\setup-demo.ps1
  .\scripts\setup-demo.ps1 -LiveRef main     # use a branch instead of the final tag
#>
param(
    [string]$LiveRef = '',
    [switch]$SkipInstall
)
. "$PSScriptRoot\common.ps1"

Write-Step "Demo root: $DemoRoot"
foreach ($t in 'git', 'uv', 'npm') { if (-not (Test-Tool $t)) { throw "$t is required but was not found on PATH" } }

Push-Location $RepoRoot
try {
    git fetch --tags --quiet 2>$null
    if (-not $LiveRef) {
        $LiveRef = $LiveBranch
    }

    Write-Step "Runtime data directory"
    New-Item -ItemType Directory -Force $DataDir | Out-Null
    if (-not (Test-Path $EnvFile)) {
        Copy-Item (Join-Path $RepoRoot '.env.example') $EnvFile
        Write-Warn2 "Created $EnvFile from .env.example - fill in AOC_SESSION, AOC_CONTACT and the Azure endpoints."
    } else { Write-Ok "$EnvFile exists (left untouched)" }

    Write-Step "Worktree A (live app) -> $LiveDir @ $LiveRef"
    if (Test-Path $LiveDir) {
        $dirtyLive = git -C $LiveDir status --porcelain --untracked-files=no
        if ($dirtyLive) { Write-Warn2 "aps-live has local changes; not updating it" }
        else { git -C $LiveDir checkout --quiet --detach $LiveRef; Write-Ok "updated to $LiveRef ($(git -C $LiveDir rev-parse --short HEAD))" }
    } else {
        git worktree add --quiet --detach $LiveDir $LiveRef
        Write-Ok "created"
    }

    Write-Step "Worktree B (walkthrough) -> $WalkDir @ 00-start"
    if (Test-Path $WalkDir) {
        Write-Ok "exists; current HEAD: $(git -C $WalkDir describe --tags --always)"
    } else {
        $hasSteps = git branch --list '00-start'
        if ($hasSteps) { git worktree add --quiet $WalkDir '00-start' }
        else { git worktree add --quiet --detach $WalkDir 'HEAD'; Write-Warn2 "step branches missing: python scripts\walkthroughuild_walkthrough.py" }
        Write-Ok "created"
    }
} finally { Pop-Location }

if (-not $SkipInstall) {
    Write-Step "Installing backend dependencies (uv sync)"
    Push-Location (Join-Path $LiveDir 'backend'); try { uv sync --quiet } finally { Pop-Location }
    Write-Step "Installing frontend dependencies (npm ci)"
    Push-Location (Join-Path $LiveDir 'frontend'); try { npm ci --no-fund --no-audit --loglevel=error } finally { Pop-Location }
}

Write-Step "Done"
Write-Host @"

  Live app worktree : $LiveDir
  Walkthrough       : $WalkDir
  Data + secrets    : $DataDir  (APS_ENV_FILE=$EnvFile)

  Next: edit $EnvFile, then run .\scripts\preflight.ps1 and .\scripts\start-live-app.ps1
"@
