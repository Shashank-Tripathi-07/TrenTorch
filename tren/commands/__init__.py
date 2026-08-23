"""
CLI Commands package.

Each command is implemented as a separate module with proper separation of concerns.
Commands are organized into logical groups: system, module, and package.
"""

from .base import BaseCommand

# Individual commands
from .nbgrader import NBGraderCommand
from .benchmark import BenchmarkCommand

# Command groups (with subcommands organized in subfolders)
from .system import SystemCommand
from .module import ModuleWorkflowCommand
from .package import PackageCommand

__all__ = [
    'BaseCommand',
    # Individual commands
    'NBGraderCommand',
    'BenchmarkCommand',
    # Command groups
    'SystemCommand',
    'ModuleWorkflowCommand',
    'PackageCommand',
]
