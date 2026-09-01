"""
TinyTorch CLI Main Entry Point

A professional command-line interface with proper architecture:
- Clean separation of concerns
- Proper error handling
- Logging support
- Configuration management
- Extensible command system
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Windows opens stdout/stderr with the console's legacy codepage (e.g. cp1252),
# not UTF-8, so emoji output crashes with UnicodeEncodeError unless the
# already-open streams are reconfigured directly (setting PYTHONIOENCODING
# here is too late to affect them).


def _is_windows(platform: str, os_name: str) -> bool:
    """Whether stdout/stderr need UTF-8 reconfiguration for this platform.

    Pulled out of the top-level if so it's callable directly with fake
    platform/os_name values in a test -- the original inline check could
    only be exercised by reloading this whole module under a monkeypatched
    sys.platform/os.name, which cascades into re-running every import below
    (including export_utils.py's module-level Path(...) default argument)
    and crashes on a real Windows filesystem.
    """
    return platform == "win32" or os_name == "nt"


if _is_windows(sys.platform, os.name):
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")

# Set TINYTORCH_QUIET before any tinytorch imports to suppress autograd messages
os.environ["TINYTORCH_QUIET"] = "1"

from platforms.cli.cli_platform.dev import DevCommand
from platforms.cli.cli_platform.package import PackageCommand
from platforms.cli.cli_platform.setup import SetupCommand
from platforms.cli.cli_platform.system import SystemCommand
from platforms.cli.processes.benchmark import BenchmarkCommand
from platforms.cli.processes.convert import ConvertCommand
from platforms.cli.processes.milestone import MilestoneCommand
from platforms.cli.processes.module_workflow import ModuleWorkflowCommand
from platforms.cli.processes.olympics import OlympicsCommand
from platforms.cli.server import ServeCommand
from platforms.cli.tui import TUICommand

from .commands.base import BaseCommand
from .core.config import CLIConfig, migrate_progress_dir
from .core.console import Panel, get_console, print_ascii_logo, print_banner, print_error
from .core.exceptions import TinyTorchCLIError
from .core.theme import Theme
from .core.virtual_env_manager import get_venv_path


# Get version from pyproject.toml (single source of truth)
def _get_version() -> str:
    """Read version from pyproject.toml."""
    try:
        # Try to find pyproject.toml relative to this file.
        # This file lives at platforms/cli/main.py, and pyproject.toml is at
        # the repo root -- two levels up from this file's own directory, not one.
        cli_dir = Path(__file__).parent
        pyproject_path = cli_dir.parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            content = pyproject_path.read_text()
            for line in content.splitlines():
                if line.strip().startswith("version"):
                    # Parse: version = "0.1.4"
                    return line.split("=")[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return "unknown"


__version__ = _get_version()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("tren-cli.log"), logging.StreamHandler(sys.stderr)],
)

logger = logging.getLogger(__name__)


class TrenTorchCLI:
    """Main CLI application class."""

    def __init__(self):
        """Initialize the CLI application."""
        self.config = CLIConfig.from_project_root()
        migrate_progress_dir(self.config.project_root)
        self.console = get_console()
        self._user_data_dir = self.config.project_root / "user_data"
        # SINGLE SOURCE OF TRUTH: All valid commands registered here
        self.commands: dict[str, type[BaseCommand]] = {
            # Interactive Interfaces
            "tui": TUICommand,
            "dashboard": TUICommand,
            "serve": ServeCommand,
            # Essential
            "setup": SetupCommand,
            # Workflow (student-facing)
            "system": SystemCommand,
            "module": ModuleWorkflowCommand,
            # Developer tools
            "dev": DevCommand,
            "package": PackageCommand,
            # Progress tracking
            "milestone": MilestoneCommand,
            "benchmark": BenchmarkCommand,
            "olympics": OlympicsCommand,
            "convert": ConvertCommand,
        }

        # Command categorization for help display
        self.student_commands = ["tui", "serve", "module", "milestone", "benchmark", "olympics"]
        self.developer_commands = ["dev", "system", "package"]

        # Welcome screen sections (used for both tren and tren --help)
        self.welcome_sections = {
            "quick_start": [
                (
                    f"[{Theme.CAT_QUICKSTART}]tren tui[/{Theme.CAT_QUICKSTART}]",
                    "Launch interactive visual TUI dashboard",
                ),
                (
                    f"[{Theme.CAT_QUICKSTART}]tren serve[/{Theme.CAT_QUICKSTART}]",
                    "Launch visualizer Web UI (http://localhost:8080)",
                ),
                (
                    f"[{Theme.CAT_QUICKSTART}]tren setup[/{Theme.CAT_QUICKSTART}]",
                    "First-time setup (includes verification)",
                ),
                (
                    f"[{Theme.CAT_QUICKSTART}]tren module start 01[/{Theme.CAT_QUICKSTART}]",
                    "Start Module 01 (tensors)",
                ),
                (
                    f"[{Theme.CAT_QUICKSTART}]tren module complete 01[/{Theme.CAT_QUICKSTART}]",
                    "Test, export, and track progress",
                ),
            ],
            "track_progress": [
                (f"[{Theme.CAT_PROGRESS}]tren module status[/{Theme.CAT_PROGRESS}]", "View module progress"),
                (
                    f"[{Theme.CAT_PROGRESS}]tren milestone status[/{Theme.CAT_PROGRESS}]",
                    "View unlocked capabilities",
                ),
            ],
            "help_docs": [
                (f"[{Theme.CAT_HELP}]tren system health[/{Theme.CAT_HELP}]", "Check environment health"),
                (f"[{Theme.CAT_HELP}]tren --help[/{Theme.CAT_HELP}]", "See all commands"),
            ],
        }

    def _generate_welcome_text(self) -> str:
        """Generate dynamic welcome text for interactive mode."""
        lines = []

        # Quick Start
        lines.append(f"[{Theme.SECTION}]Quick Start:[/{Theme.SECTION}]")
        for cmd, desc in self.welcome_sections["quick_start"]:
            lines.append(f"  {cmd:<38} {desc}")

        # Track Progress
        lines.append(f"\n[{Theme.SECTION}]Track Progress:[/{Theme.SECTION}]")
        for cmd, desc in self.welcome_sections["track_progress"]:
            lines.append(f"  {cmd:<38} {desc}")

        # Help & Docs
        lines.append(f"\n[{Theme.SECTION}]Help & Docs:[/{Theme.SECTION}]")
        for cmd, desc in self.welcome_sections["help_docs"]:
            lines.append(f"  {cmd:<38} {desc}")

        return "\n".join(lines)

    def _is_first_run(self) -> bool:
        """Check if this is the first time running tito."""
        return not self._user_data_dir.exists()

    def _mark_welcome_shown(self) -> None:
        """Mark that the welcome message has been shown by creating user_data/ folder."""
        self._user_data_dir.mkdir(parents=True, exist_ok=True)

    def _show_first_run_welcome(self) -> None:
        """Show a one-time welcome message for new users."""
        if not self._is_first_run():
            return

        from rich import box

        welcome_text = f"""[{Theme.EMPHASIS}]🎓 LEARNING APPROACH[/{Theme.EMPHASIS}]

Each notebook is stub-only: you write the real code. [bold]No solutions included![/bold]

The best way to learn:
  [{Theme.SUCCESS}]1.[/{Theme.SUCCESS}] Read the module's docstrings and hints closely
  [{Theme.SUCCESS}]2.[/{Theme.SUCCESS}] Implement each stub yourself -- match PyTorch's own
     API names where a hint suggests one, so your code stays portable
  [{Theme.SUCCESS}]3.[/{Theme.SUCCESS}] Run [{Theme.INFO}]tren module complete[/{Theme.INFO}] -- your own code is what gets tested and exported
     [{Theme.DIM}](reset with: tren module reset)[/{Theme.DIM}]

[{Theme.WARNING}]🐛 PRE-RELEASE:[/{Theme.WARNING}] We're looking for bugs and feedback!
   Found something? → [{Theme.INFO}]github.com/harvard-edge/cs249r_book/discussions[/{Theme.INFO}]"""

        self.console.print()
        self.console.print(
            Panel(
                welcome_text,
                title="[bold]Welcome to TrenTorch (Pre-release)[/bold]",
                border_style=Theme.BORDER_WELCOME,
                box=box.ROUNDED,
            )
        )
        self.console.print()

        # Mark as shown so it only appears once
        self._mark_welcome_shown()

    def _generate_epilog(self) -> str:
        """Generate dynamic epilog from registered commands."""
        lines = []

        # Student Commands section
        lines.append("Student Commands:")
        for cmd_name in self.student_commands:
            if cmd_name in self.commands:
                cmd = self.commands[cmd_name](self.config)
                # Simplify description for epilog (first sentence or shorter version)
                desc = cmd.description.split(".")[0].split("-")[0].strip()
                lines.append(f"  {cmd_name:<12} {desc}")
        lines.append("")

        # Developer Commands section
        lines.append("Developer Commands:")
        for cmd_name in self.developer_commands:
            if cmd_name in self.commands:
                cmd = self.commands[cmd_name](self.config)
                desc = cmd.description.split(".")[0].split("-")[0].strip()
                lines.append(f"  {cmd_name:<12} {desc}")
        lines.append("")

        # Quick Start section (strip Rich formatting for plain text)
        lines.append("Quick Start:")
        for cmd, desc in self.welcome_sections["quick_start"]:
            # Remove Rich color tags for plain epilog
            plain_cmd = cmd.replace("[green]", "").replace("[/green]", "")
            lines.append(f"  {plain_cmd:<28} {desc}")

        return "\n".join(lines)

    def create_parser(self) -> argparse.ArgumentParser:
        """Create the main argument parser."""
        parser = argparse.ArgumentParser(
            prog="tren",
            description="Tren⚡️Torch CLI - Build ML systems from scratch",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=self._generate_epilog(),
        )

        # Global options
        parser.add_argument("--version", action="version", version=f"Tren⚡️Torch v{__version__}")
        parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
        parser.add_argument("--no-color", action="store_true", help="Disable colored output")
        parser.add_argument(
            "--tui", "-i", action="store_true", help="Launch interactive Textual TUI dashboard"
        )

        # Subcommands
        subparsers = parser.add_subparsers(dest="command", help="Available commands", metavar="COMMAND")

        # Add command parsers
        for command_name, command_class in self.commands.items():
            # Create temporary instance to get metadata
            temp_command = command_class(self.config)
            cmd_parser = subparsers.add_parser(
                command_name,
                help=temp_command.description,
                formatter_class=argparse.RawDescriptionHelpFormatter,
            )
            temp_command.add_arguments(cmd_parser)

        return parser

    def validate_environment(self) -> bool:
        """Validate the environment and show issues if any."""
        issues = self.config.validate(get_venv_path())

        if issues:
            print_error(
                "Environment validation failed:\n" + "\n".join(f"  • {issue}" for issue in issues),
                "Environment Issues",
            )
            self.console.print("\n[dim]Run 'tren system health' for detailed diagnosis[/dim]")
            # Return True to allow command execution despite validation issues
            # This is temporary for development
            return True

        return True

    def _show_help(self) -> int:
        """Show custom Rich-formatted help."""
        from rich.table import Table

        # Show ASCII logo
        print_ascii_logo()

        # Create commands table
        table = Table(show_header=True, header_style=Theme.SECTION, box=None, padding=(0, 2))
        table.add_column("Command", style=Theme.COMMAND, width=15)
        table.add_column("Description", style=Theme.DIM)

        # Add all commands dynamically
        for cmd_name, cmd_class in self.commands.items():
            cmd = cmd_class(self.config)
            table.add_row(cmd_name, cmd.description)

        self.console.print()
        self.console.print(
            f"[{Theme.SECTION}]Tren⚡️Torch CLI[/{Theme.SECTION}] - Build ML systems from scratch"
        )
        self.console.print()
        self.console.print(
            f"[{Theme.EMPHASIS}]Usage:[/{Theme.EMPHASIS}] [{Theme.INFO}]tren[/{Theme.INFO}] [{Theme.OPTION}]COMMAND[/{Theme.OPTION}] [{Theme.DIM}][OPTIONS][/{Theme.DIM}]"
        )
        self.console.print()
        self.console.print(f"[{Theme.SECTION}]Available Commands:[/{Theme.SECTION}]")
        self.console.print(table)
        self.console.print()
        self.console.print(self._generate_welcome_text())
        self.console.print()
        self.console.print(f"[{Theme.SECTION}]Global Options:[/{Theme.SECTION}]")
        self.console.print(f"  [{Theme.OPTION}]--help, -h[/{Theme.OPTION}]      Show this help message")
        self.console.print(f"  [{Theme.OPTION}]--version[/{Theme.OPTION}]       Show version number")
        self.console.print(
            f"  [{Theme.OPTION}]--tui, -i[/{Theme.OPTION}]        Launch interactive TUI dashboard"
        )
        self.console.print(f"  [{Theme.OPTION}]--verbose, -v[/{Theme.OPTION}]   Enable verbose output")
        self.console.print(f"  [{Theme.OPTION}]--no-color[/{Theme.OPTION}]      Disable colored output")
        self.console.print()

        return 0

    def _check_invalid_command(self, args: list[str] | None) -> int | None:
        """Check for invalid commands and provide a helpful error message.

        Returns exit code if handled, None to continue normal parsing.
        """
        if not args:
            return None

        first_arg = args[0]

        # Skip flags (--help, --version, etc.)
        if first_arg.startswith("-"):
            return None

        # Check if it's an invalid command
        if first_arg.lower() not in self.commands:
            from rich.panel import Panel

            self.console.print()
            self.console.print(
                Panel(
                    f"[yellow]'{first_arg}' is not a valid command.[/yellow]\n\n"
                    f"[dim]Run 'tren --help' to see all available commands.[/dim]",
                    title="[bold]Command Not Found[/bold]",
                    border_style="yellow",
                )
            )
            self.console.print()
            return 1

        return None

    def run(self, args: list[str] | None = None) -> int:
        """Run the CLI application."""
        try:
            # Check for help flag before argparse to use Rich formatting
            if args and ("-h" in args or "--help" in args) and len(args) == 1:
                return self._show_help()

            # Check for invalid commands before argparse (cleaner error message)
            mistake_result = self._check_invalid_command(args)
            if mistake_result is not None:
                return mistake_result

            parser = self.create_parser()
            parsed_args = parser.parse_args(args)

            # Update config with global options
            if hasattr(parsed_args, "verbose") and parsed_args.verbose:
                self.config.verbose = True
                logging.getLogger().setLevel(logging.DEBUG)

            if hasattr(parsed_args, "no_color") and parsed_args.no_color:
                self.config.no_color = True

            # --tui / -i is a shortcut for the `tui` subcommand. Route it
            # through the normal command path so it gets the same venv guard,
            # environment validation, and banner as `tren tui`.
            if getattr(parsed_args, "tui", False) and not parsed_args.command:
                parsed_args.command = "tui"

            # Guard against running outside a virtual environment unless explicitly allowed
            if parsed_args.command not in ["setup", None]:
                # Check both sys.prefix (traditional activation) and VIRTUAL_ENV (direnv/PATH-based)
                in_venv = sys.prefix != sys.base_prefix or os.environ.get("VIRTUAL_ENV") is not None
                allow_system = (
                    os.environ.get("TREN_ALLOW_SYSTEM") == "1" or os.environ.get("TITO_ALLOW_SYSTEM") == "1"
                )
                if not in_venv and not allow_system:
                    print_error(
                        "TrenTorch must run inside a virtual environment.\n"
                        "Activate your project venv (for example, source .venv/bin/activate) "
                        "or set TREN_ALLOW_SYSTEM=1 to proceed at your own risk.",
                        "Virtual Environment Required",
                    )
                    return 1

            # Skip banner for machine-readable output (--json flag, module path)
            skip_banner = (hasattr(parsed_args, "json") and parsed_args.json) or (
                parsed_args.command == "module"
                and hasattr(parsed_args, "module_command")
                and parsed_args.module_command == "path"
            )
            if parsed_args.command and not self.config.no_color and not skip_banner:
                print_banner()
                # Show first-run welcome (only once, ever)
                self._show_first_run_welcome()

            # Validate environment for most commands (skip for health)
            skip_validation = parsed_args.command in [None, "version", "help"] or (
                parsed_args.command == "system"
                and hasattr(parsed_args, "system_command")
                and parsed_args.system_command == "health"
            )
            if not skip_validation:
                if not self.validate_environment():
                    return 1

            # Handle no command
            if not parsed_args.command:
                # Show ASCII logo first
                print_ascii_logo()

                # Show first-run welcome (only once, ever)
                self._show_first_run_welcome()

                # Generate dynamic welcome message
                self.console.print(
                    Panel(
                        self._generate_welcome_text(),
                        title="Welcome to Tren⚡️Torch!",
                        border_style=Theme.BORDER_WELCOME,
                    )
                )
                return 0

            # Execute command
            if parsed_args.command in self.commands:
                command_class = self.commands[parsed_args.command]
                command = command_class(self.config)
                return command.execute(parsed_args)
            else:
                print_error(f"Unknown command: {parsed_args.command}")
                return 1

        except KeyboardInterrupt:
            self.console.print(f"\n[{Theme.WARNING}]Operation cancelled by user[/{Theme.WARNING}]")
            return 130
        except TinyTorchCLIError as e:
            logger.error(f"CLI error: {e}")
            print_error(str(e))
            return 1
        except Exception as e:
            logger.exception("Unexpected error in CLI")
            print_error(f"Unexpected error: {e}")
            return 1


def main() -> int:
    """Main entry point for the CLI."""
    cli = TrenTorchCLI()
    return cli.run(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
