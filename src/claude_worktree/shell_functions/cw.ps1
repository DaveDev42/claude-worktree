# claude-worktree shell functions for PowerShell
# Source this file to enable shell functions:
#   cw _shell-function powershell | Out-String | Invoke-Expression

# Navigate to a worktree by branch name
# If no argument is provided, navigate to the base (main) worktree
function cw-cd {
    param(
        [Parameter(Mandatory=$false, Position=0)]
        [string]$Branch
    )

    $worktreePath = $null

    if (-not $Branch) {
        # No argument - navigate to base (main) worktree
        $worktreePath = git worktree list --porcelain 2>&1 |
            Where-Object { $_ -is [string] } |
            ForEach-Object {
                if ($_ -match '^worktree (.+)$') { $Matches[1]; break }
            } | Select-Object -First 1
    } else {
        # Argument provided - navigate to specified branch worktree
        $worktreePath = git worktree list --porcelain 2>&1 |
            Where-Object { $_ -is [string] } |
            ForEach-Object {
                if ($_ -match '^worktree (.+)$') { $path = $Matches[1] }
                if ($_ -match "^branch refs/heads/$Branch$") { $path }
            } | Select-Object -First 1
    }

    if (-not $worktreePath) {
        if (-not $Branch) {
            Write-Error "Error: No worktree found (not in a git repository?)"
        } else {
            Write-Error "Error: No worktree found for branch '$Branch'"
        }
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
    $branches = git worktree list --porcelain 2>&1 |
        Where-Object { $_ -is [string] } |
        Select-String -Pattern '^branch ' |
        ForEach-Object { $_ -replace '^branch refs/heads/', '' } |
        Sort-Object -Unique

    # Filter branches that match the current word
    $branches | Where-Object { $_ -like "$wordToComplete*" } |
        ForEach-Object {
            [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
        }
}
