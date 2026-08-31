"""
TrenTorch Local Companion Server.

Provides a lightweight, zero-dependency HTTP & SSE server that connects
local module source code to the interactive TrenTorch Visualizer Web UI.
"""

from .command import ServeCommand

__all__ = ["ServeCommand"]
