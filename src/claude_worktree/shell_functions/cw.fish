# claude-worktree shell functions for fish
# Source this file to enable shell functions:
#   cw _shell-function fish | source

# Navigate to a worktree by branch name
# If no argument is provided, navigate to the base (main) worktree
function cw-cd
    set -l worktree_path

    if test (count $argv) -eq 0
        # No argument - navigate to base (main) worktree
        set worktree_path (git worktree list --porcelain 2>/dev/null | awk '
            /^worktree / { print $2; exit }
        ')
    else
        # Argument provided - navigate to specified branch worktree
        set -l branch $argv[1]
        set worktree_path (git worktree list --porcelain 2>/dev/null | awk -v branch="$branch" '
            /^worktree / { path=$2 }
            /^branch / && $2 == "refs/heads/"branch { print path; exit }
        ')
    end

    if test -z "$worktree_path"
        if test (count $argv) -eq 0
            echo "Error: No worktree found (not in a git repository?)" >&2
        else
            echo "Error: No worktree found for branch '$argv[1]'" >&2
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
complete -c cw-cd -f -a '(git worktree list --porcelain 2>/dev/null | grep "^branch " | sed "s|^branch refs/heads/||" | sort -u)'
