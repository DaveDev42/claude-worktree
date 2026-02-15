# claude-worktree shell functions for bash/zsh
# Source this file to enable shell functions:
#   source <(cw _shell-function bash)

# Navigate to a worktree by branch name
# If no argument is provided, navigate to the base (main) worktree
# Use -g/--global to search across all registered repositories
cw-cd() {
    local branch=""
    local global_mode=0

    # Parse arguments
    while [ $# -gt 0 ]; do
        case "$1" in
            -g|--global)
                global_mode=1
                shift
                ;;
            -*)
                echo "Error: Unknown option '$1'" >&2
                echo "Usage: cw-cd [-g|--global] [branch]" >&2
                return 1
                ;;
            *)
                branch="$1"
                shift
                ;;
        esac
    done

    local worktree_path

    if [ $global_mode -eq 1 ]; then
        # Global mode: delegate to cw _path -g
        if [ -z "$branch" ]; then
            echo "Error: Branch name is required with -g/--global" >&2
            return 1
        fi
        worktree_path=$(cw _path -g "$branch")
        if [ $? -ne 0 ]; then
            return 1
        fi
    elif [ -z "$branch" ]; then
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
        if [ -z "$branch" ]; then
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
    local has_global=0

    # Check if -g or --global is already in the command
    local i
    for i in "${COMP_WORDS[@]}"; do
        case "$i" in
            -g|--global) has_global=1 ;;
        esac
    done

    # If current word starts with -, complete flags
    if [[ "$cur" == -* ]]; then
        COMPREPLY=($(compgen -W "-g --global" -- "$cur"))
        return
    fi

    local branches
    if [ $has_global -eq 1 ]; then
        # Global mode: get branches from all registered repos
        branches=$(cw _path --list-branches -g 2>/dev/null)
    else
        # Local mode: get branches directly from git
        branches=$(git worktree list --porcelain 2>/dev/null | grep "^branch " | sed 's/^branch refs\/heads\///' | sort -u)
    fi

    COMPREPLY=($(compgen -W "$branches" -- "$cur"))
}

# Register completion for bash
if [ -n "$BASH_VERSION" ]; then
    complete -F _cw_cd_completion cw-cd
fi

# Tab completion for zsh
if [ -n "$ZSH_VERSION" ]; then
    # Register Typer completion for cw CLI inline
    # (eliminates need for ~/.zfunc/_cw file and FPATH setup)
    _cw_completion() {
        eval $(env _TYPER_COMPLETE_ARGS="${words[1,$CURRENT]}" _CW_COMPLETE=complete_zsh cw)
    }
    compdef _cw_completion cw

    _cw_cd_zsh() {
        local has_global=0
        local i
        for i in "${words[@]}"; do
            case "$i" in
                -g|--global) has_global=1 ;;
            esac
        done

        # Complete flags
        if [[ "$PREFIX" == -* ]]; then
            local -a flags
            flags=('-g:Search all registered repositories' '--global:Search all registered repositories')
            _describe 'flags' flags
            return
        fi

        local -a branches
        if [ $has_global -eq 1 ]; then
            branches=(${(f)"$(cw _path --list-branches -g 2>/dev/null)"})
        else
            branches=(${(f)"$(git worktree list --porcelain 2>/dev/null | grep '^branch ' | sed 's/^branch refs\/heads\///' | sort -u)"})
        fi
        compadd -a branches
    }
    compdef _cw_cd_zsh cw-cd
fi
