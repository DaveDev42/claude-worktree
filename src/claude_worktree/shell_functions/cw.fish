# claude-worktree shell functions for fish
# Source this file to enable shell functions:
#   cw _shell-function fish | source

# Navigate to a worktree by branch name
function cw-cd
    if test (count $argv) -eq 0
        echo "Usage: cw-cd <branch-name>" >&2
        return 1
    end

    set -l branch $argv[1]
    set -l worktree_path (git worktree list --porcelain 2>/dev/null | awk -v branch="$branch" '
        /^worktree / { path=$2 }
        /^branch / && $2 == "refs/heads/"branch { print path; exit }
    ')

    if test -z "$worktree_path"
        echo "Error: No worktree found for branch '$branch'" >&2
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
