"""
Core CLI functionality and shared utilities.
"""

from .config import CLIConfig
from .console import get_console
from .exceptions import ExecutionError, TrenTorchCLIError, ValidationError
from .modules import (
    clear_cache,
    get_module_display_name,
    get_module_mapping,
    get_module_name,
    get_next_module,
    get_total_modules,
    module_exists,
    normalize_module_number,
)

__all__ = [
    "get_console",
    "TrenTorchCLIError",
    "ValidationError",
    "ExecutionError",
    "CLIConfig",
    # Module utilities
    "get_module_mapping",
    "get_module_name",
    "get_module_display_name",
    "get_next_module",
    "normalize_module_number",
    "get_total_modules",
    "module_exists",
    "clear_cache",
]
