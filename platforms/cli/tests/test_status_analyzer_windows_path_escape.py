"""
TrenTorchStatusAnalyzer.analyze_module() generates a small Python script
to subprocess-test whether a module's dev file imports cleanly, embedding
the module's directory path via an f-string:

    test_code = f'''
    sys.path.insert(0, '{module_path}')
    ...
    '''

Found by direct bug hunt, reproduced standalone before this test existed:
on Windows, module_path's backslashes aren't escaped for the generated
source. A path segment like "...\\02_activations" reads back as the
octal/control-char escape "\\x02activations" once the generated code is
parsed -- sys.path gets a corrupted, nonexistent path, and the "does this
module import?" check silently fails regardless of whether the module is
actually fine.

Only reproducible with an actual directory name matching that shape, so
this test creates one for real rather than mocking subprocess: the
regression is specifically in how the path gets embedded in the
generated source, not in anything subprocess.run does.
"""

from pathlib import Path

from platforms.cli.core.status_analyzer import TrenTorchStatusAnalyzer


def test_analyze_module_handles_octal_escape_shaped_directory_name(tmp_path):
    """A module directory whose name starts with a digit that reads as a
    Python octal/control-char escape after a path separator (e.g. "02_...")
    must still import successfully -- this is the exact shape of every real
    module directory in data/src/ (01_tensor, 02_activations, ...)."""
    module_dir = tmp_path / "02_activations"
    module_dir.mkdir()
    (module_dir / "02_activations.py").write_text("x = 1\n", encoding="utf-8")

    analyzer = TrenTorchStatusAnalyzer(Path(tmp_path))
    status = analyzer.analyze_module(module_dir)

    assert status.imports_successfully, (
        f"module import check failed -- issues: {status.issues} "
        "(likely the generated sys.path.insert() argument was corrupted)"
    )
