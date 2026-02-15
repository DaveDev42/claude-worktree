# claude-worktree shell functions for PowerShell
# Source this file to enable shell functions:
#   cw _shell-function powershell | Out-String | Invoke-Expression

# Navigate to a worktree by branch name
# If no argument is provided, show interactive worktree selector
# Use -g to search across all registered repositories
# Supports repo:branch notation (auto-enables global mode)
function cw-cd {
    param(
        [Parameter(Mandatory=$false, Position=0)]
        [string]$Branch,
        [Alias('global')]
        [switch]$g
    )

    # Auto-detect repo:branch notation → enable global mode
    if (-not $g -and $Branch -match ':') {
        $g = [switch]::Present
    }

    $worktreePath = $null

    if (-not $Branch) {
        # No argument — interactive selector
        if ($g) {
            $worktreePath = cw _path -g --interactive
        } else {
            $worktreePath = cw _path --interactive
        }
        if ($LASTEXITCODE -ne 0) {
            return
        }
    } elseif ($g) {
        # Global mode: delegate to cw _path -g
        $worktreePath = cw _path -g $Branch
        if ($LASTEXITCODE -ne 0) {
            return
        }
    } else {
        # Local mode: get worktree path from git directly
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

    $branches = $null
    if ($fakeBoundParameters.ContainsKey('g')) {
        # Global mode: get repo:branch from all registered repos
        $branches = cw _path --list-branches -g 2>&1 |
            Where-Object { $_ -is [string] -and $_.Trim() } |
            Sort-Object -Unique
    } else {
        # Local mode: get branches from git
        $branches = git worktree list --porcelain 2>&1 |
            Where-Object { $_ -is [string] } |
            Select-String -Pattern '^branch ' |
            ForEach-Object { $_ -replace '^branch refs/heads/', '' } |
            Sort-Object -Unique
    }

    # Filter branches that match the current word
    $branches | Where-Object { $_ -like "$wordToComplete*" } |
        ForEach-Object {
            [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
        }
}
