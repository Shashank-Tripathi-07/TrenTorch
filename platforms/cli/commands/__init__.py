"""
CLI Commands package.

Holds only what's genuinely shared across both platforms/cli_platform/ and
platforms/processes/: BaseCommand, export_utils.py's notebook/nbdev helpers,
and jupyter.py's server + %tren magic wiring. Every actual command lives
under tren/platforms/ now, organized by feature -- see tren/platforms/.
"""

from .base import BaseCommand

__all__ = [
    "BaseCommand",
]
