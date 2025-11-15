#!/usr/bin/env python3
"""
Automated release script for claude-worktree.

Usage:
    python scripts/release.py               # Patch release (default, tests skipped)
    python scripts/release.py --minor       # Minor release (tests skipped)
    python scripts/release.py --major       # Major release (tests skipped)
    python scripts/release.py --run-tests   # Run tests locally before release
    python scripts/release.py --dry-run     # Simulate without changes

Note: Tests are skipped by default - GitHub Actions runs comprehensive tests on the PR.
"""

import argparse
import re
import subprocess
import sys
import tomllib
from enum import Enum
from pathlib import Path


class ReleaseType(Enum):
    """Semantic versioning release types."""

    PATCH = "patch"
    MINOR = "minor"
    MAJOR = "major"


class ReleaseError(Exception):
    """Base exception for release errors."""

    pass


def run_command(
    cmd: list[str], check: bool = True, capture_output: bool = False, dry_run: bool = False
) -> subprocess.CompletedProcess:
    """
    Run a shell command with optional dry-run mode.

    Args:
        cmd: Command and arguments as list
        check: Raise exception on non-zero exit
        capture_output: Capture stdout/stderr
        dry_run: If True, only print command without executing

    Returns:
        CompletedProcess instance

    Raises:
        ReleaseError: If command fails and check=True
    """
    cmd_str = " ".join(cmd)
    if dry_run:
        print(f"[DRY-RUN] Would run: {cmd_str}")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    print(f"Running: {cmd_str}")
    try:
        result = subprocess.run(cmd, check=check, capture_output=capture_output, text=True)
        return result
    except subprocess.CalledProcessError as e:
        raise ReleaseError(f"Command failed: {cmd_str}\n{e.stderr}") from e


def read_current_version() -> str:
    """
    Read current version from pyproject.toml.

    Returns:
        Version string (e.g., "0.10.8")

    Raises:
        ReleaseError: If pyproject.toml not found or version not found
    """
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        raise ReleaseError("pyproject.toml not found. Run from project root.")

    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)

    version = pyproject.get("project", {}).get("version")
    if not version:
        raise ReleaseError("Version not found in pyproject.toml")

    return version


def parse_version(version: str) -> tuple[int, int, int]:
    """
    Parse semantic version string into components.

    Args:
        version: Version string (e.g., "0.10.8")

    Returns:
        Tuple of (major, minor, patch)

    Raises:
        ReleaseError: If version format is invalid
    """
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version)
    if not match:
        raise ReleaseError(f"Invalid version format: {version}")

    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch)


def bump_version(current: str, release_type: ReleaseType) -> str:
    """
    Calculate new version based on release type.

    Args:
        current: Current version string
        release_type: Type of release (patch/minor/major)

    Returns:
        New version string

    Examples:
        >>> bump_version("0.10.8", ReleaseType.PATCH)
        "0.10.9"
        >>> bump_version("0.10.9", ReleaseType.MINOR)
        "0.11.0"
        >>> bump_version("0.11.5", ReleaseType.MAJOR)
        "1.0.0"
    """
    major, minor, patch = parse_version(current)

    if release_type == ReleaseType.MAJOR:
        major += 1
        minor = 0
        patch = 0
    elif release_type == ReleaseType.MINOR:
        minor += 1
        patch = 0
    else:  # PATCH
        patch += 1

    return f"{major}.{minor}.{patch}"


def check_git_status(dry_run: bool = False) -> None:
    """
    Check if git working tree is clean.

    Args:
        dry_run: If True, skip check

    Raises:
        ReleaseError: If working tree has uncommitted changes
    """
    if dry_run:
        print("[DRY-RUN] Would check git status")
        return

    result = run_command(["git", "status", "--porcelain"], capture_output=True, dry_run=False)
    if result.stdout.strip():
        raise ReleaseError("Working tree has uncommitted changes. Commit or stash them first.")


def run_tests(skip_tests: bool = True, dry_run: bool = False) -> None:
    """
    Run test suite with pytest.

    Args:
        skip_tests: If True, skip test execution (default: True - tests run in GitHub Actions)
        dry_run: If True, only simulate

    Raises:
        ReleaseError: If tests fail
    """
    if skip_tests:
        print("⚠️  Skipping tests (GitHub Actions will run them) - use --run-tests to run locally")
        return

    print("Running tests...")
    run_command(["uv", "run", "--extra", "dev", "pytest"], dry_run=dry_run)
    print("✅ All tests passed")


def update_pyproject_version(new_version: str, dry_run: bool = False) -> None:
    """
    Update version in pyproject.toml.

    Args:
        new_version: New version string
        dry_run: If True, only simulate

    Raises:
        ReleaseError: If update fails
    """
    pyproject_path = Path("pyproject.toml")

    if dry_run:
        print(f"[DRY-RUN] Would update pyproject.toml to version {new_version}")
        return

    with open(pyproject_path) as f:
        content = f.read()

    # Replace version line
    new_content = re.sub(
        r'^version = "[\d.]+"',
        f'version = "{new_version}"',
        content,
        flags=re.MULTILINE,
    )

    if content == new_content:
        raise ReleaseError("Failed to update version in pyproject.toml")

    with open(pyproject_path, "w") as f:
        f.write(new_content)

    print(f"✅ Updated pyproject.toml to version {new_version}")


def update_uv_lock(dry_run: bool = False) -> None:
    """
    Update uv.lock file.

    Args:
        dry_run: If True, only simulate

    Raises:
        ReleaseError: If lock update fails
    """
    print("Updating uv.lock...")
    run_command(["uv", "lock"], dry_run=dry_run)
    print("✅ Updated uv.lock")


def create_release_branch(version: str, dry_run: bool = False) -> str:
    """
    Create release branch.

    Args:
        version: Version string
        dry_run: If True, only simulate

    Returns:
        Branch name

    Raises:
        ReleaseError: If branch creation fails
    """
    branch_name = f"release/v{version}"
    run_command(["git", "checkout", "-b", branch_name], dry_run=dry_run)
    print(f"✅ Created branch {branch_name}")
    return branch_name


def commit_changes(version: str, dry_run: bool = False) -> None:
    """
    Commit version bump changes.

    Args:
        version: Version string
        dry_run: If True, only simulate

    Raises:
        ReleaseError: If commit fails
    """
    run_command(["git", "add", "pyproject.toml", "uv.lock"], dry_run=dry_run)
    run_command(["git", "commit", "-m", f"chore: Bump version to {version}"], dry_run=dry_run)
    print(f"✅ Committed version bump to {version}")


def push_branch(branch_name: str, dry_run: bool = False) -> None:
    """
    Push release branch to remote.

    Args:
        branch_name: Branch name
        dry_run: If True, only simulate

    Raises:
        ReleaseError: If push fails
    """
    run_command(["git", "push", "origin", branch_name], dry_run=dry_run)
    print(f"✅ Pushed branch {branch_name} to remote")


def create_pr(version: str, release_type: ReleaseType, dry_run: bool = False) -> None:
    """
    Create GitHub pull request.

    Args:
        version: Version string
        release_type: Type of release
        dry_run: If True, only simulate

    Raises:
        ReleaseError: If PR creation fails
    """
    title = f"chore: Release v{version}"
    body = f"Version bump for {release_type.value} release.\n\nRelease: v{version}"

    run_command(["gh", "pr", "create", "--title", title, "--body", body], dry_run=dry_run)
    print(f"✅ Created PR for release v{version}")


def main() -> None:
    """Main release automation workflow."""
    parser = argparse.ArgumentParser(
        description="Automated release script for claude-worktree",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/release.py               # Patch release (0.10.8 → 0.10.9, tests skipped)
  python scripts/release.py --minor       # Minor release (0.10.9 → 0.11.0, tests skipped)
  python scripts/release.py --major       # Major release (0.11.0 → 1.0.0, tests skipped)
  python scripts/release.py --run-tests   # Run tests locally before release
  python scripts/release.py --dry-run     # Simulate without changes

Note: Tests are skipped by default - GitHub Actions runs them automatically.
        """,
    )

    # Release type (mutually exclusive)
    release_group = parser.add_mutually_exclusive_group()
    release_group.add_argument("--minor", action="store_true", help="Minor version bump (x.N.0)")
    release_group.add_argument("--major", action="store_true", help="Major version bump (N.0.0)")

    # Options
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run tests before creating release (tests are skipped by default - GitHub Actions runs them)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate without making any changes",
    )

    args = parser.parse_args()

    # Determine release type
    if args.major:
        release_type = ReleaseType.MAJOR
    elif args.minor:
        release_type = ReleaseType.MINOR
    else:
        release_type = ReleaseType.PATCH

    try:
        print("🚀 Starting release automation...\n")

        # Step 1: Check git status
        print("Step 1: Checking git status...")
        check_git_status(dry_run=args.dry_run)

        # Step 2: Read current version
        print("\nStep 2: Reading current version...")
        current_version = read_current_version()
        new_version = bump_version(current_version, release_type)
        print(f"Current version: {current_version}")
        print(f"New version: {new_version} ({release_type.value} release)")

        # Step 3: Run tests (skip by default, run only if --run-tests flag is set)
        print("\nStep 3: Running tests...")
        run_tests(skip_tests=not args.run_tests, dry_run=args.dry_run)

        # Step 4: Update pyproject.toml
        print("\nStep 4: Updating pyproject.toml...")
        update_pyproject_version(new_version, dry_run=args.dry_run)

        # Step 5: Update uv.lock
        print("\nStep 5: Updating uv.lock...")
        update_uv_lock(dry_run=args.dry_run)

        # Step 6: Create release branch
        print("\nStep 6: Creating release branch...")
        branch_name = create_release_branch(new_version, dry_run=args.dry_run)

        # Step 7: Commit changes
        print("\nStep 7: Committing changes...")
        commit_changes(new_version, dry_run=args.dry_run)

        # Step 8: Push to remote
        print("\nStep 8: Pushing to remote...")
        push_branch(branch_name, dry_run=args.dry_run)

        # Step 9: Create PR
        print("\nStep 9: Creating pull request...")
        create_pr(new_version, release_type, dry_run=args.dry_run)

        # Success
        print("\n✅ Release automation completed successfully!")
        print("\n📋 Next steps:")
        print("   1. Review PR at: https://github.com/DaveDev42/claude-worktree/pulls")
        print("   2. Merge PR to trigger automated release workflow")
        print("   3. Monitor workflow at: https://github.com/DaveDev42/claude-worktree/actions")
        print("   4. Package will be automatically published to PyPI")

        if args.dry_run:
            print("\n⚠️  DRY-RUN mode: No actual changes were made")

    except ReleaseError as e:
        print(f"\n❌ Release failed: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Release interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
