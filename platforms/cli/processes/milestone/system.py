"""Milestone state: unlock/completion tracking, prerequisite checks, and the
auto-run-on-unlock hook `tren module complete` calls into.

Split out of the old flat milestone.py so state and unlock logic has one
home, separate from command dispatch (command.py) and display (display.py).
"""

import importlib
import json
from datetime import datetime
from pathlib import Path

import yaml
from rich import box
from rich.panel import Panel

from platforms.cli.core.console import get_console
from .constants import MILESTONE_SCRIPTS, MODULE_EXPORT_CHECKS


def _module_progress_to_int(module_value):
    """Normalize module progress entries like 1, "01", or "01_tensor" to int."""
    if isinstance(module_value, int):
        return module_value
    if not isinstance(module_value, str):
        return None
    prefix = module_value.split("_", 1)[0]
    try:
        return int(prefix)
    except ValueError:
        return None


def _load_completed_module_numbers() -> set:
    """Read completed module numbers from the canonical user_data progress file."""
    progress_file = Path("user_data") / "progress.json"
    completed = set()
    if not progress_file.exists():
        return completed

    try:
        with open(progress_file, 'r') as f:
            progress_data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return completed

    for module_value in progress_data.get("completed_modules", []):
        module_num = _module_progress_to_int(module_value)
        if module_num is not None:
            completed.add(module_num)
    return completed


def _required_modules_for(milestone: dict) -> list[int]:
    """Return all modules required by a milestone as sorted ints."""
    required = set()
    for module_value in milestone.get("required_modules", []):
        module_num = _module_progress_to_int(module_value)
        if module_num is not None:
            required.add(module_num)
    for script in milestone.get("scripts", []):
        for module_value in script.get("required_modules", []):
            module_num = _module_progress_to_int(module_value)
            if module_num is not None:
                required.add(module_num)
    return sorted(required)


def _validate_required_exports(required_modules: list[int]) -> list[str]:
    """Return missing or silently failed exports for the required modules."""
    failures = []

    for module_num in required_modules:
        for module_path, symbol_name in MODULE_EXPORT_CHECKS.get(module_num, []):
            try:
                module = importlib.import_module(module_path)
            except ImportError as exc:
                failures.append(f"{module_path}.{symbol_name}: import failed ({exc})")
                continue

            value = getattr(module, symbol_name, None)
            if value is None:
                failures.append(f"{module_path}.{symbol_name}: exported as None")

    return failures


class MilestoneSystem:
    """Core milestone tracking and management system."""

    def __init__(self, config):
        self.config = config
        self.console = get_console()

        # Load milestones from configuration file
        self.MILESTONES = self._load_milestones_config()

    def _load_milestones_config(self) -> dict:
        """Load milestone configuration from YAML files (main and era-specific)."""
        config_path = Path("data") / "milestones" / "milestones.yml"
        milestones = {}

        # Try to load main milestones.yml first
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)

                # Convert to expected format
                for milestone_id, milestone_data in config['milestones'].items():
                    milestone_data['id'] = str(milestone_id)
                    milestones[str(milestone_id)] = milestone_data

            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not load main milestone config: {e}[/yellow]")

        # Also try to load era-specific configurations
        era_paths = [
            Path("data") / "milestones" / "foundation" / "milestone.yml",
            Path("data") / "milestones" / "revolution" / "milestone.yml",
            Path("data") / "milestones" / "generation" / "milestone.yml"
        ]

        for era_path in era_paths:
            if era_path.exists():
                try:
                    with open(era_path, 'r') as f:
                        era_config = yaml.safe_load(f)

                    if 'milestone' in era_config:
                        milestone_data = era_config['milestone']
                        milestone_id = milestone_data['id']
                        milestones[str(milestone_id)] = milestone_data

                except Exception as e:
                    self.console.print(f"[yellow]Warning: Could not load era config {era_path}: {e}[/yellow]")

        # If no milestones loaded, use MILESTONE_SCRIPTS as fallback
        if not milestones:
            return MILESTONE_SCRIPTS

        return milestones

    def get_milestone_status(self) -> dict:
        """Get current milestone progress status."""
        milestone_data = self._get_milestone_progress_data()

        status = {
            "milestones": {},
            "overall_progress": 0,
            "total_unlocked": 0,
            "total_completed": 0,
            "next_milestone": None
        }

        total_milestones = len(self.MILESTONES)
        unlocked_count = 0
        completed_count = 0

        for milestone_id, milestone in self.MILESTONES.items():
            # Check if all required modules are complete (no more checkpoint dependencies)
            required_modules = _required_modules_for(milestone)
            required_complete = all(
                self._is_module_completed(f"{mod:02d}")
                for mod in required_modules
            )

            # Check if milestone is unlocked (ready to run, not the same as actually
            # run and achieved -- see is_completed below)
            is_unlocked = milestone_id in milestone_data.get("unlocked_milestones", [])

            # Check if the milestone has actually been run and passed
            is_completed = milestone_id in milestone_data.get("completed_milestones", [])

            # Check if trigger module is completed (if trigger_module exists)
            trigger_module = milestone.get("trigger_module", "")
            if trigger_module:
                trigger_complete = self._is_module_completed(trigger_module)
            else:
                # No trigger module - consider complete if all required modules done
                trigger_complete = required_complete

            milestone_status = {
                "id": milestone_id,
                "name": milestone["name"],
                "title": milestone["title"],
                "emoji": milestone.get("emoji", "🎯"),
                "trigger_module": trigger_module,
                "required_modules": required_modules,
                "victory_condition": milestone.get("victory_condition", milestone.get("description", "")),
                "capability": milestone.get("capability", milestone.get("description", "")),
                "real_world_impact": milestone.get("real_world_impact", milestone.get("historical_context", "")),
                "required_complete": required_complete,
                "trigger_complete": trigger_complete,
                "is_unlocked": is_unlocked,
                "is_completed": is_completed,
                "can_unlock": required_complete and trigger_complete and not is_unlocked,
                "unlock_date": milestone_data.get("unlock_dates", {}).get(milestone_id)
            }

            status["milestones"][milestone_id] = milestone_status

            if is_completed:
                completed_count += 1
            if is_unlocked:
                unlocked_count += 1
            elif milestone_status["can_unlock"] and not status["next_milestone"]:
                status["next_milestone"] = milestone_id

        status["total_unlocked"] = unlocked_count
        status["total_completed"] = completed_count
        status["overall_progress"] = (unlocked_count / total_milestones) * 100 if total_milestones > 0 else 0

        return status

    def run_milestone_test(self, milestone_id: str) -> dict:
        """Run tests to validate milestone achievement."""
        if milestone_id not in self.MILESTONES:
            return {"success": False, "error": f"Milestone {milestone_id} not found"}

        milestone = self.MILESTONES[milestone_id]

        # Check all required modules are complete
        required_modules = milestone.get("required_modules", [])
        failed_modules = []

        for mod in required_modules:
            if not self._is_module_completed(f"{mod:02d}"):
                failed_modules.append(f"{mod:02d}")

        if failed_modules:
            return {
                "success": False,
                "error": f"Required modules not completed: {', '.join(failed_modules)}",
                "milestone_name": milestone["name"]
            }

        # Check trigger module completion
        trigger_module = milestone.get("trigger_module", "")
        if trigger_module and not self._is_module_completed(trigger_module):
            return {
                "success": False,
                "error": f"Trigger module {trigger_module} not completed",
                "milestone_name": milestone["name"]
            }

        # All tests passed
        return {
            "success": True,
            "milestone_id": milestone_id,
            "milestone_name": milestone["name"],
            "title": milestone.get("title", ""),
            "capability": milestone.get("capability", milestone.get("description", "")),
            "victory_condition": milestone.get("victory_condition", "")
        }

    def _unlock_milestone(self, milestone_id: str) -> None:
        """Record milestone unlock in progress tracking."""
        milestone_data = self._get_milestone_progress_data()

        if milestone_id not in milestone_data["unlocked_milestones"]:
            milestone_data["unlocked_milestones"].append(milestone_id)
            milestone_data["unlock_dates"][milestone_id] = datetime.now().isoformat()
            milestone_data["total_unlocked"] = len(milestone_data["unlocked_milestones"])

        self._save_milestone_progress_data(milestone_data)

    def _is_module_completed(self, module_name: str) -> bool:
        """Check if a module has been completed."""
        # Check module progress file
        progress_file = Path("user_data") / "progress.json"
        if progress_file.exists():
            try:
                with open(progress_file, 'r') as f:
                    progress_data = json.load(f)
                    module_num = _module_progress_to_int(module_name)
                    completed_nums = {
                        _module_progress_to_int(mod)
                        for mod in progress_data.get("completed_modules", [])
                    }
                    return module_num in completed_nums
            except (json.JSONDecodeError, IOError):
                pass
        return False

    def _get_milestone_progress_data(self) -> dict:
        """Get or create milestone progress data."""
        progress_dir = Path("user_data")
        progress_file = progress_dir / "milestones.json"

        progress_dir.mkdir(exist_ok=True)

        if progress_file.exists():
            try:
                with open(progress_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        return {
            "completed_milestones": [],
            "completion_dates": {},
            "unlocked_milestones": [],
            "unlock_dates": {},
            "total_unlocked": 0,
            "achievements": []
        }

    def _save_milestone_progress_data(self, milestone_data: dict) -> None:
        """Save milestone progress data."""
        progress_dir = Path("user_data")
        progress_file = progress_dir / "milestones.json"

        progress_dir.mkdir(exist_ok=True)

        try:
            with open(progress_file, 'w') as f:
                json.dump(milestone_data, f, indent=2)
        except IOError:
            pass


def check_and_run_milestone_unlocks(config, console) -> None:
    """Run any milestone that just became unlockable, right where it's called.

    Called from `tren module complete` after progress updates. Milestones
    used to be a separate step: complete a module, see a panel telling
    you to go run `tren milestone run <id>` yourself. Folding that run
    into the same completion flow makes the milestone feel like a
    natural checkpoint in the module progression instead of a detached
    extra command to remember.

    Lives here rather than in module_workflow/workflow.py so the Milestone
    component's process logic (checking unlocks, running, marking
    complete) stays in one place instead of being split between two
    files depending on which command happened to trigger it.
    """
    try:
        progress_file = config.project_root / "user_data" / "progress.json"
        try:
            with open(progress_file, 'r') as f:
                progress = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            progress = {}
        completed = {
            module_num
            for module_num in (_module_progress_to_int(m) for m in progress.get("completed_modules", []))
            if module_num is not None
        }

        milestones_file = config.project_root / "user_data" / "milestones.json"
        milestones_file.parent.mkdir(parents=True, exist_ok=True)
        if milestones_file.exists():
            try:
                with open(milestones_file, 'r') as f:
                    milestone_progress = json.load(f)
            except Exception:
                milestone_progress = {}
        else:
            milestone_progress = {}

        unlocked = set(milestone_progress.get("unlocked_milestones", []))
        completed_milestones = set(milestone_progress.get("completed_milestones", []))
        newly_unlocked = []

        for milestone_id, milestone in sorted(MILESTONE_SCRIPTS.items()):
            if milestone_id in unlocked or milestone_id in completed_milestones:
                continue
            required = set(_required_modules_for(milestone))
            if required.issubset(completed):
                unlocked.add(milestone_id)
                newly_unlocked.append((milestone_id, milestone))

        if not newly_unlocked:
            return

        milestone_progress["unlocked_milestones"] = sorted(unlocked)
        milestone_progress["completed_milestones"] = sorted(completed_milestones)
        milestone_progress.setdefault("unlock_dates", {})
        for milestone_id, _ in newly_unlocked:
            milestone_progress["unlock_dates"][milestone_id] = datetime.now().isoformat()
        milestone_progress["total_unlocked"] = len(unlocked)
        milestone_progress.setdefault("achievements", [])

        with open(milestones_file, 'w') as f:
            json.dump(milestone_progress, f, indent=2)

        for milestone_id, milestone in newly_unlocked:
            console.print()
            console.print(Panel.fit(
                f"[bold green]Milestone unlocked[/bold green]\n\n"
                f"[bold cyan]Milestone {milestone_id}: {milestone['name']}[/bold cyan]\n"
                f"{milestone['description']}\n\n"
                f"[dim]Running it now...[/dim]",
                border_style="green",
                box=box.DOUBLE,
            ))
            console.print()

            # Local import: MilestoneCommand lives in command.py, which
            # imports MILESTONE_SCRIPTS etc. from this module at load time.
            # A module-level import here would be circular; deferring it to
            # call time (this function only ever runs after both modules
            # are already fully loaded) breaks that cycle.
            from .command import MilestoneCommand
            from argparse import Namespace

            # skip_checks=True: the required-modules check above just
            # confirmed this milestone's prerequisites are met, no need
            # for _handle_run_command to redo that same check.
            milestone_command = MilestoneCommand(config)
            milestone_command._handle_run_command(
                Namespace(milestone_id=milestone_id, part=None, skip_checks=True)
            )
            console.print()

    except Exception as e:
        # Don't fail the module-completion workflow if milestone checking fails
        console.print(f"[dim]Note: Could not check milestone unlocks: {e}[/dim]")
