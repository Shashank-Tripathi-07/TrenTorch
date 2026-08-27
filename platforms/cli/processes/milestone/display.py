"""Milestone display: status, timeline, list, and info rendering.

Pure output, no state mutation. Split out of the old flat milestone.py so
the ASCII/Rich rendering code (the single largest chunk of the original
file) has its own home separate from command dispatch and state tracking.
"""

from argparse import Namespace
from datetime import datetime

from rich.panel import Panel
from rich.tree import Tree

from .constants import MILESTONE_SCRIPTS
from .system import MilestoneSystem, _load_completed_module_numbers, _required_modules_for


def show_status(config, console, args: Namespace) -> int:
    """Handle milestone status command."""
    milestone_system = MilestoneSystem(config)
    status = milestone_system.get_milestone_status()

    # Show header with overall progress. Note: status['overall_progress']
    # is unlock-based (it also drives the timeline progress bar elsewhere,
    # where that's the correct meaning), so it isn't used here -- showing
    # it next to "Milestones Achieved" would be contradictory (e.g. "0/6
    # achieved" beside "100%"). This header's percentage is achievement-
    # based instead, to actually match the achieved count shown above it.
    total_milestones = len(milestone_system.MILESTONES)
    achievement_progress = (status["total_completed"] / total_milestones) * 100 if total_milestones > 0 else 0
    console.print(
        Panel(
            f"[bold cyan]🎮 TinyTorch Milestone Progress[/bold cyan]\n\n"
            f"[bold]Capabilities Unlocked:[/bold] {status['total_unlocked']}/{total_milestones} milestones\n"
            f"[bold]Milestones Achieved:[/bold] {status['total_completed']}/{total_milestones} milestones\n"
            f"[bold]Overall Progress:[/bold] {achievement_progress:.0f}%\n\n"
            f"[dim]Transform from student to ML Systems Engineer![/dim]",
            title="🚀 Your Epic Journey",
            border_style="bright_blue",
        )
    )

    # Show milestone status
    for milestone_id in sorted(milestone_system.MILESTONES.keys()):
        milestone = status["milestones"][milestone_id]
        _show_milestone_status(console, milestone, args.detailed)

    # Show next steps
    if status["next_milestone"]:
        next_milestone = status["milestones"][status["next_milestone"]]
        console.print(
            Panel(
                f"[bold cyan]🎯 Next Achievement[/bold cyan]\n\n"
                f"[bold yellow]{next_milestone['emoji']} {next_milestone['title']}[/bold yellow]\n"
                f"[dim]{next_milestone['victory_condition']}[/dim]\n\n"
                f"[green]Ready to run![/green]\n"
                f"[dim]tito milestone run {next_milestone['id']}[/dim]",
                title="Next Milestone",
                border_style="bright_green",
            )
        )
    elif status["total_completed"] == total_milestones:
        console.print(
            Panel(
                f"[bold green]🏆 QUEST COMPLETE! 🏆[/bold green]\n\n"
                f"[green]You've achieved all {total_milestones} epic milestones![/green]\n"
                f"[bold white]You are now an ML Systems Engineer![/bold white]\n\n"
                f"[cyan]Share your achievement and inspire others![/cyan]",
                title="🌟 FULL MASTERY ACHIEVED",
                border_style="bright_green",
            )
        )
    elif status["total_unlocked"] == total_milestones:
        console.print(
            Panel(
                "[bold yellow]⚡ All milestones unlocked![/bold yellow]\n\n"
                "[yellow]Every milestone is ready to run.[/yellow]\n"
                "[dim]Run each with tito milestone run <id> to actually achieve it.[/dim]",
                title="🔓 All Milestones Ready",
                border_style="bright_yellow",
            )
        )

    return 0


def _show_milestone_status(console, milestone: dict, detailed: bool = False) -> None:
    """Show status for a single milestone."""
    # Status indicator
    if milestone["is_completed"]:
        status_icon = "✅"
        status_color = "bold green"
    elif milestone["is_unlocked"]:
        status_icon = "🔓"
        status_color = "green"
    elif milestone["can_unlock"]:
        status_icon = "⚡"
        status_color = "yellow"
    elif milestone["required_complete"] and not milestone["trigger_complete"]:
        status_icon = "🔒"
        status_color = "cyan"
    else:
        status_icon = "🔒"
        status_color = "dim"

    # Basic display
    milestone_content = (
        f"[{status_color}]{status_icon} {milestone['emoji']} {milestone['title']}[/{status_color}]\n"
        f"[dim]{milestone['victory_condition']}[/dim]"
    )

    # Add detailed information if requested
    if detailed:
        req_status = "✅" if milestone["required_complete"] else "❌"
        if milestone["trigger_module"]:
            trigger_status = "✅" if milestone["trigger_complete"] else "❌"
            trigger_text = milestone["trigger_module"]
        else:
            trigger_status = "•"
            trigger_text = "N/A"

        required_modules_str = ", ".join(f"{m:02d}" for m in milestone.get("required_modules", []))

        milestone_content += (
            f"\n\n[bold]Requirements:[/bold]\n"
            f"  {req_status} Modules: {required_modules_str}\n"
            f"  {trigger_status} Trigger: {trigger_text}\n"
            f"[bold]Capability:[/bold] {milestone['capability']}\n"
            f"[bold]Impact:[/bold] {milestone['real_world_impact']}"
        )

        if milestone["is_unlocked"] and milestone.get("unlock_date"):
            unlock_date = datetime.fromisoformat(milestone["unlock_date"]).strftime("%Y-%m-%d")
            milestone_content += f"\n[dim]Unlocked: {unlock_date}[/dim]"

    console.print(Panel(milestone_content, title=f"Milestone {milestone['id']}", border_style=status_color))


def show_timeline(config, console, args: Namespace) -> int:
    """Handle milestone timeline command."""
    milestone_system = MilestoneSystem(config)
    status = milestone_system.get_milestone_status()

    if args.horizontal:
        _show_horizontal_timeline(console, status, milestone_system)
    else:
        _show_tree_timeline(console, status, milestone_system)

    return 0


def _show_horizontal_timeline(console, status: dict, milestone_system: MilestoneSystem) -> None:
    """Show horizontal progress bar timeline."""
    total_milestones = len(milestone_system.MILESTONES)
    console.print(
        Panel(
            f"[bold cyan]🎮 Milestone Timeline[/bold cyan]\n\n"
            f"[bold]Progress:[/bold] {status['total_unlocked']}/{total_milestones} milestones unlocked",
            title="Your Epic Journey",
            border_style="bright_blue",
        )
    )

    # Create progress bar
    progress_width = 50
    total_milestones = len(milestone_system.MILESTONES)
    unlocked_width = int((status["total_unlocked"] / total_milestones) * progress_width)

    # Create milestone markers
    timeline = []
    for milestone_id in sorted(milestone_system.MILESTONES.keys()):
        milestone = status["milestones"][milestone_id]

        if milestone["is_unlocked"]:
            marker = f"[green]{milestone['emoji']}[/green]"
        elif milestone["can_unlock"]:
            marker = f"[yellow blink]{milestone['emoji']}[/yellow blink]"
        else:
            marker = f"[dim]{milestone['emoji']}[/dim]"

        timeline.append(marker)

    # Show timeline
    console.print(f"\n{'  '.join(timeline)}")

    # Progress bar
    filled = "█" * unlocked_width
    empty = "░" * (progress_width - unlocked_width)
    console.print(f"\n[green]{filled}[/green][dim]{empty}[/dim]")
    console.print(f"[dim]{status['overall_progress']:.0f}% complete[/dim]\n")


def _show_tree_timeline(console, status: dict, milestone_system: MilestoneSystem) -> None:
    """Show tree-style milestone timeline."""
    console.print(
        Panel(
            "[bold cyan]🎮 Milestone Progression Tree[/bold cyan]\n\n"
            "[bold]Your journey from student to ML Systems Engineer[/bold]",
            title="Epic Timeline",
            border_style="bright_blue",
        )
    )

    # Create tree structure
    tree = Tree("🚀 [bold]TinyTorch Mastery Journey[/bold]")

    for milestone_id in sorted(milestone_system.MILESTONES.keys()):
        milestone = status["milestones"][milestone_id]

        if milestone["is_unlocked"]:
            node_style = "green"
            icon = "✅"
        elif milestone["can_unlock"]:
            node_style = "yellow"
            icon = "⚡"
        else:
            node_style = "dim"
            icon = "🔒"

        branch = tree.add(f"[{node_style}]{icon} {milestone['emoji']} {milestone['title']}[/{node_style}]")

        # Add capability description
        branch.add(f"[dim]{milestone['capability']}[/dim]")

        # Add trigger module info
        if not milestone["trigger_module"]:
            required_modules_str = ", ".join(f"{m:02d}" for m in milestone.get("required_modules", []))
            if milestone["required_complete"]:
                branch.add(f"[green]✅ Prerequisites complete: {required_modules_str}[/green]")
            else:
                branch.add(f"[dim]🎯 Complete modules: {required_modules_str}[/dim]")
        elif milestone["trigger_complete"]:
            branch.add(f"[green]✅ {milestone['trigger_module']} completed[/green]")
        else:
            branch.add(f"[dim]🎯 Complete: {milestone['trigger_module']}[/dim]")

    console.print(tree)
    console.print()


def show_list(config, console, args: Namespace) -> int:
    """Handle milestone list command - show available milestones."""
    console.print(
        Panel(
            "[bold cyan]🏆 TinyTorch Milestones[/bold cyan]\n\n"
            "[dim]Recreate ML history from 1958 to 2018[/dim]",
            title="Available Milestones",
            border_style="bright_cyan",
        )
    )

    # Check module completion status from the canonical module progress file.
    completed_module_nums = _load_completed_module_numbers()

    # Check milestone completion
    milestone_progress = MilestoneSystem(config)._get_milestone_progress_data()
    completed_milestones = milestone_progress.get("completed_milestones", [])

    for milestone_id in sorted(MILESTONE_SCRIPTS.keys()):
        milestone = MILESTONE_SCRIPTS[milestone_id]
        required_modules = _required_modules_for(milestone)

        # Check if prerequisites met (required_modules contains integers)
        prereqs_met = all(mod in completed_module_nums for mod in required_modules)
        is_complete = milestone_id in completed_milestones

        # Status indicator
        if is_complete:
            status_icon = "✅"
            status_color = "green"
        elif prereqs_met:
            status_icon = "🎯"
            status_color = "yellow"
        else:
            status_icon = "🔒"
            status_color = "dim"

        # Build display
        if args.simple:
            console.print(
                f"[{status_color}]{status_icon} {milestone['id']} - {milestone['name']}[/{status_color}]"
            )
        else:
            milestone_display = (
                f"[{status_color}]{status_icon} {milestone['emoji']} {milestone['name']}[/{status_color}]\n"
                f"[bold]{milestone['title']}[/bold]\n"
                f"[dim]{milestone['description']}[/dim]\n"
                f"[dim]Historical: {milestone['historical_context']}[/dim]\n\n"
            )

            if prereqs_met and not is_complete:
                milestone_display += (
                    f"[bold yellow]▶ Run now:[/bold yellow] [cyan]tito milestone run {milestone_id}[/cyan]\n"
                )
            elif not prereqs_met:
                missing = [f"{m:02d}" for m in required_modules if m not in completed_module_nums]
                milestone_display += f"[dim]Required: Complete modules {', '.join(missing)}[/dim]\n"

            console.print(
                Panel(
                    milestone_display.strip(),
                    title=f"Milestone {milestone['id']} ({milestone['year']})",
                    border_style=status_color,
                )
            )

    return 0


def show_info(config, console, args: Namespace) -> int:
    """Handle milestone info command - show detailed information."""
    from .constants import MILESTONE_ALIASES

    milestone_id = args.milestone_id

    # Resolve name aliases (e.g., "perceptron" -> "01")
    if milestone_id.lower() in MILESTONE_ALIASES:
        milestone_id = MILESTONE_ALIASES[milestone_id.lower()]

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

    # Check status
    completed_module_nums = _load_completed_module_numbers()

    prereqs_met = all(m in completed_module_nums for m in milestone["required_modules"])

    # Display detailed info
    info_text = (
        f"[bold cyan]{milestone['emoji']} {milestone['name']}[/bold cyan]\n\n"
        f"[bold]{milestone['title']}[/bold]\n\n"
        f"[yellow]📚 Historical Context:[/yellow]\n"
        f"{milestone['historical_context']}\n\n"
        f"[yellow]🎯 Description:[/yellow]\n"
        f"{milestone['description']}\n\n"
        f"[yellow]📋 Required Modules:[/yellow]\n"
    )

    for mod in milestone["required_modules"]:
        mod_str = f"{mod:02d}"
        if mod in completed_module_nums:
            info_text += f"  [green]✓[/green] Module {mod_str}\n"
        else:
            info_text += f"  [red]✗[/red] Module {mod_str}\n"

    # Show scripts
    if "scripts" in milestone:
        info_text += f"\n[yellow]📂 Scripts ({len(milestone['scripts'])} parts):[/yellow]\n"
        for s in milestone["scripts"]:
            info_text += f"  • {s['name']}: {s['script']}\n"
    else:
        info_text += f"\n[yellow]📂 Script:[/yellow] {milestone['script']}\n"

    if prereqs_met:
        info_text += (
            f"\n[bold green]✅ Ready to run![/bold green]\n[cyan]tito milestone run {milestone_id}[/cyan]"
        )
    else:
        missing = [m for m in milestone["required_modules"] if m not in completed_module_nums]
        info_text += f"\n[bold yellow]🔒 Locked[/bold yellow]\nComplete modules: {', '.join(f'{m:02d}' for m in missing)}"

    console.print(
        Panel(
            info_text,
            title=f"Milestone {milestone_id} Information",
            border_style="bright_cyan",
            padding=(1, 2),
        )
    )

    return 0
