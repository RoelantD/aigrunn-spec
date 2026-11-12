<#
.SYNOPSIS
  Validate the demo environment. Never submits answers and never requests locked puzzle parts.

.DESCRIPTION
  Checks tools, worktrees, ports, configuration, then runs the backend preflight:
  storage, Advent of Code session, both Foundry models, sandbox execution + egress block,
  unsolved parts in the chosen range, and checkpoint tags.

.EXAMPLE
  .\scripts\preflight.ps1 -Days 1-5
  .\scripts\preflight.ps1 -Days 6-10 -Preload     # also cache accessible pages/inputs (paced)
#>
param(
    [string]$Days = '1-25',
    [int]$Year = 2024,
    [switch]$Preload,
    [string[]]$Skip = @()
)
. "$PSScriptRoot\common.ps1"
$failed = 0

Write-Step "Tools"
foreach ($t in 'git', 'uv', 'npm', 'node', 'az') {
    if (Test-Tool $t) { Write-Ok $t } else { Write-Warn2 "$t not found"; if ($t -ne 'az') { $failed++ } }
}
if (Test-Tool 'az') {
    $acct = az account show --query "{name:name}" -o tsv 2>$null
    if ($acct) { Write-Ok "az logged in ($acct) - Entra ID tokens available" } else { Write-Warn2 "az not logged in (needed for Entra ID auth): az login" }
}

Write-Step "Worktrees and data"
$appDir = if (Test-Path $LiveDir) { $LiveDir } else { Write-Warn2 "aps-live missing; using $RepoRoot"; $RepoRoot }
if (Test-Path $WalkDir) { Write-Ok "walkthrough on $(git -C $WalkDir branch --show-current)" } else { Write-Warn2 "aps-walkthrough missing (run setup-demo.ps1)"; $failed++ }
$missingSteps = @($Steps | Where-Object { -not (git -C $RepoRoot branch --list $_) })
if ($missingSteps.Count) { Write-Warn2 "missing step branches: $($missingSteps -join ', ') (python scripts\walkthroughuild_walkthrough.py)"; $failed++ } else { Write-Ok "all $($Steps.Count) step branches present (00-start .. 10-working)" }
if (Test-Path $LiveDir) {
    $liveHead = git -C $LiveDir rev-parse HEAD
    $mainHead = git -C $RepoRoot rev-parse $LiveBranch
    if ($liveHead -eq $mainHead) { Write-Ok "live worktree at $LiveBranch ($(git -C $LiveDir describe --tags --always))" }
    else { Write-Warn2 "live worktree is not at $LiveBranch - run .\scripts\setup-demo.ps1 to update it (stop the app first)"; $failed++ }
}
if (Test-Path $EnvFile) { Write-Ok "config: $EnvFile" } else { Write-Warn2 "missing $EnvFile"; $failed++ }

Write-Step "Ports"
foreach ($p in $BackendPort, $FrontendPort) {
    if (Test-PortFree $p) { Write-Ok "port $p free" } else { Write-Warn2 "port $p in use (fine if the app is already running)" }
}

Write-Step "Backend preflight (no submissions)"
$env:APS_ENV_FILE = $EnvFile
$env:APS_DATA_DIR = $DataDir
$cliArgs = @('run', 'python', 'cli.py', 'preflight', '--year', $Year, '--days', $Days)
if ($Preload) { $cliArgs += '--preload' }
if ($Skip.Count) { $cliArgs += '--skip'; $cliArgs += $Skip }
Push-Location (Join-Path $appDir 'backend')
try { & uv @cliArgs; if ($LASTEXITCODE -ne 0) { $failed++ } } finally { Pop-Location }

if ($failed) { Write-Host "`nPREFLIGHT: $failed problem(s) - see above." -ForegroundColor Red; exit 1 }
Write-Host "`nPREFLIGHT: all checks passed." -ForegroundColor Green
