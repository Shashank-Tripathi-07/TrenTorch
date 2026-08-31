"""
TrenTorch Interactive Terminal User Interface (TUI).

Powered by Textual for zero-friction module navigation, live testing,
milestone execution, and system diagnostics without memorizing CLI syntax.
"""

from .command import TUICommand
from .app import TrenTorchApp, launch_tui

__all__ = ["TUICommand", "TrenTorchApp", "launch_tui"]
