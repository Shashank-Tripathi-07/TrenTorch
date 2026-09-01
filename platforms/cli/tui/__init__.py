"""
TrenTorch Interactive Terminal User Interface (TUI).

Powered by Textual for zero-friction module navigation, live testing,
milestone execution, and system diagnostics without memorizing CLI syntax.

Only ``TUICommand`` is exported here on purpose: it does not import
``textual`` at module load, so every ``tren`` invocation stays fast and
``textual`` can be an optional extra (``pip install trentorch[tui]``).
Import ``platforms.cli.tui.app`` directly when you need the app itself.
"""

from .command import TUICommand

__all__ = ["TUICommand"]
