"""
Enhanced Module Workflow for TinyTorch CLI.

Implements the natural workflow:
1. tito module start 01 → Opens module 01 in Jupyter
2. Student works and saves
3. tito module complete 01 → Tests, exports, updates progress
"""

import os
import sys
import time
from argparse import ArgumentParser, Namespace
from pathlib import Path

from rich.panel import Panel
from rich.text import Text

from platforms.cli.commands.base import BaseCommand
from platforms.cli.commands.jupyter import open_jupyter
from platforms.cli.core.modules import (
    get_all_module_metadata,
    get_module_display_name,
    get_module_mapping,
    normalize_module_number,
)
from platforms.cli.processes.milestone import check_and_run_milestone_unlocks

from .reset import ModuleResetCommand
from .test import ModuleTestCommand
from .test_runner import check_notebook_syntax, run_inline_unit_tests, run_integration_tests

# One-off diagnostic instrumentation for finding out why some modules take
# far longer than others in `module complete` (e.g. Stage 1/Stage 7 in CI).
# Opt-in via TREN_PROFILE=1 so it never affects normal output; prints to
# stderr so it doesn't interleave with the CLI's own captured stdout.
_PROFILE = os.environ.get("TREN_PROFILE") == "1"


def _profile(module_name: str, step: str, duration: float) -> None:
    if _PROFILE:
        print(f"[TREN_PROFILE] {module_name} {step}: {duration:.2f}s", file=sys.stderr, flush=True)


class ModuleWorkflowCommand(BaseCommand):
    """Enhanced module command with natural workflow."""

    PRIMARY_EXPORT_LABELS = {
        "01": "Tensor",
        "02": "Activations",
        "03": "Linear",
        "04": "Losses",
        "05": "DataLoader",
        "06": "Autograd",
        "07": "Optimizers",
        "08": "Trainer",
        "09": "Spatial",
        "10": "Tokenizer",
        "11": "Embedding",
        "12": "Attention",
        "13": "Transformer",
        "14": "Profiler",
        "15": "Quantizer",
        "16": "Compressor",
        "17": "Acceleration",
        "18": "Memoization",
        "19": "Benchmark",
        "20": "Olympics",
    }

    @property
    def name(self) -> str:
        return "module"

    @property
    def description(self) -> str:
        return "Module development workflow - open, work, complete"

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Add module workflow arguments."""
        # Add subcommands - clean lifecycle workflow
        subparsers = parser.add_subparsers(dest="module_command", help="Module lifecycle operations")

        # START command - begin working on a module
        start_parser = subparsers.add_parser("start", help="Start working on a module (first time)")
        start_parser.add_argument("module_number", help="Module number to start (01, 02, 03, etc.)")
        start_parser.add_argument(
            "--no-jupyter",
            action="store_true",
            help="Create notebook but skip opening Jupyter (for CI/testing)",
        )
        start_parser.add_argument(
            "--notebook",
            action="store_true",
            help="Open in the classic Jupyter Notebook UI (skips the prompt)",
        )
        start_parser.add_argument("--lab", action="store_true", help="Open in Jupyter Lab (skips the prompt)")

        # VIEW command - just open the notebook
        view_parser = subparsers.add_parser(
            "view", help="Open module notebook in Jupyter (no status updates)"
        )
        view_parser.add_argument("module_number", help="Module number to view (01, 02, 03, etc.)")
        view_parser.add_argument(
            "--notebook",
            action="store_true",
            help="Open in the classic Jupyter Notebook UI (skips the prompt)",
        )
        view_parser.add_argument("--lab", action="store_true", help="Open in Jupyter Lab (skips the prompt)")

        # RESUME command - continue working on a module
        resume_parser = subparsers.add_parser(
            "resume", help="Resume working on a module (continue previous work)"
        )
        resume_parser.add_argument(
            "module_number",
            nargs="?",
            help="Module number to resume (01, 02, 03, etc.) - defaults to last worked",
        )
        resume_parser.add_argument(
            "--notebook",
            action="store_true",
            help="Open in the classic Jupyter Notebook UI (skips the prompt)",
        )
        resume_parser.add_argument(
            "--lab", action="store_true", help="Open in Jupyter Lab (skips the prompt)"
        )

        # COMPLETE command - finish and validate a module
        complete_parser = subparsers.add_parser(
            "complete", help="Complete module: run tests, export if passing, update progress"
        )
        complete_parser.add_argument(
            "module_number",
            nargs="?",
            help="Module number to complete (01, 02, 03, etc.) - defaults to current",
        )
        complete_parser.add_argument("--skip-tests", action="store_true", help="Skip integration tests")
        complete_parser.add_argument("--skip-export", action="store_true", help="Skip automatic export")
        complete_parser.add_argument(
            "--all", action="store_true", help="Complete all modules (test + export all)"
        )

        # TEST command - run module tests (three-phase testing)
        test_parser = subparsers.add_parser("test", help="Run module tests: inline → pytest → integration")
        test_parser.add_argument("module_number", nargs="?", help="Module number to test (01, 02, 03, etc.)")
        test_parser.add_argument("--all", action="store_true", help="Test all modules sequentially")
        test_parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed test output")
        test_parser.add_argument(
            "--stop-on-fail", action="store_true", help="Stop testing if a module fails (only with --all)"
        )
        test_parser.add_argument(
            "--unit-only",
            action="store_true",
            help="Run only inline unit tests (skip pytest and integration)",
        )
        test_parser.add_argument("--no-integration", action="store_true", help="Skip integration tests")

        # RESET command - reset module to clean state
        reset_parser = subparsers.add_parser("reset", help="Reset module to clean state")
        reset_parser.add_argument(
            "module_number", nargs="?", default=None, help="Module number to reset (01, 02, etc.)"
        )
        reset_parser.add_argument("--all", action="store_true", help="Reset ALL modules to pristine state")
        reset_parser.add_argument("--force", action="store_true", help="Skip confirmation prompts")

        # STATUS command - show progress
        subparsers.add_parser("status", help="Show module completion status and progress")

        # LIST command - show available modules
        list_parser = subparsers.add_parser("list", help="List all available modules")
        list_parser.add_argument("--json", action="store_true", help="Output as JSON (for IDE integrations)")

        # PATH command - get file paths for a module
        path_parser = subparsers.add_parser("path", help="Get file path for a module (for IDE integrations)")
        path_parser.add_argument("module_number", help="Module number (01, 02, etc.)")
        path_group = path_parser.add_mutually_exclusive_group(required=True)
        path_group.add_argument("--notebook", action="store_true", help="Path to module notebook (.ipynb)")
        path_group.add_argument("--source", action="store_true", help="Path to module source (.py)")

    # Module mapping and normalization now imported from core.modules

    def start_module(
        self, module_number: str, no_jupyter: bool = False, notebook: bool = False, lab: bool = False
    ) -> int:
        """Start working on a module with prerequisite checking and visual feedback.

        Args:
            module_number: The module to start (e.g., "01", "02")
            no_jupyter: If True, create notebook but don't open Jupyter (for CI/testing)
            notebook: --notebook was passed explicitly; open the classic UI, no prompt
            lab: --lab was passed explicitly; open Jupyter Lab, no prompt
        """
        from rich import box
        from rich.table import Table

        module_mapping = get_module_mapping()
        normalized = normalize_module_number(module_number)

        if normalized not in module_mapping:
            self.console.print(f"[red]❌ Module {normalized} not found[/red]")
            max_module = max(module_mapping.keys()) if module_mapping else "??"
            self.console.print(f"💡 Available modules: 01-{max_module}")
            return 1

        module_name = module_mapping[normalized]
        module_num = int(normalized)

        # Check if already started
        if self.is_module_started(normalized):
            self.console.print(f"[yellow]⚠️  Module {normalized} already started[/yellow]")
            self.console.print(f"💡 Did you mean: [bold cyan]tito module resume {normalized}[/bold cyan]")
            return 1

        # Check prerequisites - all previous modules must be completed
        progress = self.get_progress_data()
        completed = progress.get("completed_modules", [])

        # Module 01 has no prerequisites
        if module_num > 1:
            missing_prereqs = []
            for i in range(1, module_num):
                prereq_num = f"{i:02d}"
                if prereq_num not in completed:
                    missing_prereqs.append((prereq_num, module_mapping.get(prereq_num, "Unknown")))

            if missing_prereqs:
                # Show locked module panel
                self.console.print(
                    Panel(
                        f"[yellow]Module {normalized}: {module_name} is locked[/yellow]\n\n"
                        f"Complete the prerequisites first to unlock this module.",
                        title="🔒 Module Locked",
                        border_style="yellow",
                        box=box.ROUNDED,
                    )
                )
                self.console.print()

                # Show prerequisites table
                prereq_table = Table(
                    title="Prerequisites Required",
                    show_header=True,
                    header_style="bold yellow",
                    box=box.SIMPLE,
                )
                prereq_table.add_column("Module", style="cyan", width=8)
                prereq_table.add_column("Name", style="bold", width=20)
                prereq_table.add_column("Status", width=15, justify="center")

                for prereq_num, prereq_name in missing_prereqs:
                    prereq_table.add_row(prereq_num, prereq_name, "[red]❌ Not Complete[/red]")

                self.console.print(prereq_table)
                self.console.print()

                # Show what to do next
                first_missing = missing_prereqs[0][0]
                self.console.print(f"💡 Next: [bold cyan]tito module start {first_missing}[/bold cyan]")
                self.console.print("   Complete modules in order to build your ML framework progressively")

                return 1

        # Check for the notebook file itself, not just the directory: a
        # directory can exist but be empty if a previous conversion failed
        # partway, which would otherwise skip regeneration silently.
        module_dir = self.config.project_root / "data" / "modules" / module_name
        short_name = module_name.split("_", 1)[1] if "_" in module_name else module_name
        notebook_file = module_dir / f"{short_name}.ipynb"
        if not notebook_file.exists():
            # Create module from src/ using export
            src_dir = self.config.project_root / "data" / "src" / module_name
            if not src_dir.exists():
                self.console.print(f"[red]❌ Source not found: src/{module_name}[/red]")
                return 1

            self.console.print("[cyan]📝 Creating module from source...[/cyan]")
            if not self._create_module_from_src(module_name):
                self.console.print(f"[red]❌ Failed to create module {module_name}[/red]")
                return 1
            self.console.print(f"[green]✅ Module {normalized} ready![/green]")
            self.console.print()

        # Show success panel
        self.console.print(
            Panel(
                f"[green]Starting Module {normalized}: {module_name}[/green]\n\n"
                f"Build your ML framework one component at a time.",
                title=f"🚀 Module {normalized} Unlocked!",
                border_style="bright_green",
                box=box.ROUNDED,
            )
        )
        self.console.print()

        # Show module info table
        info_table = Table(show_header=False, box=None, padding=(0, 2))
        info_table.add_column("Field", style="dim", width=18)
        info_table.add_column("Value")

        info_table.add_row("📦 Module", f"[bold cyan]{normalized} - {module_name}[/bold cyan]")
        info_table.add_row("📊 Progress", f"{len(completed)}/{len(module_mapping)} modules completed")

        # Check for milestone unlocks
        milestone_info = self._get_milestone_for_module(module_num)
        if milestone_info:
            mid, mname, required = milestone_info
            if module_num in required:
                completed_nums = {
                    int(str(module).split("_", 1)[0])
                    for module in completed
                    if str(module).split("_", 1)[0].isdigit()
                }
                # r >= module_num is always true here: the prerequisite
                # check above already returned 1 if any module before
                # module_num was incomplete, so any required r < module_num
                # is guaranteed to already be in completed_nums.
                modules_left = len([r for r in required if r not in completed_nums])
                if modules_left <= 3:
                    info_table.add_row("🏆 Milestone", f"[magenta]{mid} - {mname}[/magenta]")
                    info_table.add_row("", f"[dim]{modules_left} modules until unlock[/dim]")

        self.console.print(info_table)
        self.console.print()

        # Mark as started
        self.mark_module_started(normalized)

        if no_jupyter:
            # CI/testing mode - just create notebook, don't open Jupyter
            self.console.print(f"[green]✅ Module {normalized} ready (notebook created)[/green]")
            self.console.print(f"💡 Next: [bold cyan]tito module complete {normalized}[/bold cyan]")
            return 0

        # Instructions
        self.console.print("💡 [bold]What to do:[/bold]")
        self.console.print("   1. Work in Jupyter Lab (opening now...)")
        self.console.print("   2. Build your implementation")
        self.console.print("   3. Run: [bold cyan]tito module complete " + normalized + "[/bold cyan]")
        self.console.print()

        return open_jupyter(self.config, self.console, module_name, notebook=notebook, lab=lab)

    def view_module(self, module_number: str, notebook: bool = False, lab: bool = False) -> int:
        """Open a module notebook in Jupyter without any status ceremony."""
        module_mapping = get_module_mapping()
        normalized = normalize_module_number(module_number)

        if normalized not in module_mapping:
            self.console.print(f"[red]❌ Module {normalized} not found[/red]")
            return 1

        module_name = module_mapping[normalized]
        # Notebooks are in data/modules/ directory, not src/ (which is modules_dir in config).
        # Check for the notebook file itself, not just the directory: see the
        # matching comment in start_module for why directory-existence alone is
        # not a reliable signal that a notebook actually exists.
        module_dir = self.config.project_root / "data" / "modules" / module_name
        short_name = module_name.split("_", 1)[1] if "_" in module_name else module_name
        notebook_file = module_dir / f"{short_name}.ipynb"

        if not notebook_file.exists():
            self.console.print(f"[yellow]⚠️  Module {normalized} not started yet[/yellow]")
            self.console.print(f"💡 Run: [bold cyan]tito module start {normalized}[/bold cyan]")
            return 1

        return open_jupyter(self.config, self.console, module_name, notebook=notebook, lab=lab)

    def _create_module_from_src(self, module_name: str) -> bool:
        """Create a module in data/modules/ by converting from src/.

        Uses the same conversion logic as 'tito dev export' but only creates
        the student-facing notebook, without exporting to the tinytorch package.
        Full `src/` (including `### BEGIN SOLUTION` ... `### END SOLUTION` blocks) is
        passed through to jupytext so notebooks match the source-of-truth and exports
        remain consistent for `tito module complete` and CI user-journey.
        """
        from platforms.cli.commands.export_utils import convert_py_to_notebook

        src_path = self.config.project_root / "data" / "src" / module_name
        if not src_path.exists():
            return False

        # Convert data/src/*.py to data/modules/*.ipynb using jupytext
        return convert_py_to_notebook(src_path, self.venv_path, self.console)

    def _get_milestone_for_module(self, module_num: int) -> tuple | None:
        """Get the milestone this module contributes to."""
        from platforms.cli.processes.milestone import MILESTONE_SCRIPTS, _required_modules_for

        for mid, milestone in sorted(MILESTONE_SCRIPTS.items()):
            required = _required_modules_for(milestone)
            if module_num in required:
                return (mid, milestone["name"], required)

        return None

    def _get_export_path_for_module(self, module_name: str) -> str:
        """Return the generated package path for a module based on default_exp."""
        from platforms.cli.commands.export_utils import get_export_target

        module_path = Path("data") / "modules" / module_name
        export_target = get_export_target(module_path)
        if export_target != "unknown":
            return f"data/trentorch/{export_target.replace('.', '/')}.py"

        short_name = module_name.split("_", 1)[1] if "_" in module_name else module_name
        return f"data/trentorch/core/{short_name}.py"

    def _get_primary_export_label(self, module_name: str) -> str:
        """Return a concise user-facing label for the module's exported API."""
        module_num = module_name.split("_", 1)[0]
        return self.PRIMARY_EXPORT_LABELS.get(module_num, module_name.split("_", 1)[-1].title())

    def resume_module(
        self, module_number: str | None = None, notebook: bool = False, lab: bool = False
    ) -> int:
        """Resume working on a module (continue previous work)."""
        module_mapping = get_module_mapping()

        # If no module specified, resume last worked
        if not module_number:
            last_worked = self.get_last_worked_module()
            if not last_worked:
                self.console.print("[yellow]⚠️  No module to resume[/yellow]")
                self.console.print("💡 Start with: [bold cyan]tito module start 01[/bold cyan]")
                return 1
            module_number = last_worked

        normalized = normalize_module_number(module_number)

        if normalized not in module_mapping:
            self.console.print(f"[red]❌ Module {normalized} not found[/red]")
            max_module = max(module_mapping.keys()) if module_mapping else "??"
            self.console.print(f"💡 Available modules: 01-{max_module}")
            return 1

        module_name = module_mapping[normalized]

        # Check if module was started
        if not self.is_module_started(normalized):
            self.console.print(f"[yellow]⚠️  Module {normalized} not started yet[/yellow]")
            self.console.print(f"💡 Start with: [bold cyan]tito module start {normalized}[/bold cyan]")
            return 1

        # Update last worked
        self.update_last_worked(normalized)

        self.console.print(f"🔄 Resuming Module {normalized}: {module_name}")
        self.console.print("💡 Continue your work, then run:")
        self.console.print(f"   [bold cyan]tito module complete {normalized}[/bold cyan]")

        return open_jupyter(self.config, self.console, module_name, notebook=notebook, lab=lab)

    def complete_module(
        self, module_number: str | None = None, skip_tests: bool = False, skip_export: bool = False
    ) -> int:
        """Complete a module with enhanced visual feedback and celebration."""
        from rich import box

        module_mapping = get_module_mapping()

        # If no module specified, complete current/last worked
        if not module_number:
            last_worked = self.get_last_worked_module()
            if not last_worked:
                self.console.print("[yellow]⚠️  No module to complete[/yellow]")
                self.console.print("💡 Start with: [bold cyan]tito module start 01[/bold cyan]")
                return 1
            module_number = last_worked

        normalized = normalize_module_number(module_number)

        if normalized not in module_mapping:
            self.console.print(f"[red]❌ Module {normalized} not found[/red]")
            return 1

        module_name = module_mapping[normalized]

        # Validate sequential completion: all previous modules must be completed
        module_num = int(normalized)
        if module_num > 1:
            progress = self.get_progress_data()
            completed = progress.get("completed_modules", [])
            prev_num = f"{module_num - 1:02d}"

            if prev_num not in completed:
                self.console.print(f"[red]❌ Cannot complete module {normalized}[/red]")
                self.console.print(f"[yellow]⚠️  You must complete module {prev_num} first[/yellow]")
                self.console.print(f"💡 Run: [bold cyan]tito module complete {prev_num}[/bold cyan]")
                return 1

        # Header
        self.console.print(
            Panel(
                "Unit tests → Export → Integration tests → Progress tracking",
                title=f"🎯 Completing Module {normalized}: {module_name}",
                border_style="bright_cyan",
                box=box.ROUNDED,
            )
        )
        self.console.print()

        # Step 1: Run UNIT tests (test source files, don't need exported package)
        if not skip_tests:
            self.console.print(
                "[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]"
            )
            self.console.print()
            self.console.print("[bold cyan] Step 1/4: Running Unit Tests[/bold cyan]")
            self.console.print()

            _t0 = time.time()
            unit_result = run_inline_unit_tests(self.config, self.console, module_name, verbose=True)
            _profile(module_name, "step1_unit_tests", time.time() - _t0)
            unit_result["passed"]

            if unit_result["failed"] > 0:
                self.console.print()
                self.console.print(f"[red]   ❌ Unit tests failed for {module_name}[/red]")
                self.console.print("   💡 Fix the issues and try again")
                return 1

            self.console.print(f"   ✅ Unit tests: {unit_result['passed']}/{unit_result['passed']} passed")

        # Step 1.5: Catch notebook syntax errors before export. Unit tests run
        # against the instructor src/ file, so a SyntaxError in the student
        # notebook would otherwise slip through to a silent, broken export.
        if not skip_export:
            syntax_check = check_notebook_syntax(self.config, module_name)
            if not syntax_check["ok"]:
                self.console.print()
                self.console.print(f"[red]   ❌ {syntax_check['error']}[/red]")
                self.console.print("   💡 Fix the syntax error in your notebook and try again")
                return 1

        # Step 2: Export to package (BEFORE integration tests, since they need the export)
        if not skip_export:
            self.console.print()
            self.console.print(
                "[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]"
            )
            self.console.print()
            self.console.print("[bold cyan] Step 2/4: Exporting to TinyTorch Package[/bold cyan]")
            self.console.print()

            _t0 = time.time()
            export_result = self.export_module(module_name)
            _profile(module_name, "step2_export", time.time() - _t0)
            if export_result != 0:
                self.console.print(f"[red]   ❌ Export failed for {module_name}[/red]")
                self.console.print("   💡 Fix the issues and try again")
                return 1
            else:
                export_path = self._get_export_path_for_module(module_name)
                export_label = self._get_primary_export_label(module_name)
                self.console.print(f"   ✅ Exported: {export_path}")
                self.console.print("   ✅ Updated: data/trentorch/__init__.py")
                self.console.print()
                self.console.print(
                    f"   [dim]Your {export_label} implementation is now part of the framework![/dim]"
                )

        # Step 3: Run INTEGRATION tests (AFTER export, since they import from tinytorch.core.*)
        if not skip_tests:
            self.console.print()
            self.console.print(
                "[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]"
            )
            self.console.print()
            self.console.print("[bold cyan] Step 3/4: Running Integration Tests[/bold cyan]")
            self.console.print()

            _t0 = time.time()
            integration_result = run_integration_tests(self.config, self.console, module_name, verbose=True)
            _profile(module_name, "step3_integration_tests", time.time() - _t0)
            integration_result["passed"]

            if integration_result["failed"] > 0:
                self.console.print()
                self.console.print(f"[red]   ❌ Integration tests failed for {module_name}[/red]")
                self.console.print("   💡 Fix the issues and try again")
                return 1

            if integration_result["passed"] > 0:
                self.console.print(
                    f"   ✅ Integration tests: {integration_result['passed']}/{integration_result['passed']} passed"
                )
            else:
                self.console.print("   [dim]No integration tests for this module[/dim]")

        # Step 4: Update progress tracking
        self.console.print()
        self.console.print(
            "[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]"
        )
        self.console.print()
        self.console.print("[bold cyan] Step 4/4: Tracking Progress[/bold cyan]")
        self.console.print()

        _t0 = time.time()
        progress = self.get_progress_data()
        self.update_progress(normalized, module_name)
        _profile(module_name, "step4_progress_tracking", time.time() - _t0)

        new_progress = self.get_progress_data()
        completed_count = len(new_progress.get("completed_modules", []))
        total_modules = len(module_mapping)
        progress_percent = int((completed_count / total_modules) * 100)

        self.console.print(f"   ✅ Module {normalized} marked complete")
        self.console.print(f"   📈 Progress: {completed_count}/{total_modules} modules ({progress_percent}%)")

        self.console.print()
        self.console.print(
            "[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]"
        )
        self.console.print()

        # Step 4: Celebration panel
        # (every path above this point that could fail already returned 1
        # directly, so reaching here always means success -- an unused
        # `success` flag used to wrap this in `if success:`, which was
        # dead weight: it was set once to True and never reassigned
        # anywhere in this function, so the celebration panel, the
        # milestone-unlock check below, and this function's own return
        # value were each conditioned on something that could never be
        # False. Simplified to match what the code actually does.)
        component_name = module_name.split("_", 1)[1].title()

        celebration_text = Text()
        celebration_text.append(f"You didn't import {component_name}. You BUILT it.\n\n", style="bold green")
        celebration_text.append("What you can do now:\n", style="bold")
        celebration_text.append(f"  >>> from tinytorch import {component_name}\n", style="cyan")
        celebration_text.append(f"  >>> # Use your {component_name} implementation!\n\n", style="dim cyan")

        # Next module suggestion
        next_num = f"{int(normalized) + 1:02d}"
        if next_num in module_mapping:
            next_module = module_mapping[next_num]
            next_name = next_module.split("_", 1)[1].title()
            celebration_text.append("💡 Next: ", style="")
            celebration_text.append(f"tito module start {next_num}", style="bold cyan")
            celebration_text.append("\n", style="")
            celebration_text.append(f"         Build {next_name}", style="dim")

        self.console.print(
            Panel(
                celebration_text,
                title="🎉 Module Complete!",
                border_style="bright_green",
                box=box.ROUNDED,
            )
        )

        # Step 5: Check for milestone unlocks. Skipped during the maintainer
        # verify-solution loop (Stage 1) to avoid auto-running a real,
        # minutes-long milestone as a side effect of testing curriculum
        # correctness -- milestone behavior itself is covered by Stage 7.
        from .test_runner import VERIFY_SOLUTION_ENV

        if os.environ.get(VERIFY_SOLUTION_ENV) != "1":
            check_and_run_milestone_unlocks(self.config, self.console)

        return 0

    def complete_all_modules(self, skip_tests: bool = False, skip_export: bool = False) -> int:
        """Complete all modules in sequence.

        This iterates through all modules in order (01 → 20) and runs
        complete_module on each one. Useful for:
        - CI validation of all modules
        - Students who want to export everything they've built
        - Rebuilding the full package from existing notebooks

        Note: This expects notebooks to exist in data/modules/. For rebuilding
        from src/, use 'tito dev export --all' instead.
        """
        from rich import box

        module_mapping = get_module_mapping()
        module_nums = sorted(module_mapping.keys(), key=lambda x: int(x))

        console = self.console
        console.print(
            Panel(
                f"[bold cyan]Completing All Modules ({len(module_nums)} total)[/bold cyan]\n\n"
                "This will test and export each module in sequence.\n"
                "[dim]Modules without notebooks will be skipped.[/dim]",
                title="🔄 Complete All Modules",
                border_style="cyan",
                box=box.ROUNDED,
            )
        )
        console.print()

        passed = 0
        failed = 0
        skipped = 0

        for module_num in module_nums:
            module_name = module_mapping[module_num]

            # Check if notebook exists
            short_name = module_name.split("_", 1)[1] if "_" in module_name else module_name
            notebook_path = (
                self.config.project_root / "data" / "modules" / module_name / f"{short_name}.ipynb"
            )

            if not notebook_path.exists():
                console.print(f"  [dim]⏭️  Module {module_num}: {module_name} (no notebook)[/dim]")
                skipped += 1
                continue

            console.print(f"  [cyan]▶[/cyan] Module {module_num}: {module_name}...", end=" ")

            # Temporarily suppress the elaborate complete_module output
            # by calling the core logic directly
            result = self._complete_module_quiet(module_num, module_name, skip_tests, skip_export)

            if result == 0:
                passed += 1
                console.print("[green]✓[/green]")
            else:
                failed += 1
                console.print("[red]✗[/red]")
                # Stop on first failure
                console.print(f"\n[red]❌ Failed at module {module_num}[/red]")
                break

        console.print()

        if failed == 0:
            console.print(
                Panel(
                    f"[bold green]✅ All modules completed![/bold green]\n\n"
                    f"Passed: {passed}  Skipped: {skipped}",
                    title="🎉 Success",
                    border_style="green",
                    box=box.ROUNDED,
                )
            )
            return 0
        else:
            console.print(
                Panel(
                    f"[bold red]❌ Module completion failed[/bold red]\n\n"
                    f"Passed: {passed}  Failed: {failed}  Skipped: {skipped}",
                    title="⚠️ Failure",
                    border_style="red",
                    box=box.ROUNDED,
                )
            )
            return 1

    def _complete_module_quiet(
        self, module_num: str, module_name: str, skip_tests: bool, skip_export: bool
    ) -> int:
        """Complete a single module without verbose output.

        Core logic extracted from complete_module for use in batch operations.
        Returns 0 on success, 1 on failure.
        """
        # Run unit tests
        if not skip_tests:
            unit_result = run_inline_unit_tests(self.config, self.console, module_name, verbose=False)
            if unit_result["failed"] > 0:
                return 1

        # Catch notebook syntax errors before export (see complete_module Step 1.5)
        if not skip_export:
            syntax_check = check_notebook_syntax(self.config, module_name)
            if not syntax_check["ok"]:
                self.console.print(f"[red]❌ {syntax_check['error']}[/red]")
                return 1

        # Export to package
        if not skip_export:
            export_result = self.export_module(module_name)
            if export_result != 0:
                return 1

        # Run integration tests (after export)
        if not skip_tests:
            integration_result = run_integration_tests(self.config, self.console, module_name, verbose=False)
            if integration_result["failed"] > 0:
                return 1

        # Update progress
        self.get_progress_data()
        self.update_progress(module_num, module_name)

        return 0

    def export_module(self, module_name: str) -> int:
        """Export student's notebook to the TinyTorch package.

        This only runs nbdev_export on the existing notebook.
        It does NOT convert from data/src/*.py (that would overwrite student work).

        Developers who want to rebuild from src/ should use: tito dev export
        """
        import os
        from pathlib import Path

        from platforms.cli.commands.export_utils import ensure_writable_target, get_export_target

        from .test_runner import VERIFY_SOLUTION_ENV

        try:
            # Normally exports the student's own notebook in data/modules/.
            # Under the maintainer verification loop (tren dev test --inline),
            # TREN_DEV_VERIFY_SOLUTION is set and nobody's notebook is solved,
            # so export from data/solutions/ (the reference implementation)
            # instead -- matching run_inline_unit_tests' own source switch.
            short_name = module_name.split("_", 1)[1] if "_" in module_name else module_name
            target_root = "solutions" if os.environ.get(VERIFY_SOLUTION_ENV) == "1" else "modules"
            notebook_path = Path("data") / target_root / module_name / f"{short_name}.ipynb"

            if not notebook_path.exists():
                self.console.print(f"[red]❌ Notebook not found: {notebook_path}[/red]")
                self.console.print("[dim]Make sure you're in the TinyTorch project root.[/dim]")
                return 1

            # Ensure target file is writable
            module_path = notebook_path.parent
            export_target = get_export_target(module_path)
            if export_target != "unknown":
                ensure_writable_target(export_target)

            # Run nbdev_export using Python API directly (more reliable than subprocess)
            from nbdev.export import nb_export

            target_display = (
                f"data/trentorch/{export_target.replace('.', '/')}.py"
                if export_target != "unknown"
                else "data/trentorch/..."
            )
            self.console.print(f"[dim]📦 Exporting {notebook_path.name} → {target_display}[/dim]")

            lib_path = Path.cwd() / "data" / "trentorch"
            nb_export(notebook_path, lib_path=lib_path)

            # Verify the export actually produced a file
            if export_target != "unknown":
                target_file = lib_path / (export_target.replace(".", "/") + ".py")
                if not target_file.exists():
                    self.console.print(
                        f"[red]❌ Export verification failed: {target_file} was not created[/red]"
                    )
                    self.console.print(f"[dim]   Expected from #| default_exp: {export_target}[/dim]")
                    self.console.print(
                        "[yellow]   Check that your notebook has #| export cells with code[/yellow]"
                    )
                    return 1

                # Verify the file has actual content (not empty)
                content = target_file.read_text(encoding="utf-8")
                code_lines = [
                    line for line in content.split("\n") if line.strip() and not line.strip().startswith("#")
                ]
                if len(code_lines) < 2:
                    self.console.print(f"[red]❌ Export verification failed: {target_file} is empty[/red]")
                    self.console.print(
                        "[yellow]   Your notebook's #| export cells may not contain code[/yellow]"
                    )
                    return 1

            self.console.print("[dim]✅ Your code is now part of the tinytorch package![/dim]")
            return 0

        except ImportError:
            self.console.print("[red]❌ nbdev not found — cannot export module[/red]")
            self.console.print("[yellow]   Fix: pip install nbdev[/yellow]")
            return 1
        except Exception as e:
            self.console.print(f"[red]❌ Export failed: {e}[/red]")
            return 1

    def get_progress_data(self) -> dict:
        """Get current progress data from user_data/progress.json."""
        user_data_dir = self.config.project_root / "user_data"
        progress_file = user_data_dir / "progress.json"

        try:
            import json

            if progress_file.exists():
                with open(progress_file) as f:
                    return json.load(f)
        except Exception:
            pass

        return {
            "started_modules": [],
            "completed_modules": [],
            "last_worked": None,
            "last_completed": None,
            "last_updated": None,
        }

    def save_progress_data(self, progress: dict) -> None:
        """Save progress data to user_data/progress.json."""
        user_data_dir = self.config.project_root / "user_data"
        user_data_dir.mkdir(parents=True, exist_ok=True)
        progress_file = user_data_dir / "progress.json"

        try:
            import json
            from datetime import datetime

            progress["last_updated"] = datetime.now().isoformat()

            with open(progress_file, "w") as f:
                json.dump(progress, f, indent=2)
        except Exception as e:
            self.console.print(f"[yellow]⚠️  Could not save progress: {e}[/yellow]")

    def is_module_started(self, module_number: str) -> bool:
        """Check if a module has been started."""
        progress = self.get_progress_data()
        return module_number in progress.get("started_modules", [])

    def is_module_completed(self, module_number: str) -> bool:
        """Check if a module has been completed."""
        progress = self.get_progress_data()
        return module_number in progress.get("completed_modules", [])

    def mark_module_started(self, module_number: str) -> None:
        """Mark a module as started."""
        progress = self.get_progress_data()

        if "started_modules" not in progress:
            progress["started_modules"] = []

        if module_number not in progress["started_modules"]:
            progress["started_modules"].append(module_number)

        progress["last_worked"] = module_number
        self.save_progress_data(progress)

    def update_last_worked(self, module_number: str) -> None:
        """Update the last worked module."""
        progress = self.get_progress_data()
        progress["last_worked"] = module_number
        self.save_progress_data(progress)

    def get_last_worked_module(self) -> str | None:
        """Get the last worked module."""
        progress = self.get_progress_data()
        return progress.get("last_worked")

    def update_progress(self, module_number: str, module_name: str) -> None:
        """Update user progress tracking."""
        progress = self.get_progress_data()

        # Update completed modules
        if "completed_modules" not in progress:
            progress["completed_modules"] = []

        if module_number not in progress["completed_modules"]:
            progress["completed_modules"].append(module_number)

        # Remove from started modules when completing (prevent double-tracking)
        if "started_modules" in progress and module_number in progress["started_modules"]:
            progress["started_modules"].remove(module_number)

        progress["last_completed"] = module_number
        self.save_progress_data(progress)

        self.console.print(f"📈 Progress updated: {len(progress['completed_modules'])} modules completed")

    def show_next_steps(self, completed_module: str) -> None:
        """Show next steps after completing a module."""
        module_mapping = get_module_mapping()
        completed_num = int(completed_module)
        next_num = f"{completed_num + 1:02d}"

        if next_num in module_mapping:
            next_module = module_mapping[next_num]
            self.console.print(
                Panel(
                    f"🎉 Module {completed_module} completed!\n\n"
                    f"Next steps:\n"
                    f"  [bold cyan]tren module start {next_num}[/bold cyan] - Start {next_module}\n"
                    f"  [dim]tren module status[/dim] - View overall progress",
                    title="What's Next?",
                    border_style="green",
                )
            )
        else:
            self.console.print(
                Panel(
                    f"🎉 Module {completed_module} completed!\n\n"
                    "🏆 Congratulations! You've completed all available modules!\n"
                    "🚀 You're now ready to run MLPerf benchmarks!",
                    title="All Modules Complete!",
                    border_style="gold1",
                )
            )

    def list_modules(self, json_mode: bool = False) -> int:
        """List all available modules with descriptions (auto-discovered)."""
        import json

        # Auto-discover modules from filesystem
        module_mapping = get_module_mapping()
        metadata = get_all_module_metadata()
        progress = self.get_progress_data()
        started = progress.get("started_modules", [])
        completed = progress.get("completed_modules", [])

        if json_mode:
            # Machine-readable output for IDE integrations
            modules = []
            for num, folder_name in sorted(module_mapping.items()):
                meta = metadata.get(num)
                title = meta.title if meta else get_module_display_name(num)
                desc = meta.description if meta else ""

                if num in completed:
                    status = "completed"
                elif num in started:
                    status = "started"
                else:
                    status = "not_started"

                modules.append(
                    {
                        "number": num,
                        "folder": folder_name,
                        "title": title,
                        "description": desc,
                        "status": status,
                    }
                )
            print(json.dumps(modules))
            return 0

        # Human-readable Rich table output
        from rich import box
        from rich.table import Table

        table = Table(
            title="📚 Tiny🔥Torch Modules", box=box.ROUNDED, show_header=True, header_style="bold blue"
        )
        table.add_column("#", style="cyan", width=3)
        table.add_column("Module", style="bold", no_wrap=True)
        table.add_column("Description", style="dim")

        for num, folder_name in sorted(module_mapping.items()):
            meta = metadata.get(num)
            if meta:
                title = meta.title
                desc = meta.description
            else:
                title = get_module_display_name(num)
                desc = ""
            table.add_row(num, title, desc)

        self.console.print()
        self.console.print(table)
        self.console.print()
        self.console.print("[dim]Start a module: [bold]tito module start 01[/bold][/dim]")
        self.console.print("[dim]Check progress: [bold]tito module status[/bold][/dim]")
        self.console.print()

        return 0

    def get_path(self, module_number: str, notebook: bool = False, source: bool = False) -> int:
        """Print the absolute path to a module file. For IDE integrations."""
        module_mapping = get_module_mapping()
        normalized = normalize_module_number(module_number)

        if normalized not in module_mapping:
            self.console.print(f"[red]❌ Module {normalized} not found[/red]")
            return 1

        folder = module_mapping[normalized]
        project_root = self.config.project_root

        if notebook:
            slug = folder.split("_", 1)[1] if "_" in folder else folder
            target = project_root / "data" / "modules" / folder / f"{slug}.ipynb"
        elif source:
            target = project_root / "data" / "src" / folder / f"{folder}.py"
        else:
            self.console.print("[red]❌ Specify --notebook or --source[/red]")
            return 1

        print(str(target))
        return 0 if target.exists() else 1

    def show_status(self) -> int:
        """Show module completion status with enhanced visuals."""
        from datetime import datetime, timedelta

        from rich import box
        from rich.table import Table
        from rich.text import Text

        module_mapping = get_module_mapping()
        progress = self.get_progress_data()

        started = progress.get("started_modules", [])
        completed = progress.get("completed_modules", [])
        last_worked = progress.get("last_worked")
        last_updated = progress.get("last_updated")

        # Calculate progress percentage
        total_modules = len(module_mapping)
        completed_count = len(completed)
        progress_percent = int((completed_count / total_modules) * 100)

        # Create progress bar
        filled = int(progress_percent / 5)  # 20 blocks total
        progress_bar = "█" * filled + "░" * (20 - filled)

        # Calculate streak and last activity
        streak_days = 0  # TODO: Calculate from completion dates
        last_activity = "just now"
        if last_updated:
            try:
                last_time = datetime.fromisoformat(last_updated)
                time_diff = datetime.now() - last_time
                if time_diff < timedelta(hours=1):
                    last_activity = f"{int(time_diff.total_seconds() / 60)} minutes ago"
                elif time_diff < timedelta(days=1):
                    last_activity = f"{int(time_diff.total_seconds() / 3600)} hours ago"
                else:
                    last_activity = f"{time_diff.days} days ago"
            except Exception:
                pass

        # Header panel with progress summary
        header_text = Text()
        header_text.append(
            f"Progress: {progress_bar} {completed_count}/{total_modules} modules ({progress_percent}%)\n",
            style="bold",
        )
        if streak_days > 0:
            header_text.append(f"Streak: 🔥 {streak_days} days  •  ", style="dim")
        header_text.append(f"Last activity: {last_activity}", style="dim")

        self.console.print(
            Panel(header_text, title="📊 Your Learning Journey", border_style="bright_cyan", box=box.ROUNDED)
        )

        self.console.print()

        # Create module status table
        status_table = Table(show_header=True, header_style="bold blue", box=box.SIMPLE, padding=(0, 1))

        status_table.add_column("##", style="cyan", width=4, justify="right")
        status_table.add_column("Module", style="bold", width=18)
        status_table.add_column("Status", width=12, justify="center")
        status_table.add_column("Next Action", style="dim", width=30)

        # Add rows for each module (show all modules - no collapsing)
        for num, name in sorted(module_mapping.items()):
            int(num)

            # Determine status
            if num in completed:
                status = "✅ Done"
                status_style = "green"
                next_action = "─"
            elif num in started:
                if num == last_worked:
                    status = "🚀 Working"
                    status_style = "yellow bold"
                    next_action = f"tito module complete {num}"
                else:
                    status = "💻 Started"
                    status_style = "cyan"
                    next_action = f"tito module resume {num}"
            else:
                # Check if previous module is completed
                prev_num = f"{int(num) - 1:02d}"
                if prev_num in completed or int(num) == 1:
                    status = "⏳ Ready"
                    status_style = "dim"
                    next_action = f"tito module start {num}"
                else:
                    status = "🔒 Locked"
                    status_style = "dim"
                    next_action = f"Complete module {prev_num} first"

            status_table.add_row(num, name, f"[{status_style}]{status}[/{status_style}]", next_action)

        self.console.print(status_table)
        self.console.print()

        # Milestones section (if any are unlocked or ready)
        # Show every milestone with state — slicing to the first few hid later
        # milestones once early ones were unlocked (issue #1615), so students
        # never saw that milestones 04+ were ready to be unlocked.
        if completed_count >= 1:
            milestone_unlocks = self._check_milestone_readiness(completed)
            if milestone_unlocks:
                self.console.print("[bold magenta]🏆 Milestones Unlocked:[/bold magenta]")
                for milestone_id, milestone_name, ready in milestone_unlocks:
                    if ready == "unlocked":
                        self.console.print(f"  [magenta]✅ {milestone_id} - {milestone_name}[/magenta]")
                    elif ready == "ready":
                        self.console.print(
                            f"  [yellow]🎯 {milestone_id} - {milestone_name} [Ready to unlock!][/yellow]"
                        )
                self.console.print()

        # Next steps
        if last_worked:
            if last_worked not in completed:
                self.console.print(f"💡 Next: [bold cyan]tito module complete {last_worked}[/bold cyan]")
            else:
                next_num = f"{int(last_worked) + 1:02d}"
                if next_num in module_mapping:
                    self.console.print(f"💡 Next: [bold cyan]tito module start {next_num}[/bold cyan]")
        else:
            self.console.print("💡 Next: [bold cyan]tito module start 01[/bold cyan]")

        return 0

    def _check_milestone_readiness(self, completed_modules: list) -> list:
        """Check which milestones are unlocked or ready.

        Uses the canonical ``MILESTONE_SCRIPTS`` table from ``tito milestone``
        so module status, milestone list, and milestone run share one set of
        prerequisites.
        """
        import json

        from platforms.cli.processes.milestone import (
            MILESTONE_SCRIPTS,
            _module_progress_to_int,
            _required_modules_for,
        )

        # Check which milestones have been run successfully.
        milestones_file = self.config.project_root / "user_data" / "milestones.json"
        completed_milestones = []
        if milestones_file.exists():
            try:
                with open(milestones_file) as f:
                    data = json.load(f)
                    completed_milestones = data.get("completed_milestones", [])
            except Exception:
                pass

        completed_set = {
            module_num
            for module_num in (_module_progress_to_int(m) for m in completed_modules)
            if module_num is not None
        }

        result = []
        for mid, milestone in sorted(MILESTONE_SCRIPTS.items()):
            required = _required_modules_for(milestone)
            name = milestone["name"]
            all_modules_done = all(m in completed_set for m in required)

            if mid in completed_milestones:
                # Milestone has been run and completed
                result.append((mid, name, "unlocked"))
            elif all_modules_done:
                # All required modules done but milestone not yet run
                result.append((mid, name, "ready"))

        return result

    def run(self, args: Namespace) -> int:
        """Execute the module workflow command."""
        # Handle subcommands
        if hasattr(args, "module_command") and args.module_command:
            if args.module_command == "start":
                return self.start_module(
                    args.module_number,
                    no_jupyter=getattr(args, "no_jupyter", False),
                    notebook=getattr(args, "notebook", False),
                    lab=getattr(args, "lab", False),
                )
            elif args.module_command == "view":
                return self.view_module(
                    args.module_number,
                    notebook=getattr(args, "notebook", False),
                    lab=getattr(args, "lab", False),
                )
            elif args.module_command == "resume":
                return self.resume_module(
                    getattr(args, "module_number", None),
                    notebook=getattr(args, "notebook", False),
                    lab=getattr(args, "lab", False),
                )
            elif args.module_command == "complete":
                # Check for --all flag
                if getattr(args, "all", False):
                    return self.complete_all_modules(
                        getattr(args, "skip_tests", False), getattr(args, "skip_export", False)
                    )
                return self.complete_module(
                    getattr(args, "module_number", None),
                    getattr(args, "skip_tests", False),
                    getattr(args, "skip_export", False),
                )
            elif args.module_command == "test":
                # Delegate to ModuleTestCommand
                test_command = ModuleTestCommand(self.config)
                return test_command.run(args)
            elif args.module_command == "reset":
                # Delegate to ModuleResetCommand
                reset_command = ModuleResetCommand(self.config)
                return reset_command.run(args)
            elif args.module_command == "status":
                return self.show_status()
            elif args.module_command == "list":
                return self.list_modules(json_mode=getattr(args, "json", False))
            elif args.module_command == "path":
                return self.get_path(
                    args.module_number,
                    notebook=getattr(args, "notebook", False),
                    source=getattr(args, "source", False),
                )

        # Show help if no valid command
        self.console.print(
            Panel(
                "[bold cyan]Module Lifecycle Commands[/bold cyan]\n\n"
                "[bold]Core Workflow:[/bold]\n"
                "  [bold green]tito module start 01[/bold green]     - Start working on Module 01 (first time)\n"
                "  [bold green]tito module view 01[/bold green]      - Open Module 01 notebook\n"
                "  [bold green]tito module resume 01[/bold green]    - Resume working on Module 01 (continue)\n"
                "  [bold green]tito module complete 01[/bold green]  - Complete Module 01 (test + export)\n"
                "  [bold yellow]tito module reset 01[/bold yellow]    - Reset Module 01 to clean state (with backup)\n\n"
                "[bold]Smart Defaults:[/bold]\n"
                "  [bold]tito module resume[/bold]        - Resume last worked module\n"
                "  [bold]tito module complete[/bold]      - Complete current module\n"
                "  [bold]tito module status[/bold]        - Show progress with states\n\n"
                "[bold]Natural Learning Flow:[/bold]\n"
                "  1. [dim]tito module start 01[/dim]     → Begin tensors (first time)\n"
                "  2. [dim]Work in Jupyter, save[/dim]    → Ctrl+S to save progress\n"
                "  3. [dim]tito module complete 01[/dim]  → Test, export, track progress\n"
                "  4. [dim]tito module start 02[/dim]     → Begin activations\n"
                "  5. [dim]tito module view 02[/dim]      → Just open the notebook\n\n"
                "[bold]Module States:[/bold]\n"
                "  ⏳ Not started  🚀 In progress  ✅ Completed\n\n"
                "[bold]Reset Options:[/bold]\n"
                "  [dim]tito module reset[/dim]         - Prompt for module to reset\n"
                "  [dim]tito module reset 01[/dim]      - Reset module 01\n"
                "  [dim]tito module reset --all[/dim]   - Reset all modules (fresh install)",
                title="Module Development Workflow",
                border_style="bright_cyan",
            )
        )

        return 0
