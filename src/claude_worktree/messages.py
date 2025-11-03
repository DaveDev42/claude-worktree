"""Standardized error and informational messages for claude-worktree."""


class ErrorMessages:
    """Centralized error message templates for consistency."""

    @staticmethod
    def worktree_not_found(branch: str) -> str:
        """
        Standard message when a worktree is not found for a branch.

        Args:
            branch: The branch name that was not found

        Returns:
            Formatted error message with helpful suggestion
        """
        return f"No worktree found for branch '{branch}'. Use 'cw list' to see available worktrees."

    @staticmethod
    def branch_not_found(branch: str) -> str:
        """
        Standard message when a branch does not exist.

        Args:
            branch: The branch name that was not found

        Returns:
            Formatted error message
        """
        return f"Branch '{branch}' not found"

    @staticmethod
    def invalid_branch_name(error_msg: str) -> str:
        """
        Standard message for invalid branch names.

        Args:
            error_msg: Specific error from git validation

        Returns:
            Formatted error message with helpful hints
        """
        return (
            f"Invalid branch name: {error_msg}\n"
            f"Hint: Use alphanumeric characters, hyphens, and slashes. "
            f"Avoid special characters like emojis, backslashes, or control characters."
        )

    @staticmethod
    def cannot_determine_branch() -> str:
        """
        Standard message when current branch cannot be determined.

        Returns:
            Formatted error message
        """
        return "Cannot determine current branch"

    @staticmethod
    def cannot_determine_base_branch() -> str:
        """
        Standard message when base branch cannot be determined.

        Returns:
            Formatted error message with helpful suggestion
        """
        return "Cannot determine base branch. Specify with --base or checkout a branch first."

    @staticmethod
    def missing_metadata(branch: str) -> str:
        """
        Standard message when worktree metadata is missing.

        Args:
            branch: The branch with missing metadata

        Returns:
            Formatted error message with helpful suggestion
        """
        return f"Missing metadata for branch '{branch}'. Was this worktree created with 'cw new'?"

    @staticmethod
    def base_repo_not_found(path: str) -> str:
        """
        Standard message when base repository is not found.

        Args:
            path: The expected path that doesn't exist

        Returns:
            Formatted error message
        """
        return f"Base repository not found at: {path}"

    @staticmethod
    def worktree_dir_not_found(path: str) -> str:
        """
        Standard message when worktree directory doesn't exist.

        Args:
            path: The expected directory path

        Returns:
            Formatted error message
        """
        return f"Worktree directory does not exist: {path}"

    @staticmethod
    def rebase_failed(
        worktree_path: str, rebase_target: str, conflicted_files: list[str] | None = None
    ) -> str:
        """
        Standard message when rebase fails.

        Args:
            worktree_path: Path to the worktree where rebase failed
            rebase_target: The branch/ref being rebased onto
            conflicted_files: Optional list of files with conflicts

        Returns:
            Formatted error message with resolution steps
        """
        msg = (
            f"Rebase failed. Please resolve conflicts manually:\n"
            f"  cd {worktree_path}\n"
            f"  git rebase {rebase_target}"
        )
        if conflicted_files:
            msg += f"\n\nConflicted files ({len(conflicted_files)}):"
            for file in conflicted_files:
                msg += f"\n  • {file}"
            msg += "\n\nTip: Use --ai-merge flag to get AI assistance with conflicts"
        return msg

    @staticmethod
    def merge_failed(base_path: str, feature_branch: str) -> str:
        """
        Standard message when fast-forward merge fails.

        Args:
            base_path: Path to the base repository
            feature_branch: The feature branch being merged

        Returns:
            Formatted error message with resolution steps
        """
        return (
            f"Fast-forward merge failed. Manual intervention required:\n"
            f"  cd {base_path}\n"
            f"  git merge {feature_branch}"
        )

    @staticmethod
    def pr_creation_failed(stderr: str) -> str:
        """
        Standard message when pull request creation fails.

        Args:
            stderr: Error output from gh command

        Returns:
            Formatted error message
        """
        return f"Failed to create pull request: {stderr}"

    @staticmethod
    def gh_cli_not_found() -> str:
        """
        Standard message when GitHub CLI is not installed.

        Returns:
            Formatted error message with installation link
        """
        return (
            "GitHub CLI (gh) is required to create pull requests.\n"
            "Install it from: https://cli.github.com/"
        )

    @staticmethod
    def cannot_delete_main_worktree() -> str:
        """
        Standard message when attempting to delete main repository worktree.

        Returns:
            Formatted error message
        """
        return "Cannot delete main repository worktree"

    @staticmethod
    def stash_not_found(stash_ref: str) -> str:
        """
        Standard message when a stash reference is not found.

        Args:
            stash_ref: The stash reference that doesn't exist

        Returns:
            Formatted error message with helpful suggestion
        """
        return f"Stash '{stash_ref}' not found. Use 'cw stash list' to see available stashes."

    @staticmethod
    def backup_not_found(backup_id: str, branch: str) -> str:
        """
        Standard message when a backup is not found.

        Args:
            backup_id: The backup identifier that doesn't exist
            branch: The branch the backup was expected for

        Returns:
            Formatted error message
        """
        return f"Backup '{backup_id}' not found for branch '{branch}'"

    @staticmethod
    def import_file_not_found(import_file: str) -> str:
        """
        Standard message when import file doesn't exist.

        Args:
            import_file: Path to the missing import file

        Returns:
            Formatted error message
        """
        return f"Import file not found: {import_file}"

    @staticmethod
    def detached_head_warning() -> str:
        """
        Standard warning message for detached HEAD state.

        Returns:
            Formatted warning message
        """
        return "Worktree is detached or branch not found. Specify branch with --branch or skip with --force."
