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

# Walkthrough steps = branches. Each branch's content equals a real development stage (see demo/CHECKPOINTS.md).
$Script:Steps = @('00-start', '01-install', '02-constitution', '03-specify', '04-clarify', '05-plan',
                  '06-tasks', '07-analyze', '08-implement', '09-converge', '10-working')
# Short names and the original demo/NN tag names keep working as aliases.
$Script:StepAliases = @{
    'start' = '00-start'; 'install' = '01-install'; 'initial' = '01-install'
    'constitution' = '02-constitution'; 'specify' = '03-specify'; 'clarify' = '04-clarify'
    'plan' = '05-plan'; 'tasks' = '06-tasks'; 'analyze' = '07-analyze'; 'implement' = '08-implement'
    'converge' = '09-converge'; 'complete' = '09-converge'; 'working' = '10-working'
}
# Kept for preflight: the original stage tags.
$Script:Checkpoints = [ordered]@{
    'initial' = 'demo/00-initial'; 'constitution' = 'demo/01-constitution'; 'specify' = 'demo/02-specify'
    'clarify' = 'demo/03-clarify'; 'plan' = 'demo/04-plan'; 'tasks' = 'demo/05-tasks'
    'implement' = 'demo/06-implement'; 'complete' = 'demo/07-complete'
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

function Resolve-Step([string]$name) {
    if ($Script:Steps -contains $name) { return $name }
    if ($Script:StepAliases.ContainsKey($name)) { return $Script:StepAliases[$name] }
    if ($name -match '^\d{1,2}$') { $p = '{0:D2}-' -f [int]$name; foreach ($s in $Script:Steps) { if ($s.StartsWith($p)) { return $s } } }
    throw "Unknown step '$name'. Use one of: $($Script:Steps -join ', ')"
}
