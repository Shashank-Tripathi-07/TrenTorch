"""
TUI command wrapper for TrenTorch CLI.
"""

from argparse import ArgumentParser, Namespace

from platforms.cli.commands.base import BaseCommand


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
        try:
            from .app import launch_tui
        except ModuleNotFoundError as exc:
            missing = (exc.name or "").split(".")[0]
            if missing != "textual" and "textual" not in str(exc):
                raise
            self.console.print(
                "[red]❌ The interactive TUI needs the optional 'textual' dependency.[/red]\n"
                "[dim]Install it with:[/dim] [bold]pip install trentorch\\[tui][/bold]"
            )
            return 1

        selected_module = getattr(args, "module", None)
        return launch_tui(self.config, initial_module=selected_module)
