"""
Regression test: demonstrate_crisis()'s random-search loop must actually
report the best random configuration it found, not silently discard it.

Found by direct bug hunt: the loop computed a new best-so-far
`(w1, w2, b, "Random")` tuple but never assigned or used it -- a bare
expression statement that does nothing (confirmed via `ruff` B018,
"useless expression"). The best random-search config was thrown away
the moment it was found.
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

from rich.console import Console

MODULE_PATH = Path(__file__).parent.parent / "02_1969_xor" / "01_xor_crisis.py"


def _load_module():
    """Import 01_xor_crisis.py as a module without running its
    if __name__ == "__main__" block."""
    trentorch_root = Path(__file__).parent.parent.parent.parent
    if str(trentorch_root) not in sys.path:
        sys.path.insert(0, str(trentorch_root))
    spec = importlib.util.spec_from_file_location("xor_crisis_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    with patch("builtins.print"):
        spec.loader.exec_module(module)
    return module


def test_demonstrate_crisis_reports_best_random_config():
    module = _load_module()

    from io import StringIO

    buf = StringIO()
    module.console = Console(file=buf, width=120, no_color=True)

    module.demonstrate_crisis()

    output = buf.getvalue()
    assert "Best from random search" in output
    # Before the fix, the winning (w1, w2, b) from the random-search loop
    # was computed and then discarded -- nothing after "Best from random
    # search" ever reported which weights actually produced it.
    assert "w1=" in output and "w2=" in output and "b=" in output, (
        "the best random-search weight configuration was found but never reported"
    )
