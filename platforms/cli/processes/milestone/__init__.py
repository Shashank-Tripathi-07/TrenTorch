"""Milestone package: state (system.py), display (display.py), and the
`tren milestone` command dispatcher (command.py).

Re-exports the names external callers already depend on
(`platforms.cli.main`, `module_workflow/workflow.py`,
`cli_platform/dev/test.py`, and the CLI test suite) so this package split
doesn't change any import path outside of it.
"""

from .command import MilestoneCommand
from .constants import (
    MILESTONE_ACHIEVEMENT_HIGHLIGHTS,
    MILESTONE_ALIASES,
    MILESTONE_SCRIPTS,
    MODULE_EXPORT_CHECKS,
)
from .system import (
    MilestoneSystem,
    _load_completed_module_numbers,
    _module_progress_to_int,
    _required_modules_for,
    _validate_required_exports,
    check_and_run_milestone_unlocks,
)

__all__ = [
    "MilestoneCommand",
    "MilestoneSystem",
    "check_and_run_milestone_unlocks",
    "MILESTONE_ALIASES",
    "MILESTONE_SCRIPTS",
    "MILESTONE_ACHIEVEMENT_HIGHLIGHTS",
    "MODULE_EXPORT_CHECKS",
    "_load_completed_module_numbers",
    "_module_progress_to_int",
    "_required_modules_for",
    "_validate_required_exports",
]
