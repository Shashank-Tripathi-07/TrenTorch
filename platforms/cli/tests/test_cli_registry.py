"""
CLI Registry Tests - Validate all commands are properly registered and accessible

This test suite ensures:
1. All commands in TrenTorchCLI.commands are valid BaseCommand subclasses
2. All commands have proper metadata (name, description)
3. All commands can be invoked via argparse
4. No commands are missing from registration
5. No orphaned command files exist without registration
"""

import argparse
import sys
from pathlib import Path

import pytest

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from platforms.cli.commands.base import BaseCommand
from platforms.cli.core.config import CLIConfig
from platforms.cli.main import TrenTorchCLI


class TestCLIRegistry:
    """Test that all commands are properly registered in the CLI."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cli = TrenTorchCLI()
        self.config = CLIConfig.from_project_root()

    def test_all_commands_are_base_command_subclasses(self):
        """Verify all registered commands inherit from BaseCommand."""
        for cmd_name, cmd_class in self.cli.commands.items():
            assert issubclass(cmd_class, BaseCommand), (
                f"Command '{cmd_name}' ({cmd_class.__name__}) must inherit from BaseCommand"
            )

    def test_all_commands_have_description(self):
        """Verify all commands have a description."""
        for cmd_name, cmd_class in self.cli.commands.items():
            cmd_instance = cmd_class(self.config)
            assert hasattr(cmd_instance, "description"), (
                f"Command '{cmd_name}' must have a 'description' attribute"
            )
            assert cmd_instance.description, f"Command '{cmd_name}' has empty description"
            assert len(cmd_instance.description) > 10, (
                f"Command '{cmd_name}' description too short: '{cmd_instance.description}'"
            )

    def test_all_commands_implement_execute(self):
        """Verify all commands implement execute() method."""
        for cmd_name, cmd_class in self.cli.commands.items():
            cmd_instance = cmd_class(self.config)
            assert hasattr(cmd_instance, "execute"), f"Command '{cmd_name}' must implement execute() method"
            assert callable(cmd_instance.execute), f"Command '{cmd_name}' execute must be callable"

    def test_all_commands_implement_add_arguments(self):
        """Verify all commands implement add_arguments() method."""
        for cmd_name, cmd_class in self.cli.commands.items():
            cmd_instance = cmd_class(self.config)
            assert hasattr(cmd_instance, "add_arguments"), (
                f"Command '{cmd_name}' must implement add_arguments() method"
            )
            assert callable(cmd_instance.add_arguments), (
                f"Command '{cmd_name}' add_arguments must be callable"
            )

    def test_parser_creation_succeeds(self):
        """Verify the argument parser can be created without errors."""
        parser = self.cli.create_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_all_commands_registered_in_parser(self):
        """Verify all registered commands appear in the parser."""
        parser = self.cli.create_parser()

        # Get all subparsers
        subparsers_actions = [
            action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
        ]

        assert len(subparsers_actions) == 1, "Should have exactly one subparsers group"

        # Get registered command names from parser
        subparser_choices = subparsers_actions[0].choices.keys()

        # Verify all commands in self.cli.commands are in parser
        for cmd_name in self.cli.commands.keys():
            assert cmd_name in subparser_choices, (
                f"Command '{cmd_name}' registered in TrenTorchCLI.commands but not in parser"
            )

    def test_no_duplicate_command_names(self):
        """Verify no duplicate command names in registry."""
        cmd_names = list(self.cli.commands.keys())
        unique_names = set(cmd_names)
        assert len(cmd_names) == len(unique_names), (
            f"Duplicate command names found: {[n for n in cmd_names if cmd_names.count(n) > 1]}"
        )

    def test_command_help_text_accessible(self):
        """Verify all commands can generate help text without errors."""
        parser = self.cli.create_parser()

        for cmd_name in self.cli.commands.keys():
            # This should not raise any exceptions
            help_text = parser.format_help()
            assert cmd_name in help_text or cmd_name == "src", f"Command '{cmd_name}' not found in help text"


class TestCommandFiles:
    """Test that command files match registry."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cli = TrenTorchCLI()
        self.tren_dir = Path(__file__).parent.parent
        self.commands_dir = self.tren_dir / "commands"
        self.cli_platform_dir = self.tren_dir / "cli_platform"
        self.processes_dir = self.tren_dir / "processes"

    def test_command_files_exist(self):
        """Verify all registered commands have corresponding files.

        Feature commands live under tren/platforms/ (cli_platform/ for
        bootstrapping/maintainer concerns, processes/ for the student-facing
        workflow); only genuinely shared code (base.py, export_utils.py,
        jupyter.py) stays in tren/commands/.
        """
        cmd_to_file = {
            "setup": self.cli_platform_dir / "setup.py",
            "system": self.cli_platform_dir / "system" / "__init__.py",
            "dev": self.cli_platform_dir / "dev" / "__init__.py",
            "package": self.cli_platform_dir / "package" / "__init__.py",
            "module": self.processes_dir / "module_workflow" / "__init__.py",
            "milestone": self.processes_dir / "milestone" / "__init__.py",
            "olympics": self.processes_dir / "olympics.py",
            "benchmark": self.processes_dir / "benchmark.py",
        }

        for cmd_name, file_path in cmd_to_file.items():
            if cmd_name in self.cli.commands:
                assert file_path.exists(), f"Command '{cmd_name}' registered but file missing: {file_path}"

    def test_no_orphaned_command_files(self):
        """Warn about command files that aren't registered anywhere."""
        # Only tren/commands/ itself is checked flat (base.py + shared
        # helpers); platforms/cli_platform/ and platforms/processes/ are
        # organized by feature, each folder containing exactly the files
        # that one command group owns, so there's nothing to orphan-check
        # there beyond "does the registered command's file exist" above.
        command_files = [
            f for f in self.commands_dir.glob("*.py") if f.name not in ["__init__.py", "base.py"]
        ]

        expected_files = {
            "export_utils.py",  # Helper for export functionality, shared by cli_platform/dev and processes/module_workflow
            "jupyter.py",  # Jupyter component: server lifecycle, %tren magic registration
        }

        orphaned = []
        for cmd_file in command_files:
            if cmd_file.name not in expected_files:
                orphaned.append(f"{cmd_file.name} -> not in expected files")

        if orphaned:
            pytest.fail(
                f"Found {len(orphaned)} orphaned command files:\n"
                + "\n".join(f"  - {item}" for item in orphaned)
                + "\n\nEither register these commands or move to platforms/"
            )


class TestEpilogDocumentation:
    """Test that epilog in parser matches actual available commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cli = TrenTorchCLI()

    def test_epilog_mentions_registered_commands(self):
        """Verify epilog mentions all registered command groups."""
        parser = self.cli.create_parser()
        epilog = parser.epilog

        # Key command groups that should be mentioned
        expected_groups = ["system", "module", "package", "milestone", "olympics"]

        missing = []
        for group in expected_groups:
            if group in self.cli.commands:
                if group not in epilog:
                    missing.append(group)

        if missing:
            pytest.fail(
                f"Commands registered but not in epilog: {missing}\n"
                f"Update epilog in tren/main.py create_parser() method"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
