"""
Developer clean command for TinyTorch CLI.

Wraps the project's make-based clean target so tools can call
Tito instead of raw make commands.

Usage:
    tito dev clean          Clean all generated files (project root)
"""

import subprocess
from argparse import ArgumentParser, Namespace

from tren.commands.base import BaseCommand


class DevCleanCommand(BaseCommand):
    """Developer clean command — removes build artifacts."""

    @property
    def name(self) -> str:
        return "clean"

    @property
    def description(self) -> str:
        return "Clean build artifacts"

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            'target',
            nargs='?',
            default='all',
            choices=['all'],
            help='What to clean: all (default)'
        )

    def run(self, args: Namespace) -> int:
        console = self.console
        cwd = self.config.project_root
        console.print("[cyan]🧹 Cleaning all generated files...[/cyan]")

        # `make` isn't bundled with Git Bash on Windows (unlike git/python,
        # it has no equivalent auto-installed fallback), so this is a very
        # reachable crash for any Windows user without WSL or a separate
        # make install: subprocess.run raises FileNotFoundError with no
        # indication of *why*, rather than something recognizable as
        # "install this tool".
        try:
            result = subprocess.run(['make', 'clean'], cwd=str(cwd))
        except FileNotFoundError:
            console.print("[red]❌ 'make' is not installed or not on your PATH[/red]")
            console.print("  This command needs GNU Make to run its clean targets.")
            console.print("  Windows: install via 'choco install make', WSL, or Git Bash's own")
            console.print("           MinGW package manager.")
            console.print("  macOS/Linux: usually preinstalled, or 'brew install make' / 'apt install make'.")
            return 1

        return result.returncode
