# Shared settings for the demo scripts (Windows PowerShell 5.1 and PowerShell 7 compatible).
$ErrorActionPreference = 'Stop'

$Script:RepoRoot     = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Script:DemoRoot     = if ($env:APS_DEMO_ROOT) { $env:APS_DEMO_ROOT } else { (Split-Path $Script:RepoRoot -Parent) }
$Script:LiveDir      = Join-Path $Script:DemoRoot 'aps-live'
$Script:WalkDir      = Join-Path $Script:DemoRoot 'aps-walkthrough'
$Script:DataDir      = Join-Path $Script:DemoRoot 'aps-data'
$Script:EnvFile      = Join-Path $Script:DataDir '.env'
$Script:BackendPort  = 8765
$Script:FrontendPort = 5175
$Script:FinalTag     = 'demo/07-complete'
$Script:LiveBranch   = 'main'   # live app follows main: demo/07-complete + fixes from live verification

$Script:Checkpoints = [ordered]@{
    'initial'      = 'demo/00-initial'
    'constitution' = 'demo/01-constitution'
    'specify'      = 'demo/02-specify'
    'clarify'      = 'demo/03-clarify'
    'plan'         = 'demo/04-plan'
    'tasks'        = 'demo/05-tasks'
    'implement'    = 'demo/06-implement'
    'complete'     = 'demo/07-complete'
}

function Write-Step([string]$msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok([string]$msg)   { Write-Host "    [ok] $msg" -ForegroundColor Green }
function Write-Warn2([string]$msg) { Write-Host "    [!] $msg" -ForegroundColor Yellow }

function Test-Tool([string]$name) { return [bool](Get-Command $name -ErrorAction SilentlyContinue) }

function Test-PortFree([int]$port) {
    $l = $null
    try {
        $l = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $port)
        $l.Start(); return $true
    } catch { return $false } finally { if ($l) { $l.Stop() } }
}

function Resolve-Checkpoint([string]$name) {
    if ($Script:Checkpoints.Contains($name)) { return $Script:Checkpoints[$name] }
    foreach ($v in $Script:Checkpoints.Values) { if ($v -eq $name -or $v -like "demo/$name-*") { return $v } }
    throw "Unknown checkpoint '$name'. Use one of: $($Script:Checkpoints.Keys -join ', ')"
}
