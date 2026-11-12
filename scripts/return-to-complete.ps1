<#
.SYNOPSIS
  Return worktree B (aps-walkthrough) to the completed application checkpoint.
  The live solver in worktree A is never touched.
#>
param([switch]$Force)
& "$PSScriptRoot\show-checkpoint.ps1" complete -Force:$Force
