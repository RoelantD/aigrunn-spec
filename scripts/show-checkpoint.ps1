<#
.SYNOPSIS
  Switch worktree B (aps-walkthrough) to a walkthrough step branch (00-start ... 10-working).

.DESCRIPTION
  Each step branch holds the exact content of a real development stage plus a NEXT_STEP.md with the
  prompt that leads to the next step. Switching never touches worktree A or aps-data, so the running
  solver is unaffected. Uncommitted changes are never discarded without confirmation (or -Force),
  and they are stashed first. The script also writes .specify/feature.json (git-ignored, per-checkout
  Spec Kit state) so Spec Kit commands in the walkthrough resolve the active feature.

.EXAMPLE
  .\scripts\show-checkpoint.ps1 02-constitution
  .\scripts\show-checkpoint.ps1 2            # same
  .\scripts\show-checkpoint.ps1 clarify      # alias for 04-clarify
  .\scripts\show-checkpoint.ps1 -Next        # one step forward
  .\scripts\show-checkpoint.ps1 -List
#>
param(
    [Parameter(Position = 0)][string]$Step = '',
    [switch]$List,
    [switch]$Next,
    [switch]$Previous,
    [switch]$Force,
    [switch]$Open
)
. "$PSScriptRoot\common.ps1"

if (-not (Test-Path $WalkDir)) { throw "Walkthrough worktree not found at $WalkDir. Run .\scripts\setup-demo.ps1." }
$current = git -C $WalkDir branch --show-current

if ($List -or (-not $Step -and -not $Next -and -not $Previous)) {
    Write-Host "Walkthrough steps (current: $current):"
    foreach ($s in $Steps) {
        $subject = git -C $RepoRoot log -1 --format=%s $s 2>$null
        $mark = if ($s -eq $current) { '>' } else { ' ' }
        Write-Host ("  {0} {1,-16} {2}" -f $mark, $s, $subject)
    }
    return
}

if ($Next -or $Previous) {
    $i = [array]::IndexOf($Steps, $current)
    if ($i -lt 0) { $i = 0 }
    $i = if ($Next) { [Math]::Min($i + 1, $Steps.Count - 1) } else { [Math]::Max($i - 1, 0) }
    $Step = $Steps[$i]
}
$branch = Resolve-Step $Step

$dirty = git -C $WalkDir status --porcelain --untracked-files=normal
if ($dirty) {
    Write-Warn2 "The walkthrough worktree has uncommitted changes:"
    $dirty | ForEach-Object { Write-Host "      $_" }
    if (-not $Force) {
        $answer = Read-Host "Discard these changes and switch to $branch? Type 'discard' to continue, anything else to cancel"
        if ($answer -ne 'discard') { Write-Host "Cancelled. Nothing changed."; return }
    }
    $stashName = "show-checkpoint backup $(Get-Date -Format s)"
    git -C $WalkDir stash push --include-untracked -m $stashName | Out-Null
    Write-Ok "changes saved in 'git stash' ($stashName) - recover with: git -C `"$WalkDir`" stash list"
}

git -C $WalkDir checkout --quiet $branch
if ($LASTEXITCODE -ne 0) { throw "checkout of $branch failed (does the branch exist? run scripts\build-walkthrough.ps1)" }

# Spec Kit tracks the active feature separately from the branch (.specify/feature.json, git-ignored).
$featureJson = Join-Path $WalkDir '.specify\feature.json'
$featureDir = 'specs/001-agentic-aoc-solver'
if (Test-Path (Join-Path $WalkDir $featureDir)) {
    Set-Content -Path $featureJson -Value "{`n  `"feature_directory`": `"$featureDir`"`n}" -Encoding Ascii
} elseif (Test-Path $featureJson) { Remove-Item $featureJson }

Write-Step "Walkthrough is now on $branch"
git -C $WalkDir log -1 --format="    %h %s"

$show = @{
    '00-start'        = @('README.md (title)', 'NEXT_STEP.md')
    '01-install'      = @('.specify\', '.github\skills\speckit-*', '.specify\memory\constitution.md (template)')
    '02-constitution' = @('.specify\memory\constitution.md')
    '03-specify'      = @("$featureDir\spec.md", "$featureDir\checklists\requirements.md")
    '04-clarify'      = @("$featureDir\spec.md  (## Clarifications)")
    '05-plan'         = @("$featureDir\plan.md", "$featureDir\research.md", "$featureDir\contracts\aoc-client.md")
    '06-tasks'        = @("$featureDir\tasks.md", "$featureDir\checklists\submission-safety.md")
    '07-analyze'      = @("$featureDir\analysis.md", "$featureDir\tasks.md")
    '08-implement'    = @('backend\app\agents\orchestrator.py', 'frontend\src\pages\Presentation.tsx', "$featureDir\tasks.md  ([X] marks)")
    '09-converge'     = @("$featureDir\tasks.md  (Phase 11-12)", "$featureDir\traceability.md", 'docs\adr\')
    '10-working'      = @('docs\TESTING.md', 'demo\TALK_SCRIPT.md')
}
Write-Host "  Open in the editor:"
foreach ($f in $show[$branch]) { Write-Host "    $WalkDir\$f" }
Write-Host "    $WalkDir\NEXT_STEP.md   (prompt for the next step)"
if ($Open -and (Test-Tool 'code')) { code $WalkDir }
