<#
.SYNOPSIS
  Start the finished application from worktree A (aps-live) on fixed ports.

.DESCRIPTION
  Backend : http://127.0.0.1:8765  (FastAPI, uvicorn)
  Frontend: http://127.0.0.1:5175  (dashboard)  and /present (presentation view)
  Each process runs in its own window so closing this terminal or switching the walkthrough
  worktree never affects them. Run data lives in aps-data, outside both worktrees.
#>
param(
    [switch]$NoBrowser,
    [string]$AppDir = ''
)
. "$PSScriptRoot\common.ps1"

if (-not $AppDir) { $AppDir = $LiveDir }
if (-not (Test-Path (Join-Path $AppDir 'backend'))) { throw "Live worktree not found at $AppDir. Run .\scripts\setup-demo.ps1 first." }
if (-not (Test-Path $EnvFile)) { throw "$EnvFile not found. Run setup-demo.ps1 and fill it in." }

foreach ($p in $BackendPort, $FrontendPort) {
    if (-not (Test-PortFree $p)) { throw "Port $p is already in use. Is the app already running? (Get-NetTCPConnection -LocalPort $p)" }
}

$envPrefix = "`$env:APS_ENV_FILE='$EnvFile'; `$env:APS_DATA_DIR='$DataDir';"
$backendCmd = "$envPrefix Set-Location '$AppDir\backend'; `$host.UI.RawUI.WindowTitle='APS backend :$BackendPort'; " +
              "uv run uvicorn app.main:get_app --factory --host 127.0.0.1 --port $BackendPort"
$frontendCmd = "Set-Location '$AppDir\frontend'; `$host.UI.RawUI.WindowTitle='APS dashboard :$FrontendPort'; npm run dev"

Write-Step "Starting backend from $AppDir (data: $DataDir)"
Start-Process powershell -ArgumentList '-NoExit', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $backendCmd | Out-Null
Write-Step "Starting dashboard"
Start-Process powershell -ArgumentList '-NoExit', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $frontendCmd | Out-Null

Write-Step "Waiting for backend health"
$ok = $false
for ($i = 0; $i -lt 60; $i++) {
    try { $r = Invoke-RestMethod "http://127.0.0.1:$BackendPort/api/health" -TimeoutSec 2; if ($r.status -eq 'ok') { $ok = $true; break } } catch { }
    Start-Sleep -Seconds 1
}
if ($ok) { Write-Ok "backend healthy (version $($r.version))" } else { Write-Warn2 "backend did not answer yet - check its window" }

if (-not $NoBrowser) { Start-Process "http://127.0.0.1:$FrontendPort/" }
Write-Host "`n  Dashboard:    http://127.0.0.1:$FrontendPort/`n  Presentation: http://127.0.0.1:$FrontendPort/present`n"
