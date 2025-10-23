# claude-worktree shell functions for bash/zsh
# Source this file to enable shell functions:
#   source <(cw _shell-function bash)

# Navigate to a worktree by branch name
cw-cd() {
    if [ $# -eq 0 ]; then
        echo "Usage: cw-cd <branch-name>" >&2
        return 1
    fi

    local branch="$1"
    local worktree_path

    # Get worktree path from cw _path command
    worktree_path=$(cw _path "$branch" 2>/dev/null)
    local exit_code=$?

    if [ $exit_code -ne 0 ]; then
        echo "Error: No worktree found for branch '$branch'" >&2
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

    # Get list of worktree branches
    branches=$(cw list 2>/dev/null | awk 'NR>2 {print $1}' | grep -v "^-" | sed 's/refs\/heads\///')

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
        branches=($(cw list 2>/dev/null | awk 'NR>2 {print $1}' | grep -v "^-" | sed 's/refs\/heads\///'))
        _describe 'worktree branches' branches
    }
    compdef _cw_cd_zsh cw-cd
fi
