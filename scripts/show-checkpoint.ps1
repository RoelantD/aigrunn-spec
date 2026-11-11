<#
.SYNOPSIS
  Switch worktree B (aps-walkthrough) to a Spec Kit development checkpoint.

.DESCRIPTION
  Never touches worktree A or aps-data, so the running solver is unaffected.
  Refuses to discard uncommitted changes unless you confirm (or pass -Force).
  Also writes .specify/feature.json (git-ignored, per-checkout Spec Kit state) so Spec Kit commands
  in the walkthrough resolve the active feature correctly.

.EXAMPLE
  .\scripts\show-checkpoint.ps1 clarify
  .\scripts\show-checkpoint.ps1 -List
#>
param(
    [Parameter(Position = 0)][string]$Checkpoint = '',
    [switch]$List,
    [switch]$Force,
    [switch]$Open
)
. "$PSScriptRoot\common.ps1"

if ($List -or -not $Checkpoint) {
    Write-Host "Checkpoints:"
    foreach ($k in $Checkpoints.Keys) {
        $tag = $Checkpoints[$k]
        $subject = git -C $RepoRoot log -1 --format=%s $tag 2>$null
        Write-Host ("  {0,-13} {1,-22} {2}" -f $k, $tag, $subject)
    }
    return
}
if (-not (Test-Path $WalkDir)) { throw "Walkthrough worktree not found at $WalkDir. Run .\scripts\setup-demo.ps1." }
$tag = Resolve-Checkpoint $Checkpoint

$dirty = git -C $WalkDir status --porcelain --untracked-files=normal
if ($dirty) {
    Write-Warn2 "The walkthrough worktree has uncommitted changes:"
    $dirty | ForEach-Object { Write-Host "      $_" }
    if (-not $Force) {
        $answer = Read-Host "Discard these changes and switch to $tag? Type 'discard' to continue, anything else to cancel"
        if ($answer -ne 'discard') { Write-Host "Cancelled. Nothing changed."; return }
    }
    $stashName = "show-checkpoint backup $(Get-Date -Format s)"
    git -C $WalkDir stash push --include-untracked -m $stashName | Out-Null
    Write-Ok "changes saved in 'git stash' ($stashName) - recover with: git -C `"$WalkDir`" stash list"
}

git -C $WalkDir checkout --quiet --detach $tag
if ($LASTEXITCODE -ne 0) { throw "checkout of $tag failed" }

# Spec Kit tracks the active feature separately from the branch (.specify/feature.json, git-ignored).
$featureJson = Join-Path $WalkDir '.specify\feature.json'
$featureDir = 'specs/001-agentic-aoc-solver'
if (Test-Path (Join-Path $WalkDir $featureDir)) {
    Set-Content -Path $featureJson -Value "{`n  `"feature_directory`": `"$featureDir`"`n}" -Encoding Ascii
} elseif (Test-Path $featureJson) { Remove-Item $featureJson }

Write-Step "Walkthrough is now at $tag"
git -C $WalkDir log -1 --format="    %h %s (%ad)" --date=short

$show = @{
    'demo/00-initial'      = @('.specify\memory\constitution.md (template)', '.claude\skills\')
    'demo/01-constitution' = @('.specify\memory\constitution.md')
    'demo/02-specify'      = @("$featureDir\spec.md", "$featureDir\checklists\requirements.md")
    'demo/03-clarify'      = @("$featureDir\spec.md  (## Clarifications)")
    'demo/04-plan'         = @("$featureDir\plan.md", "$featureDir\research.md", "$featureDir\data-model.md", "$featureDir\contracts\")
    'demo/05-tasks'        = @("$featureDir\tasks.md", "$featureDir\analysis.md", "$featureDir\checklists\submission-safety.md")
    'demo/06-implement'    = @('backend\app\agents\orchestrator.py', 'frontend\src\pages\Presentation.tsx', "$featureDir\tasks.md  ([X] marks)")
    'demo/07-complete'     = @("$featureDir\traceability.md", 'demo\PRESENTER_GUIDE.md', 'docs\adr\')
}
Write-Host "  Open in the editor:"
foreach ($f in $show[$tag]) { Write-Host "    $WalkDir\$f" }
if ($Open -and (Test-Tool 'code')) { code $WalkDir }
