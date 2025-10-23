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
    set -l worktree_path (cw _path "$branch" 2>/dev/null)
    set -l exit_code $status

    if test $exit_code -ne 0
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
complete -c cw-cd -f -a '(cw list 2>/dev/null | awk \'NR>2 {print $1}\' | grep -v "^-" | sed \'s|refs/heads/||\')'
