"""
TUI command wrapper for TrenTorch CLI.
"""

from argparse import ArgumentParser, Namespace
from platforms.cli.commands.base import BaseCommand
from platforms.cli.core.config import CLIConfig


class TUICommand(BaseCommand):
    """Launch interactive Textual TUI dashboard for TrenTorch."""

    @property
    def name(self) -> str:
        return "tui"

    @property
    def description(self) -> str:
        return "Launch interactive Textual TUI dashboard for zero-friction learning"

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Add arguments for TUI command."""
        parser.add_argument(
            "--module",
            "-m",
            type=str,
            default=None,
            help="Pre-select specific module in the dashboard (e.g. 01, 06)",
        )

    def run(self, args: Namespace) -> int:
        """Run the TUI application."""
        from .app import launch_tui

        selected_module = getattr(args, "module", None)
        return launch_tui(self.config, initial_module=selected_module)
