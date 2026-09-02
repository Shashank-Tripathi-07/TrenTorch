"""MilestoneCommand: the `tren milestone` dispatcher and its execution
subcommands (run/test/demo). Status/timeline/list/info rendering lives in
display.py; unlock state and prerequisite checks live in system.py.
"""

import json
import subprocess
import sys
from argparse import ArgumentParser, Namespace
from datetime import datetime
from pathlib import Path

from rich.cells import cell_len
from rich.panel import Panel

from platforms.cli.commands.base import BaseCommand

from . import display
from .constants import MILESTONE_ACHIEVEMENT_HIGHLIGHTS, MILESTONE_ALIASES, MILESTONE_SCRIPTS
from .system import (
    MilestoneSystem,
    _module_progress_to_int,
    _validate_required_exports,
)


class MilestoneCommand(BaseCommand):
    @property
    def name(self) -> str:
        return "milestone"

    @property
    def description(self) -> str:
        return "Milestone achievement and capability unlock commands"

    def add_arguments(self, parser: ArgumentParser) -> None:
        subparsers = parser.add_subparsers(
            dest="milestone_command", help="Milestone subcommands", metavar="SUBCOMMAND"
        )

        # List subcommand (NEW)
        list_parser = subparsers.add_parser("list", help="List available milestones and their status")
        list_parser.add_argument("--simple", action="store_true", help="Show simple list (less detail)")

        # Run subcommand (NEW)
        run_parser = subparsers.add_parser("run", help="Run a milestone with prerequisite checking")
        run_parser.add_argument(
            "milestone_id",
            help="Milestone ID (01-06) or name (perceptron, xor, mlp, cnn, transformer, mlperf)",
        )
        run_parser.add_argument(
            "--part", type=int, help="Run only a specific part (for multi-part milestones)"
        )
        run_parser.add_argument(
            "--skip-checks", action="store_true", help="Skip prerequisite checks (not recommended)"
        )

        # Info subcommand (NEW)
        info_parser = subparsers.add_parser("info", help="Show detailed information about a milestone")
        info_parser.add_argument(
            "milestone_id",
            help="Milestone ID (01-06) or name (perceptron, xor, mlp, cnn, transformer, mlperf)",
        )

        # Status subcommand
        status_parser = subparsers.add_parser("status", help="View milestone progress and achievements")
        status_parser.add_argument(
            "--detailed", action="store_true", help="Show detailed milestone information"
        )

        # Timeline subcommand
        timeline_parser = subparsers.add_parser("timeline", help="View milestone timeline and progression")
        timeline_parser.add_argument(
            "--horizontal", action="store_true", help="Show horizontal progress bar instead of tree"
        )

        # Test subcommand
        test_parser = subparsers.add_parser("test", help="Test milestone achievement requirements")
        test_parser.add_argument(
            "milestone_id", nargs="?", help="Milestone ID to test (1-6), or test next available"
        )

        # Demo subcommand
        demo_parser = subparsers.add_parser("demo", help="Run milestone capability demonstration")
        demo_parser.add_argument("milestone_id", help="Milestone ID to demonstrate (1-6)")

    def run(self, args: Namespace) -> int:
        console = self.console

        if not hasattr(args, "milestone_command") or not args.milestone_command:
            console.print(
                Panel(
                    "[bold cyan]Milestone Commands[/bold cyan]\n\n"
                    "Recreate ML history and achieve epic capabilities!\n\n"
                    "Available subcommands:\n"
                    "  • [bold]list[/bold]       - List available milestones\n"
                    "  • [bold]run[/bold]        - Run a milestone (with prereq checks)\n"
                    "  • [bold]info[/bold]       - Show detailed milestone information\n"
                    "  • [bold]status[/bold]     - View progress and achievements\n"
                    "  • [bold]timeline[/bold]   - View milestone timeline\n"
                    "  • [bold]test[/bold]       - Test milestone requirements\n"
                    "  • [bold]demo[/bold]       - Run capability demonstration\n\n"
                    "[dim]Examples:[/dim]\n"
                    "[dim]  tren milestone list[/dim]\n"
                    "[dim]  tren milestone run 03           # Run all parts[/dim]\n"
                    "[dim]  tren milestone run 03 --part 1  # Run Part 1 only[/dim]\n"
                    "[dim]  tren milestone run 03 --part 2  # Run Part 2 only[/dim]\n"
                    "[dim]  tren milestone info 03[/dim]\n"
                    "[dim]  tren milestone status --detailed[/dim]",
                    title="🏆 Milestone System",
                    border_style="bright_cyan",
                )
            )
            return 0

        # Execute the appropriate subcommand
        if args.milestone_command == "list":
            return display.show_list(self.config, console, args)
        elif args.milestone_command == "run":
            return self._handle_run_command(args)
        elif args.milestone_command == "info":
            return display.show_info(self.config, console, args)
        elif args.milestone_command == "status":
            return display.show_status(self.config, console, args)
        elif args.milestone_command == "timeline":
            return display.show_timeline(self.config, console, args)
        elif args.milestone_command == "test":
            return self._handle_test_command(args)
        elif args.milestone_command == "demo":
            return self._handle_demo_command(args)
        else:
            console.print(
                Panel(
                    f"[red]Unknown milestone subcommand: {args.milestone_command}[/red]",
                    title="Error",
                    border_style="red",
                )
            )
            return 1

    def _handle_test_command(self, args: Namespace) -> int:
        """Handle milestone test command."""
        console = self.console
        milestone_system = MilestoneSystem(self.config)

        # Determine which milestone to test
        if args.milestone_id:
            milestone_id = args.milestone_id
        else:
            # Test next available milestone
            status = milestone_system.get_milestone_status()
            if status["next_milestone"]:
                milestone_id = status["next_milestone"]
            else:
                console.print(
                    Panel(
                        "[yellow]No milestone available to test.[/yellow]\n\n"
                        "Either all milestones are unlocked or none are ready.\n"
                        "Use [dim]tren milestone status[/dim] to see your progress.",
                        title="No Test Available",
                        border_style="yellow",
                    )
                )
                return 0

        # Validate milestone ID
        if milestone_id not in milestone_system.MILESTONES:
            console.print(
                Panel(
                    f"[red]Invalid milestone ID: {milestone_id}[/red]\n\n"
                    f"Valid milestone IDs: 1, 2, 3, 4, 5, 6",
                    title="Invalid Milestone",
                    border_style="red",
                )
            )
            return 1

        milestone = milestone_system.MILESTONES[milestone_id]

        console.print(
            Panel(
                f"[bold cyan]🧪 Testing Milestone {milestone_id}[/bold cyan]\n\n"
                f"[bold]{milestone['emoji']} {milestone['title']}[/bold]\n"
                f"[dim]{milestone.get('victory_condition', milestone.get('description', ''))}[/dim]",
                title="Milestone Test",
                border_style="bright_cyan",
            )
        )

        # Run the test with progress animation
        with console.status("[bold green]Testing milestone requirements...", spinner="dots"):
            result = milestone_system.run_milestone_test(milestone_id)

        # Show results
        if result["success"]:
            console.print(
                Panel(
                    f"[bold green]✅ Milestone Test Passed![/bold green]\n\n"
                    f"[green]All requirements met for {result['milestone_name']}[/green]\n"
                    f"[cyan]Capability: {result['capability']}[/cyan]\n\n"
                    f"[bold yellow]Run the milestone:[/bold yellow]\n"
                    f"[dim]tren milestone run {milestone_id}[/dim]",
                    title="🎉 Ready to Unlock!",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel(
                    f"[bold yellow]⚠️ Milestone Requirements Not Met[/bold yellow]\n\n"
                    f"[yellow]Milestone: {result.get('milestone_name', 'Unknown')}[/yellow]\n"
                    f"[red]Issue: {result.get('error', 'Unknown error')}[/red]\n\n"
                    f"[cyan]Complete the required modules and try again.[/cyan]",
                    title="Requirements Missing",
                    border_style="yellow",
                )
            )

        return 0

    def _handle_demo_command(self, args: Namespace) -> int:
        """Handle milestone demo command."""
        console = self.console
        milestone_system = MilestoneSystem(self.config)
        milestone_id = args.milestone_id

        # Validate milestone ID
        if milestone_id not in milestone_system.MILESTONES:
            console.print(
                Panel(
                    f"[red]Invalid milestone ID: {milestone_id}[/red]\n\n"
                    f"Valid milestone IDs: 1, 2, 3, 4, 5, 6",
                    title="Invalid Milestone",
                    border_style="red",
                )
            )
            return 1

        milestone = milestone_system.MILESTONES[milestone_id]
        status = milestone_system.get_milestone_status()
        milestone_status = status["milestones"][milestone_id]

        # Check if milestone is unlocked
        if not milestone_status["is_unlocked"]:
            console.print(
                Panel(
                    f"[yellow]Milestone {milestone_id} not yet unlocked.[/yellow]\n\n"
                    f"[bold]{milestone['emoji']} {milestone['title']}[/bold]\n"
                    f"[dim]{milestone.get('victory_condition', milestone.get('description', ''))}[/dim]\n\n"
                    f"[cyan]Complete the requirements first:[/cyan]\n"
                    f"[dim]tren milestone test {milestone_id}[/dim]",
                    title="Milestone Locked",
                    border_style="yellow",
                )
            )
            return 0

        # Check if demo file exists
        demo_file = milestone.get("demo_file")
        if not demo_file:
            console.print(
                Panel(
                    f"[yellow]Demo not available for Milestone {milestone_id}[/yellow]\n\n"
                    f"Use [dim]tren milestone run {milestone_id}[/dim] to run the milestone script.",
                    title="Demo Unavailable",
                    border_style="yellow",
                )
            )
            return 0

        demo_path = Path("capabilities") / demo_file
        if not demo_path.exists():
            console.print(
                Panel(
                    f"[yellow]Demo not available for Milestone {milestone_id}[/yellow]\n\n"
                    f"Demo file not found: {demo_file}\n"
                    f"[dim]This demo may be coming in a future update.[/dim]",
                    title="Demo Unavailable",
                    border_style="yellow",
                )
            )
            return 0

        # Run the demo
        console.print(
            Panel(
                f"[bold cyan]🎬 Launching Milestone {milestone_id} Demo[/bold cyan]\n\n"
                f"[bold]{milestone['emoji']} {milestone['title']}[/bold]\n"
                f"[yellow]Watch your capability in action![/yellow]\n\n"
                f"[cyan]Demonstrating: {milestone.get('capability', milestone.get('description', ''))}[/cyan]\n"
                f"[dim]Running: {demo_file}[/dim]",
                title="Capability Demo",
                border_style="bright_cyan",
            )
        )

        try:
            result = subprocess.run(
                [sys.executable, str(demo_path)],
                capture_output=False,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            if result.returncode == 0:
                console.print(
                    Panel(
                        f"[bold green]✅ Demo completed successfully![/bold green]\n\n"
                        f"[yellow]You've seen your {milestone['title']} capability in action![/yellow]\n"
                        f"[cyan]Real-world impact: {milestone.get('real_world_impact', milestone.get('historical_context', ''))}[/cyan]",
                        title="🎉 Demo Complete",
                        border_style="green",
                    )
                )
            else:
                console.print(f"[yellow]⚠️ Demo completed with status: {result.returncode}[/yellow]")

        except Exception as e:
            console.print(
                Panel(
                    f"[red]❌ Error running demo: {e}[/red]\n\n"
                    f"[dim]You can manually run: python capabilities/{demo_file}[/dim]",
                    title="Demo Error",
                    border_style="red",
                )
            )
            return 1

        return 0

    def _handle_list_command(self, args: Namespace) -> int:
        """Handle milestone list command - show available milestones."""
        return display.show_list(self.config, self.console, args)

    def _handle_run_command(self, args: Namespace) -> int:
        """Handle milestone run command - run a milestone with checks."""
        console = self.console
        milestone_id = args.milestone_id

        # Resolve name aliases (e.g., "perceptron" -> "01")
        if milestone_id.lower() in MILESTONE_ALIASES:
            milestone_id = MILESTONE_ALIASES[milestone_id.lower()]

        # Validate milestone ID
        if milestone_id not in MILESTONE_SCRIPTS:
            alias_list = ", ".join(sorted(MILESTONE_ALIASES.keys()))
            console.print(
                Panel(
                    f"[red]Invalid milestone: {args.milestone_id}[/red]\n\n"
                    f"Valid IDs: {', '.join(sorted(MILESTONE_SCRIPTS.keys()))}\n"
                    f"Valid names: {alias_list}",
                    title="Invalid Milestone",
                    border_style="red",
                )
            )
            return 1

        milestone = MILESTONE_SCRIPTS[milestone_id]

        # Handle both single script and multiple scripts
        # Also track which script configs we're running (for per-part requirements)
        scripts_to_run = []
        script_configs = []  # Store full config for each script (includes required_modules)

        if "scripts" in milestone:
            all_script_configs = milestone["scripts"]
            all_scripts = [(s["name"], s["script"], s.get("description", "")) for s in all_script_configs]

            # Handle --part flag for multipart milestones
            if args.part is not None:
                if args.part < 1 or args.part > len(all_scripts):
                    console.print(
                        Panel(
                            f"[red]Invalid part number: {args.part}[/red]\n\n"
                            f"Milestone {milestone_id} has {len(all_scripts)} parts.\n"
                            f"Valid parts: 1-{len(all_scripts)}\n\n"
                            f"[dim]Available parts:[/dim]\n"
                            + "\n".join(
                                f"  Part {i + 1}: {s[0]} - {s[2]}" for i, s in enumerate(all_scripts)
                            ),
                            title="Invalid Part",
                            border_style="red",
                        )
                    )
                    return 1
                scripts_to_run = [all_scripts[args.part - 1]]
                script_configs = [all_script_configs[args.part - 1]]
                console.print(f"[dim]Running Part {args.part} of {len(all_scripts)}[/dim]\n")
            else:
                # Check if milestone has a default_part (e.g., TinyDigits for CNN milestone)
                # This allows multi-part milestones to have a "no-download" default
                default_part = milestone.get("default_part")
                if default_part is not None and 1 <= default_part <= len(all_scripts):
                    scripts_to_run = [all_scripts[default_part - 1]]
                    script_configs = [all_script_configs[default_part - 1]]
                    console.print(
                        f"[dim]Running Part {default_part} (default). Use --part N for other parts.[/dim]\n"
                    )
                else:
                    scripts_to_run = all_scripts
                    script_configs = all_script_configs
        else:
            if args.part is not None:
                console.print(
                    f"[yellow]⚠️ Milestone {milestone_id} has only one part, ignoring --part flag[/yellow]\n"
                )
            scripts_to_run = [("Main", milestone["script"], milestone.get("description", ""))]
            script_configs = [milestone]  # Single script uses milestone-level config

        # Check if all scripts exist
        for script_name, script_file, _ in scripts_to_run:
            script_path = Path(script_file)
            if not script_path.exists():
                console.print(
                    Panel(
                        f"[red]Milestone script not found![/red]\n\n"
                        f"Expected: {script_file}\n"
                        f"[dim]This milestone may not be implemented yet.[/dim]",
                        title="Script Not Found",
                        border_style="red",
                    )
                )
                return 1

        # Check prerequisites and validate exports/tests (unless skipped)
        if not args.skip_checks:
            console.print(
                f"\n[bold cyan]🔍 Checking prerequisites for Milestone {milestone_id}...[/bold cyan]\n"
            )

            # Check module completion status using module workflow
            from platforms.cli.processes.module_workflow.workflow import ModuleWorkflowCommand

            module_workflow = ModuleWorkflowCommand(self.config)
            progress_data = module_workflow.get_progress_data()

            # Determine required modules based on what we're running
            # If running specific part(s), use per-part requirements if available
            # Otherwise use milestone-level requirements
            required_modules = set()
            for config in script_configs:
                part_reqs = config.get("required_modules", milestone.get("required_modules", []))
                required_modules.update(part_reqs)
            required_modules = sorted(required_modules)

            completed_modules = progress_data.get("completed_modules", [])

            # Convert completed to set of integers. Handles "01" and "01_tensor".
            completed_set = {
                module_num
                for module_num in (_module_progress_to_int(m) for m in completed_modules)
                if module_num is not None
            }
            missing_modules = [m for m in required_modules if m not in completed_set]

            if missing_modules:
                part_info = ""
                # `and len(script_configs) == 1` used to also gate this: every
                # code path above that leaves script_configs longer than one
                # element (the "run every part" fallback a few dozen lines up)
                # only runs when args.part is None, so by the time args.part
                # is not None here, script_configs is already guaranteed to
                # have exactly one element -- the length check could never
                # independently be False, dead weight rather than a real
                # second condition.
                if args.part is not None:
                    part_info = f" (Part {args.part})"
                console.print(
                    Panel(
                        f"[bold yellow]❌ Missing Required Modules[/bold yellow]\n\n"
                        f"[yellow]Milestone {milestone_id}{part_info} requires modules: {', '.join(f'{m:02d}' for m in required_modules)}[/yellow]\n"
                        f"[red]Missing: {', '.join(f'{m:02d}' for m in missing_modules)}[/red]\n\n"
                        f"[cyan]Complete the missing modules first:[/cyan]\n"
                        + "\n".join(
                            f"[dim]  tren module complete {m:02d}[/dim]" for m in missing_modules[:3]
                        ),
                        title="Prerequisites Not Met",
                        border_style="yellow",
                    )
                )
                return 1

            console.print("[green]✅ All required modules completed![/green]\n")

            # Test imports work
            console.print("[bold cyan]🧪 Testing YOUR implementations...[/bold cyan]\n")

            import sys as _sys

            _sys.path.insert(0, str(Path.cwd()))

            export_failures = _validate_required_exports(required_modules)
            if export_failures:
                console.print(
                    Panel(
                        "[red]Import Test Failed![/red]\n\n"
                        "[yellow]Missing or invalid exports:[/yellow]\n"
                        + "\n".join(f"  • {failure}" for failure in export_failures[:8])
                        + ("\n  • ..." if len(export_failures) > 8 else "")
                        + "\n\n"
                        "[dim]Your modules may not be exported correctly.[/dim]\n"
                        "[dim]Try re-exporting: tren module complete XX[/dim]",
                        title="Import Test Failed",
                        border_style="red",
                    )
                )
                return 1

            for module_num in required_modules:
                console.print(f"  [green]✓[/green] Module {module_num:02d} exports available")

            console.print("\n[green]✅ YOUR Tren⚡️Torch is ready![/green]\n")

        # Show milestone banner
        scripts_info = ""
        if len(scripts_to_run) > 1:
            scripts_info = "[bold]📂 Parts:[/bold]\n" + "\n".join(
                f"  • {name}: {desc}" for name, _, desc in scripts_to_run
            )
        else:
            scripts_info = f"[bold]📂 Running:[/bold] {scripts_to_run[0][1]}"

        WIDTH = 48

        line1_text = f"  {milestone['emoji']} Milestone {milestone_id}: {milestone['name']}"
        line1 = f"[bold magenta]║[/bold magenta]{line1_text}{' ' * (WIDTH - cell_len(line1_text))}[bold magenta]║[/bold magenta]"

        line2_text = f"  {milestone['title']}"
        line2 = f"[bold magenta]║[/bold magenta]{line2_text}{' ' * (WIDTH - cell_len(line2_text))}[bold magenta]║[/bold magenta]"

        console.print(
            Panel(
                f"[bold magenta]╔{'═' * WIDTH}╗[/bold magenta]\n"
                f"{line1}\n"
                f"{line2}\n"
                f"[bold magenta]╚{'═' * WIDTH}╝[/bold magenta]\n\n"
                f"[bold]📚 Historical Context:[/bold]\n"
                f"{milestone['historical_context']}\n\n"
                f"[bold]🎯 What You'll Do:[/bold]\n"
                f"{milestone['description']}\n\n"
                f"{scripts_info}\n\n"
                f"[dim]All code uses YOUR Tren⚡️Torch implementations![/dim]",
                title=f"🏆 Milestone {milestone_id} ({milestone['year']})",
                border_style="bright_magenta",
                padding=(1, 2),
            )
        )

        # Only prompt if in interactive terminal
        import sys

        if sys.stdin.isatty() and sys.stdout.isatty():
            try:
                console.input("\n[yellow]Press Enter to begin...[/yellow] ")
            except EOFError:
                pass

        # Run all milestone scripts
        all_passed = True
        for part_idx, (script_name, script_file, script_desc) in enumerate(scripts_to_run):
            if len(scripts_to_run) > 1:
                console.print(
                    f"\n[bold cyan]━━━ Part {part_idx + 1}/{len(scripts_to_run)}: {script_name} ━━━[/bold cyan]"
                )
                if script_desc:
                    console.print(f"[dim]{script_desc}[/dim]\n")
            else:
                console.print(f"\n[bold green]🚀 Starting Milestone {milestone_id}...[/bold green]\n")

            console.print("━" * 80 + "\n")

            try:
                result = subprocess.run(
                    [sys.executable, script_file],
                    capture_output=False,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )

                console.print("\n" + "━" * 80)

                if result.returncode != 0:
                    all_passed = False
                    console.print(f"[yellow]⚠️ Part {script_name} completed with errors[/yellow]")
                    if len(scripts_to_run) > 1:
                        # Ask if they want to continue (only in interactive mode)
                        if sys.stdin.isatty() and sys.stdout.isatty():
                            try:
                                cont = input("\n[yellow]Continue to next part? (y/n): [/yellow] ")
                                if cont.lower() != "y":
                                    return result.returncode
                            except EOFError:
                                return result.returncode
                        else:
                            # Non-interactive: stop on first failure
                            return result.returncode

            except KeyboardInterrupt:
                console.print("\n\n[yellow]⚠️ Milestone interrupted by user[/yellow]")
                return 130
            except Exception as e:
                console.print(f"[red]Error running {script_name}: {e}[/red]")
                all_passed = False

        if all_passed:
            # Success! Mark milestone as complete
            self._mark_milestone_complete(milestone_id)

            parts_text = ""
            if len(scripts_to_run) > 1:
                parts_text = f"\n\n[bold]All {len(scripts_to_run)} parts completed:[/bold]\n" + "\n".join(
                    f"  ✅ {name}" for name, _, _ in scripts_to_run
                )

            default_highlights = [
                "Every line of code: YOUR implementations",
                "Every tensor operation: YOUR Tensor class",
                "Every gradient: YOUR autograd",
            ]
            highlights = MILESTONE_ACHIEVEMENT_HIGHLIGHTS.get(milestone_id, default_highlights)
            highlights_text = "\n".join(f"• {line}" for line in highlights)

            console.print(
                Panel(
                    f"[bold green]🏆 MILESTONE ACHIEVED![/bold green]\n\n"
                    f"[green]You completed Milestone {milestone_id}: {milestone['name']}[/green]\n"
                    f"[yellow]{milestone['title']}[/yellow]{parts_text}\n\n"
                    f"[bold]What makes this special:[/bold]\n"
                    f"{highlights_text}\n\n"
                    f"[cyan]Achievement saved locally![/cyan]",
                    title="✨ Achievement Unlocked ✨",
                    border_style="bright_green",
                    padding=(1, 2),
                )
            )

            # Show next steps
            next_id = str(int(milestone_id) + 1).zfill(2)
            if next_id in MILESTONE_SCRIPTS:
                next_milestone = MILESTONE_SCRIPTS[next_id]
                console.print("\n[bold yellow]🎯 What's Next:[/bold yellow]")
                console.print(f"[dim]Milestone {next_id}: {next_milestone['name']}[/dim]")

                # Get completed modules for checking next milestone
                progress_file = Path("user_data") / "progress.json"
                completed_modules = []
                if progress_file.exists():
                    try:
                        with open(progress_file) as f:
                            progress_data = json.load(f)
                            for mod in progress_data.get("completed_modules", []):
                                try:
                                    completed_modules.append(int(mod.split("_")[0]))
                                except (ValueError, IndexError):
                                    pass
                    except (OSError, json.JSONDecodeError):
                        pass

                # Check if unlocked
                missing = [m for m in next_milestone["required_modules"] if m not in completed_modules]
                if missing:
                    console.print(
                        f"[dim]Unlock by completing modules: {', '.join(f'{m:02d}' for m in missing[:3])}[/dim]"
                    )
                else:
                    console.print(f"[green]Ready to run: tren milestone run {next_id}[/green]")

            return 0
        else:
            console.print("[yellow]⚠️ Milestone completed with errors[/yellow]")
            return 1

    def _handle_info_command(self, args: Namespace) -> int:
        """Handle milestone info command - show detailed information."""
        return display.show_info(self.config, self.console, args)

    def _mark_milestone_complete(self, milestone_id: str) -> None:
        """Mark a milestone as complete in progress tracking."""
        milestone_system = MilestoneSystem(self.config)
        progress = milestone_system._get_milestone_progress_data()

        # Add to completed_milestones
        if milestone_id not in progress.get("completed_milestones", []):
            if "completed_milestones" not in progress:
                progress["completed_milestones"] = []
            progress["completed_milestones"].append(milestone_id)
            progress["completion_dates"] = progress.get("completion_dates", {})
            progress["completion_dates"][milestone_id] = datetime.now().isoformat()

        # Also add to unlocked_milestones (for status display)
        if milestone_id not in progress.get("unlocked_milestones", []):
            if "unlocked_milestones" not in progress:
                progress["unlocked_milestones"] = []
            progress["unlocked_milestones"].append(milestone_id)
            progress["unlock_dates"] = progress.get("unlock_dates", {})
            progress["unlock_dates"][milestone_id] = datetime.now().isoformat()
            progress["total_unlocked"] = len(progress["unlocked_milestones"])

        milestone_system._save_milestone_progress_data(progress)
