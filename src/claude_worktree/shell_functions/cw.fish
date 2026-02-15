# claude-worktree shell functions for fish
# Source this file to enable shell functions:
#   cw _shell-function fish | source

# Navigate to a worktree by branch name
# If no argument is provided, show interactive worktree selector
# Use -g/--global to search across all registered repositories
# Supports repo:branch notation (auto-enables global mode)
function cw-cd
    set -l global_mode 0
    set -l branch ""

    # Parse arguments
    for arg in $argv
        switch $arg
            case -g --global
                set global_mode 1
            case '-*'
                echo "Error: Unknown option '$arg'" >&2
                echo "Usage: cw-cd [-g|--global] [branch|repo:branch]" >&2
                return 1
            case '*'
                set branch $arg
        end
    end

    # Auto-detect repo:branch notation → enable global mode
    if test $global_mode -eq 0; and string match -q '*:*' -- "$branch"
        set global_mode 1
    end

    set -l worktree_path

    if test -z "$branch"
        # No argument — interactive selector
        if test $global_mode -eq 1
            set worktree_path (cw _path -g --interactive)
        else
            set worktree_path (cw _path --interactive)
        end
        if test $status -ne 0
            return 1
        end
    else if test $global_mode -eq 1
        # Global mode: delegate to cw _path -g
        set worktree_path (cw _path -g "$branch")
        if test $status -ne 0
            return 1
        end
    else
        # Local mode: get worktree path from git directly
        set worktree_path (git worktree list --porcelain 2>/dev/null | awk -v branch="$branch" '
            /^worktree / { path=$2 }
            /^branch / && $2 == "refs/heads/"branch { print path; exit }
        ')
    end

    if test -z "$worktree_path"
        if test -z "$branch"
            echo "Error: No worktree found (not in a git repository?)" >&2
        else
            echo "Error: No worktree found for branch '$branch'" >&2
        end
        return 1
    end

    if test -d "$worktree_path"
        cd "$worktree_path"; or return 1
        echo "Switched to worktree: $worktree_path"
    else
        echo "Error: Worktree directory not found: $worktree_path" >&2
        return 1
    end
end

# Tab completion for cw-cd
# Complete -g/--global flag
complete -c cw-cd -s g -l global -d 'Search all registered repositories'

# Complete branch names: global mode if -g is present, otherwise local git
complete -c cw-cd -f -n '__fish_contains_opt -s g global' -a '(cw _path --list-branches -g 2>/dev/null)'
complete -c cw-cd -f -n 'not __fish_contains_opt -s g global' -a '(git worktree list --porcelain 2>/dev/null | grep "^branch " | sed "s|^branch refs/heads/||" | sort -u)'
