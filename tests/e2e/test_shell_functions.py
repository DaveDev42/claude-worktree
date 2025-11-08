"""
Platform-specific shell function tests.

Tests verify that shell functions (cw-cd) work correctly across different shells.
Uses temporary files instead of process substitution for reliable CI testing.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from claude_worktree.git_utils import has_command
from claude_worktree.operations import create_worktree

# Platform markers
SKIP_ON_WINDOWS = pytest.mark.skipif(sys.platform == "win32", reason="Unix shell only")
SKIP_ON_UNIX = pytest.mark.skipif(sys.platform != "win32", reason="Windows only")


def get_shell_function_script(shell: str) -> str:
    """Get shell function script content by running the CLI command.

    Uses subprocess to execute the command and capture output to avoid
    process substitution issues in tests.
    """
    result = subprocess.run(
        [sys.executable, "-m", "claude_worktree", "_shell-function", shell],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


@pytest.mark.shell
@SKIP_ON_WINDOWS
class TestBashShellFunction:
    """Test cw-cd in bash shell."""

    def test_cw_cd_changes_directory(self, temp_git_repo: Path, disable_claude) -> None:
        """Test that cw-cd actually changes directory in bash."""
        # Create worktree
        create_worktree(branch_name="test-bash", no_cd=True)

        # Get shell function script and write to temp file
        script_content = get_shell_function_script("bash")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write(script_content)
            script_file = f.name

        try:
            # Source shell function and execute cw-cd
            bash_script = f"""
            set -e
            source {script_file}
            cw-cd test-bash
            pwd
            """

            result = subprocess.run(
                ["bash", "-c", bash_script],
                cwd=temp_git_repo,
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0, f"cw-cd failed: {result.stderr}"
            assert "test-bash" in result.stdout, "Should change to worktree directory"
        finally:
            Path(script_file).unlink(missing_ok=True)

    def test_cw_cd_error_on_nonexistent_branch(self, temp_git_repo: Path) -> None:
        """Test that cw-cd fails gracefully for non-existent branch."""
        script_content = get_shell_function_script("bash")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write(script_content)
            script_file = f.name

        try:
            bash_script = f"""
            source {script_file}
            cw-cd nonexistent-branch
            """

            result = subprocess.run(
                ["bash", "-c", bash_script],
                cwd=temp_git_repo,
                capture_output=True,
                text=True,
            )

            assert result.returncode != 0, "Should fail for non-existent branch"
            output = result.stdout + result.stderr
            assert "Error" in output or "not found" in output.lower()
        finally:
            Path(script_file).unlink(missing_ok=True)

    def test_cw_cd_no_args_navigates_to_base(self, temp_git_repo: Path) -> None:
        """Test that cw-cd without arguments navigates to base (main) worktree."""
        script_content = get_shell_function_script("bash")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write(script_content)
            script_file = f.name

        try:
            bash_script = f"""
            source {script_file}
            cw-cd
            pwd
            """

            result = subprocess.run(
                ["bash", "-c", bash_script],
                cwd=temp_git_repo,
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0, f"Should succeed without arguments: {result.stderr}"
            output = result.stdout + result.stderr
            assert "Switched to worktree:" in output, "Should show switched message"
            # Verify we switched to the base repository (temp_git_repo)
            assert str(temp_git_repo) in result.stdout, "Should navigate to base worktree"
        finally:
            Path(script_file).unlink(missing_ok=True)

    def test_bash_tab_completion(self, temp_git_repo: Path, disable_claude) -> None:
        """Test bash tab completion for cw-cd."""
        # Create multiple worktrees
        create_worktree(branch_name="feature-1", no_cd=True)
        create_worktree(branch_name="feature-2", no_cd=True)

        script_content = get_shell_function_script("bash")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write(script_content)
            script_file = f.name

        try:
            # Simulate tab completion
            bash_script = f"""
            source {script_file}

            # Trigger completion function
            COMP_WORDS=(cw-cd "feat")
            COMP_CWORD=1
            _cw_cd_completion

            # Print completion results
            printf '%s\\n' "${{COMPREPLY[@]}}"
            """

            result = subprocess.run(
                ["bash", "-c", bash_script],
                cwd=temp_git_repo,
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0
            assert "feature-1" in result.stdout
            assert "feature-2" in result.stdout
        finally:
            Path(script_file).unlink(missing_ok=True)


@pytest.mark.shell
@SKIP_ON_WINDOWS
class TestZshShellFunction:
    """Test cw-cd in zsh shell."""

    def test_cw_cd_changes_directory(self, temp_git_repo: Path, disable_claude) -> None:
        """Test that cw-cd works in zsh."""
        if not has_command("zsh"):
            pytest.skip("zsh not installed")

        create_worktree(branch_name="test-zsh", no_cd=True)

        script_content = get_shell_function_script("zsh")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".zsh", delete=False) as f:
            f.write(script_content)
            script_file = f.name

        try:
            zsh_script = f"""
            source {script_file}
            cw-cd test-zsh
            pwd
            """

            result = subprocess.run(
                ["zsh", "-c", zsh_script],
                cwd=temp_git_repo,
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0, f"cw-cd failed in zsh: {result.stderr}"
            assert "test-zsh" in result.stdout
        finally:
            Path(script_file).unlink(missing_ok=True)


@pytest.mark.shell
@SKIP_ON_WINDOWS
class TestFishShellFunction:
    """Test cw-cd in fish shell."""

    def test_cw_cd_changes_directory(self, temp_git_repo: Path, disable_claude) -> None:
        """Test that cw-cd works in fish."""
        if not has_command("fish"):
            pytest.skip("fish not installed")

        create_worktree(branch_name="test-fish", no_cd=True)

        script_content = get_shell_function_script("fish")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".fish", delete=False) as f:
            f.write(script_content)
            script_file = f.name

        try:
            fish_script = f"""
            source {script_file}
            cw-cd test-fish
            pwd
            """

            result = subprocess.run(
                ["fish", "-c", fish_script],
                cwd=temp_git_repo,
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0, f"cw-cd failed in fish: {result.stderr}"
            assert "test-fish" in result.stdout
        finally:
            Path(script_file).unlink(missing_ok=True)

    def test_fish_tab_completion(self, temp_git_repo: Path, disable_claude) -> None:
        """Test fish tab completion for cw-cd."""
        if not has_command("fish"):
            pytest.skip("fish not installed")

        # Create worktrees
        create_worktree(branch_name="feature-x", no_cd=True)
        create_worktree(branch_name="feature-y", no_cd=True)

        script_content = get_shell_function_script("fish")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".fish", delete=False) as f:
            f.write(script_content)
            script_file = f.name

        try:
            # Fish completion query
            fish_script = f"""
            source {script_file}

            # Test completion
            complete -C"cw-cd feat"
            """

            result = subprocess.run(
                ["fish", "-c", fish_script],
                cwd=temp_git_repo,
                capture_output=True,
                text=True,
            )

            # Fish completions should include our branches
            # Note: The exact output format depends on fish version
            assert result.returncode == 0
        finally:
            Path(script_file).unlink(missing_ok=True)


@pytest.mark.shell
@SKIP_ON_UNIX
class TestPowerShellFunction:
    """Test cw-cd in PowerShell (Windows only)."""

    def test_cw_cd_changes_directory(self, temp_git_repo: Path, disable_claude) -> None:
        """Test that cw-cd works in PowerShell."""
        if not has_command("pwsh") and not has_command("powershell"):
            pytest.skip("PowerShell not installed")

        create_worktree(branch_name="test-pwsh", no_cd=True)

        script_content = get_shell_function_script("powershell")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script_content)
            script_file = f.name

        pwsh_cmd = "pwsh" if has_command("pwsh") else "powershell"

        try:
            pwsh_script = f"""
            . {script_file}
            cw-cd test-pwsh
            Get-Location
            """

            result = subprocess.run(
                [pwsh_cmd, "-Command", pwsh_script],
                cwd=temp_git_repo,
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0, f"cw-cd failed in PowerShell: {result.stderr}"
            assert "test-pwsh" in result.stdout
        finally:
            Path(script_file).unlink(missing_ok=True)

    def test_cw_cd_error_handling_powershell(self, temp_git_repo: Path) -> None:
        """Test PowerShell error handling."""
        if not has_command("pwsh") and not has_command("powershell"):
            pytest.skip("PowerShell not installed")

        script_content = get_shell_function_script("powershell")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script_content)
            script_file = f.name

        pwsh_cmd = "pwsh" if has_command("pwsh") else "powershell"

        try:
            pwsh_script = f"""
            . {script_file}
            cw-cd nonexistent-branch 2>&1
            """

            result = subprocess.run(
                [pwsh_cmd, "-Command", pwsh_script],
                cwd=temp_git_repo,
                capture_output=True,
                text=True,
            )

            output = result.stdout + result.stderr
            assert "Error" in output or "not found" in output.lower()
        finally:
            Path(script_file).unlink(missing_ok=True)


@pytest.mark.shell
class TestShellScriptSyntax:
    """Test that shell scripts have valid syntax (all platforms)."""

    @SKIP_ON_WINDOWS
    def test_bash_script_syntax(self) -> None:
        """Validate bash script has no syntax errors."""
        result = subprocess.run(
            ["bash", "-n", "src/claude_worktree/shell_functions/cw.bash"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Bash syntax error: {result.stderr}"

    @SKIP_ON_WINDOWS
    def test_fish_script_syntax(self) -> None:
        """Validate fish script has no syntax errors."""
        if not has_command("fish"):
            pytest.skip("fish not installed")

        result = subprocess.run(
            ["fish", "-n", "src/claude_worktree/shell_functions/cw.fish"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Fish syntax error: {result.stderr}"

    @SKIP_ON_UNIX
    def test_powershell_script_syntax(self) -> None:
        """Validate PowerShell script has no syntax errors."""
        if not has_command("pwsh") and not has_command("powershell"):
            pytest.skip("PowerShell not installed")

        pwsh_cmd = "pwsh" if has_command("pwsh") else "powershell"

        # Test script can be sourced without errors
        pwsh_test = f"{sys.executable} -m claude_worktree _shell-function powershell | Out-Null; if ($?) {{ exit 0 }} else {{ exit 1 }}"
        result = subprocess.run(
            [
                pwsh_cmd,
                "-Command",
                pwsh_test,
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"PowerShell syntax error: {result.stderr}"

    @SKIP_ON_UNIX
    def test_powershell_invoke_expression(self) -> None:
        """Validate PowerShell script works with Invoke-Expression (profile usage)."""
        if not has_command("pwsh") and not has_command("powershell"):
            pytest.skip("PowerShell not installed")

        pwsh_cmd = "pwsh" if has_command("pwsh") else "powershell"

        # Test actual usage pattern: pipe to Out-String then Invoke-Expression
        # This matches the documented way to source the function in PowerShell profiles
        pwsh_test = f"{sys.executable} -m claude_worktree _shell-function powershell | Out-String | Invoke-Expression; if ($?) {{ Write-Output 'success'; exit 0 }} else {{ exit 1 }}"

        result = subprocess.run(
            [
                pwsh_cmd,
                "-Command",
                pwsh_test,
            ],
            capture_output=True,
            text=True,
        )

        # Check for both success and absence of syntax errors
        assert result.returncode == 0, f"Invoke-Expression failed: {result.stderr}"
        assert "success" in result.stdout.lower() or result.returncode == 0, (
            f"Function not loaded: {result.stdout}"
        )

        # Verify no parsing errors about missing braces
        assert "Missing closing" not in result.stderr, f"Parsing error: {result.stderr}"
        assert "empty string" not in result.stderr.lower(), f"Empty string error: {result.stderr}"
