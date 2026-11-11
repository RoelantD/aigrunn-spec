<#
.SYNOPSIS
  Prepare the two-worktree conference setup.

.DESCRIPTION
  Creates, next to this repository:
    aps-live         worktree A (detached at demo/07-complete) - runs the solver
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
        $LiveRef = if (git tag --list $FinalTag) { $FinalTag } else { 'HEAD' }
    }

    Write-Step "Runtime data directory"
    New-Item -ItemType Directory -Force $DataDir | Out-Null
    if (-not (Test-Path $EnvFile)) {
        Copy-Item (Join-Path $RepoRoot '.env.example') $EnvFile
        Write-Warn2 "Created $EnvFile from .env.example - fill in AOC_SESSION, AOC_CONTACT and the Azure endpoints."
    } else { Write-Ok "$EnvFile exists (left untouched)" }

    Write-Step "Worktree A (live app) -> $LiveDir @ $LiveRef"
    if (Test-Path $LiveDir) {
        Write-Ok "exists; current HEAD: $(git -C $LiveDir describe --tags --always)"
    } else {
        git worktree add --detach $LiveDir $LiveRef | Out-Host
        Write-Ok "created"
    }

    Write-Step "Worktree B (walkthrough) -> $WalkDir @ demo/00-initial"
    if (Test-Path $WalkDir) {
        Write-Ok "exists; current HEAD: $(git -C $WalkDir describe --tags --always)"
    } else {
        $start = if (git tag --list 'demo/00-initial') { 'demo/00-initial' } else { 'HEAD' }
        git worktree add --detach $WalkDir $start | Out-Host
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
