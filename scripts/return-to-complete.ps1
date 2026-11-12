<#
.SYNOPSIS
  Return worktree B (aps-walkthrough) to the final step, 10-working.
  The live solver in worktree A is never touched.
#>
param([switch]$Force)
& "$PSScriptRoot\show-checkpoint.ps1" 10-working -Force:$Force
