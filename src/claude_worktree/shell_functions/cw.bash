# claude-worktree shell functions for bash/zsh
# Source this file to enable shell functions:
#   source <(cw _shell-function bash)

# Navigate to a worktree by branch name
# If no argument is provided, navigate to the base (main) worktree
cw-cd() {
    local branch="$1"
    local worktree_path

    if [ $# -eq 0 ]; then
        # No argument - navigate to base (main) worktree
        worktree_path=$(git worktree list --porcelain 2>/dev/null | awk '
            /^worktree / { print $2; exit }
        ')
    else
        # Argument provided - navigate to specified branch worktree
        worktree_path=$(git worktree list --porcelain 2>/dev/null | awk -v branch="$branch" '
            /^worktree / { path=$2 }
            /^branch / && $2 == "refs/heads/"branch { print path; exit }
        ')
    fi

    if [ -z "$worktree_path" ]; then
        if [ $# -eq 0 ]; then
            echo "Error: No worktree found (not in a git repository?)" >&2
        else
            echo "Error: No worktree found for branch '$branch'" >&2
        fi
        return 1
    fi

    if [ -d "$worktree_path" ]; then
        cd "$worktree_path" || return 1
        echo "Switched to worktree: $worktree_path"
    else
        echo "Error: Worktree directory not found: $worktree_path" >&2
        return 1
    fi
}

# Tab completion for cw-cd
_cw_cd_completion() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local branches

    # Get list of worktree branches directly from git
    branches=$(git worktree list --porcelain 2>/dev/null | grep "^branch " | sed 's/^branch refs\/heads\///' | sort -u)

    COMPREPLY=($(compgen -W "$branches" -- "$cur"))
}

# Register completion for bash
if [ -n "$BASH_VERSION" ]; then
    complete -F _cw_cd_completion cw-cd
fi

# Tab completion for zsh
if [ -n "$ZSH_VERSION" ]; then
    _cw_cd_zsh() {
        local branches
        branches=($(git worktree list --porcelain 2>/dev/null | grep "^branch " | sed 's/^branch refs\/heads\///' | sort -u))
        _describe 'worktree branches' branches
    }
    compdef _cw_cd_zsh cw-cd
fi
