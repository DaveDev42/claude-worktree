# claude-worktree shell functions for PowerShell
# Source this file to enable shell functions:
#   cw _shell-function powershell | Invoke-Expression

# Navigate to a worktree by branch name
function cw-cd {
    param(
        [Parameter(Mandatory=$false, Position=0)]
        [string]$Branch
    )

    if (-not $Branch) {
        Write-Error "Usage: cw-cd <branch-name>"
        return
    }

    # Get worktree path from cw _path command
    $worktreePath = & cw _path $Branch 2>$null
    $exitCode = $LASTEXITCODE

    if ($exitCode -ne 0) {
        Write-Error "Error: No worktree found for branch '$Branch'"
        return
    }

    if (Test-Path -Path $worktreePath -PathType Container) {
        Set-Location -Path $worktreePath
        Write-Host "Switched to worktree: $worktreePath"
    } else {
        Write-Error "Error: Worktree directory not found: $worktreePath"
        return
    }
}

# Tab completion for cw-cd
Register-ArgumentCompleter -CommandName cw-cd -ParameterName Branch -ScriptBlock {
    param($commandName, $parameterName, $wordToComplete, $commandAst, $fakeBoundParameters)

    # Get list of worktree branches from git
    $branches = git worktree list --porcelain 2>$null |
        Select-String -Pattern '^branch ' |
        ForEach-Object { $_ -replace '^branch refs/heads/', '' } |
        Sort-Object -Unique

    # Filter branches that match the current word
    $branches | Where-Object { $_ -like "$wordToComplete*" } |
        ForEach-Object {
            [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
        }
}
