# claude-worktree shell functions for fish
# Source this file to enable shell functions:
#   cw _shell-function fish | source

# Navigate to a worktree by branch name
# If no argument is provided, navigate to the base (main) worktree
# Use -g/--global to search across all registered repositories
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
                echo "Usage: cw-cd [-g|--global] [branch]" >&2
                return 1
            case '*'
                set branch $arg
        end
    end

    set -l worktree_path

    if test $global_mode -eq 1
        # Global mode: delegate to cw _path -g
        if test -z "$branch"
            echo "Error: Branch name is required with -g/--global" >&2
            return 1
        end
        set worktree_path (cw _path -g "$branch")
        if test $status -ne 0
            return 1
        end
    else if test -z "$branch"
        # No argument - navigate to base (main) worktree
        set worktree_path (git worktree list --porcelain 2>/dev/null | awk '
            /^worktree / { print $2; exit }
        ')
    else
        # Argument provided - navigate to specified branch worktree
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
