"""
Configuration management for TrenTorch CLI.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass


def migrate_progress_dir(project_root: Path) -> None:
    """One-time migration of the progress-tracking directory to user_data/.

    Two directory names came before user_data/, each from a real rename in
    this project's history: .tito/ (before the tito->tren CLI rename) and
    .tren/ (before user_data/ made the directory visible instead of hidden,
    since students kept missing it existed at all). Either one holds real
    progress.json/milestones.json data that already exists on any machine
    that's run this CLI before, so renaming outright would silently reset
    that progress -- this only renames whichever legacy directory is found
    to user_data/ once, the first time user_data/ doesn't already exist,
    and never touches user_data/ once it's there. A fresh install with
    neither legacy directory just gets user_data/ created normally by
    whichever command needs it, with nothing to migrate.
    """
    user_data_dir = project_root / 'user_data'
    if user_data_dir.exists():
        return
    for legacy_name in ('.tren', '.tito'):
        legacy_dir = project_root / legacy_name
        if legacy_dir.exists():
            try:
                legacy_dir.rename(user_data_dir)
            except OSError:
                # Best effort; if the rename fails (e.g. cross-device on
                # some CI runners), leave the legacy dir in place rather
                # than crash startup.
                pass
            return


@dataclass
class CLIConfig:
    """Configuration for TrenTorch CLI."""

    # Project paths
    project_root: Path
    assignments_dir: Path
    trentorch_dir: Path
    bin_dir: Path
    modules_dir: Path  # Student working directory (src/)

    # Environment settings
    python_min_version: tuple = (3, 8)
    required_packages: list = None  # type: ignore

    # CLI settings
    verbose: bool = False
    no_color: bool = False

    def __post_init__(self):
        """Initialize default values."""
        if self.required_packages is None:
            # Core dependencies from requirements.txt (required section)
            self.required_packages = ['numpy', 'rich', 'yaml', 'pytest', 'jupytext']

    @classmethod
    def from_project_root(cls, project_root: Optional[Path] = None) -> 'CLIConfig':
        """Create config from project root directory."""
        if project_root is None:
            # Auto-detect project root
            current = Path.cwd()
            while current != current.parent:
                if (current / 'pyproject.toml').exists():
                    project_root = current
                    break
                current = current.parent
            else:
                project_root = Path.cwd()

        modules_path = project_root / 'data' / 'src'
        return cls(
            project_root=project_root,
            assignments_dir=project_root / 'assignments',
            modules_dir=modules_path,
            trentorch_dir=project_root / 'data' / 'trentorch',
            bin_dir=project_root / 'bin'
        )

    def validate(self, venv_path: Union[Path, str]='.venv') -> List[str]:
        """Validate the configuration and return any issues."""
        issues = []

        # Check Python version
        if sys.version_info < self.python_min_version:
            issues.append(f"Python {'.'.join(map(str, self.python_min_version))}+ required, "
                         f"found {sys.version_info.major}.{sys.version_info.minor}")

        # Check virtual environment (more robust detection)
        in_venv = (
            # Method 1: Check VIRTUAL_ENV environment variable
            os.environ.get('VIRTUAL_ENV') is not None or
            # Method 2: Check sys.prefix vs sys.base_prefix
            (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) or
            # Method 3: Check for sys.real_prefix (older Python versions)
            hasattr(sys, 'real_prefix') or
            # Method 4: Check if .venv directory exists and packages are available
            (venv_path.exists() and self._packages_available())
        )
        if not in_venv:
            issues.append(f"Virtual environment not activated. Run: source {venv_path}/bin/activate")

        # Check required directories (modules_dir is 'src/' where students work)
        if not self.modules_dir.exists():
            issues.append(f"Modules directory not found: {self.modules_dir}")

        # trentorch_dir check removed - the project root IS trentorch
        # if not self.trentorch_dir.exists():
        #     issues.append(f"TrenTorch package not found: {self.trentorch_dir}")

        # Check required packages
        for package in self.required_packages:
            try:
                __import__(package)
            except ImportError:
                issues.append(f"Missing dependency: {package}. Run: pip install -r requirements.txt")

        return issues

    def _packages_available(self) -> bool:
        """Check if required packages are available (helper for venv detection)."""
        try:
            for package in self.required_packages:
                __import__(package)
            return True
        except ImportError:
            return False
