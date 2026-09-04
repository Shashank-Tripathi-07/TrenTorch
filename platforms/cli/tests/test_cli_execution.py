"""
CLI Execution Tests - Smoke tests for each command

This test suite ensures:
1. Each command can be executed without crashing (help mode)
2. Commands with subcommands show their subcommand help
3. Error messages are helpful when commands fail
"""

import subprocess
import sys
from pathlib import Path

import pytest

# Add tren to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from platforms.cli.main import TrenTorchCLI
from platforms.cli.tui.command import TUICommand


class TestCommandExecution:
    """Test that all commands can be executed (smoke tests)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cli = TrenTorchCLI()
        self.project_root = Path(__file__).parent.parent.parent.parent

    def test_bare_tren_command(self, force_first_run):
        """Test bare 'tren' command shows the one-time welcome screen on a
        student's first-ever run.

        A bare `tren` on any run after the first now launches the TUI
        directly instead (see test_bare_tren_routes_to_tui_after_first_run
        below), which would hang this subprocess call waiting for terminal
        input -- force_first_run deterministically avoids that regardless
        of whatever user_data/ state is left over from other commands run
        against this same checkout.
        """
        result = subprocess.run(
            [sys.executable, "-m", "platforms.cli.main"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )

        # Should exit successfully
        assert result.returncode == 0, f"Bare tren command failed: {result.stderr}"

        # Should show welcome message
        assert "Welcome to Tren" in result.stdout or "TORCH" in result.stdout
        assert "Command Groups:" in result.stdout or "Quick Start:" in result.stdout

    def test_bare_tren_routes_to_tui_after_first_run(self, monkeypatch):
        """Bare `tren` (no command, no flags) should launch the TUI
        directly once the student is past their first-ever run -- the
        whole point of this feature is that `tren` alone genuinely starts
        the app, not just prints a hint to run `tren tui`.

        Subclasses the real TUICommand (rather than a bare stand-in) so it
        still satisfies everything create_parser() needs from a registered
        command (description, add_arguments), and only swaps out run() to
        avoid actually entering the TUI's blocking event loop.
        """
        cli = TrenTorchCLI()
        monkeypatch.setattr(cli, "_is_first_run", lambda: False)

        launched = {}

        class _RecordingTUICommand(TUICommand):
            def run(self, args):
                launched["ran"] = True
                return 0

        cli.commands["tui"] = _RecordingTUICommand

        exit_code = cli.run([])

        assert exit_code == 0
        assert launched.get("ran") is True

    def test_bare_tren_shows_welcome_not_tui_on_first_run(self, monkeypatch):
        """A brand-new student's very first `tren` should show the
        onboarding welcome panel, not drop them straight into the TUI with
        no explanation of what TrenTorch is or how to use it."""
        cli = TrenTorchCLI()
        monkeypatch.setattr(cli, "_is_first_run", lambda: True)
        monkeypatch.setattr(cli, "_mark_welcome_shown", lambda: None)

        launched = {}

        class _RecordingTUICommand(TUICommand):
            def run(self, args):
                launched["ran"] = True
                return 0

        cli.commands["tui"] = _RecordingTUICommand

        exit_code = cli.run([])

        assert exit_code == 0
        assert "ran" not in launched

    def test_tren_help(self):
        """Test 'tren -h' shows help."""
        result = subprocess.run(
            [sys.executable, "-m", "platforms.cli.main", "-h"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        assert result.returncode == 0
        # Custom help displays logo and commands
        assert "TrenTorch" in result.stdout or "TORCH" in result.stdout
        assert "Quick Start" in result.stdout or "module" in result.stdout

    def test_tren_version(self):
        """Test 'tren --version' shows the real version from pyproject.toml,
        not just some Tren-ish text. "Tren" or "CLI" appearing anywhere in
        the output would pass just as well when the version lookup silently
        fails and falls back to "unknown" (issue #80) -- checking against
        pyproject.toml's own version string is what actually catches that."""
        result = subprocess.run(
            [sys.executable, "-m", "platforms.cli.main", "--version"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        pyproject_content = (self.project_root / "pyproject.toml").read_text(encoding="utf-8")
        real_version = next(
            line.split("=")[1].strip().strip('"').strip("'")
            for line in pyproject_content.splitlines()
            if line.strip().startswith("version")
        )

        assert result.returncode == 0
        assert real_version in result.stdout
        assert "unknown" not in result.stdout.lower()

    @pytest.mark.parametrize(
        "command", ["setup", "system", "module", "dev", "package", "milestone", "benchmark", "olympics"]
    )
    def test_command_help_works(self, command):
        """Test that each command's help can be displayed."""
        result = subprocess.run(
            [sys.executable, "-m", "platforms.cli.main", command, "-h"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        # Help should always succeed
        assert result.returncode == 0, (
            f"Command '{command} -h' failed with exit code {result.returncode}\nstderr: {result.stderr}"
        )

        # Should show usage
        assert "usage:" in result.stdout.lower(), f"Command '{command} -h' didn't show usage"

    @pytest.mark.parametrize(
        "command,subcommand",
        [
            ("system", "info"),
            ("system", "health"),
            ("module", "status"),
            ("module", "list"),
            ("milestone", "status"),
        ],
    )
    def test_subcommand_help_works(self, command, subcommand):
        """Test that subcommands can show help."""
        result = subprocess.run(
            [sys.executable, "-m", "platforms.cli.main", command, subcommand, "-h"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        # Subcommand help should work
        # Note: Some commands might return non-zero if not fully implemented
        # but should at least not crash
        assert result.returncode in [0, 1, 2], (
            f"Command '{command} {subcommand} -h' crashed with exit code {result.returncode}"
        )


class TestCommandGrouping:
    """Test that commands are properly grouped and discoverable."""

    def setup_method(self):
        """Set up test fixtures."""
        self.project_root = Path(__file__).parent.parent.parent.parent

    def test_student_facing_commands_discoverable(self, force_first_run):
        """Test that main student-facing commands are easily discoverable.

        force_first_run: bare `tren` after the first-ever run now launches
        the TUI directly instead of showing this welcome screen, which
        would hang this subprocess call waiting for terminal input.
        """
        result = subprocess.run(
            [sys.executable, "-m", "platforms.cli.main"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )

        # Key student commands should be visible
        student_commands = ["setup", "module", "milestone"]

        for cmd in student_commands:
            assert cmd in result.stdout, f"Student command '{cmd}' not visible in welcome screen"

    def test_developer_commands_documented(self):
        """Test that developer commands are documented in help."""
        result = subprocess.run(
            [sys.executable, "-m", "platforms.cli.main", "-h"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        # Developer commands should be in help
        dev_commands = ["dev", "package"]

        for cmd in dev_commands:
            assert cmd in result.stdout, f"Developer command '{cmd}' not in help text"


class TestErrorMessages:
    """Test that error messages are helpful."""

    def setup_method(self):
        """Set up test fixtures."""
        self.project_root = Path(__file__).parent.parent.parent.parent

    def test_invalid_command_shows_help(self):
        """Test that invalid commands show helpful error."""
        result = subprocess.run(
            [sys.executable, "-m", "platforms.cli.main", "nonexistent"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        # Should fail
        assert result.returncode != 0

        # Should mention the invalid command
        combined_output = result.stdout + result.stderr
        assert "nonexistent" in combined_output or "invalid choice" in combined_output.lower()

    def test_missing_subcommand_shows_help(self):
        """Test that missing subcommands show help."""
        # Try module command without subcommand
        result = subprocess.run(
            [sys.executable, "-m", "platforms.cli.main", "module"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        # Should show help or error
        # Some commands might have default behavior, others require subcommand
        combined_output = result.stdout + result.stderr
        assert len(combined_output) > 0, "No output from command without subcommand"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
