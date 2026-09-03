"""
MC/DC coverage for SetupCommand.install_packages's Windows-reinstall-skip
decision and create_virtual_environment's Apple Silicon / Rosetta
detection decision.
"""

import platform
import subprocess

from platforms.cli.cli_platform.setup import SetupCommand
from platforms.cli.core.config import CLIConfig

# ---------------------------------------------------------------------------
# is_windows and self._check_package_installed("trentorch")
# ---------------------------------------------------------------------------


def _install_packages(tmp_path, monkeypatch, *, is_windows, trentorch_installed):
    monkeypatch.setattr(platform, "system", lambda: "Windows" if is_windows else "Linux")
    cmd = SetupCommand(CLIConfig.from_project_root(tmp_path))
    # Every essential package already "installed" so the real pip-install
    # loop for them never runs; trentorch's own status is what this
    # decision is actually about.
    monkeypatch.setattr(
        cmd, "_check_package_installed", lambda name: True if name != "trentorch" else trentorch_installed
    )

    def fake_run(cmd_args, **kwargs):
        return subprocess.CompletedProcess(cmd_args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    from io import StringIO

    from rich.console import Console

    buf = StringIO()
    cmd.console = Console(file=buf, width=120, no_color=True)
    cmd.install_packages()
    return buf.getvalue()


def test_windows_with_trentorch_already_installed_skips_reinstall(tmp_path, monkeypatch):
    """Baseline: is_windows True, trentorch already installed True ->
    skips the real pip install -e . step."""
    out = _install_packages(tmp_path, monkeypatch, is_windows=True, trentorch_installed=True)
    assert "skipping reinstall on Windows" in out


def test_windows_without_trentorch_installed_does_not_skip(tmp_path, monkeypatch):
    """is_windows True, trentorch not installed False -> the and is
    False, proceeds to the real install step instead of skipping.
    Paired with the baseline: only trentorch's install status differs,
    isolating that half of the and."""
    out = _install_packages(tmp_path, monkeypatch, is_windows=True, trentorch_installed=False)
    assert "skipping reinstall on Windows" not in out
    assert "Tren⚡️Torch installed" in out


def test_non_windows_with_trentorch_installed_does_not_skip(tmp_path, monkeypatch):
    """is_windows False -> the and is False regardless of trentorch's
    install status (the WinError 32 file-lock problem this skip exists
    for is Windows-specific). Paired with the baseline: only is_windows
    differs, isolating that half of the and."""
    out = _install_packages(tmp_path, monkeypatch, is_windows=False, trentorch_installed=True)
    assert "skipping reinstall on Windows" not in out
    assert "Tren⚡️Torch installed" in out


# ---------------------------------------------------------------------------
# platform.system() == "Darwin" and arch == "x86_64"
# ---------------------------------------------------------------------------


def _create_venv_arch_check(tmp_path, monkeypatch, *, system, arch, sysctl_output=None):
    monkeypatch.setattr(platform, "system", lambda: system)
    monkeypatch.setattr(platform, "machine", lambda: arch)

    # setup.py's create_virtual_environment does `import subprocess as sp`
    # locally to run the sysctl hardware check, and also uses the
    # module-level `subprocess.run` (imported at the top of this test file)
    # to actually create the venv -- both names resolve to the exact same
    # module object, so one dispatching fake has to serve both call sites;
    # monkeypatching them separately would just have the second overwrite
    # the first.
    def fake_run(cmd_args, **kwargs):
        if isinstance(cmd_args, list) and cmd_args and cmd_args[0] == "sysctl":
            if sysctl_output is not None:
                return subprocess.CompletedProcess(cmd_args, returncode=0, stdout=sysctl_output)
            return subprocess.CompletedProcess(cmd_args, returncode=1, stdout="")
        return subprocess.CompletedProcess(cmd_args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    cmd = SetupCommand(CLIConfig.from_project_root(tmp_path))
    from io import StringIO

    from rich.console import Console

    buf = StringIO()
    cmd.console = Console(file=buf, width=120, no_color=True)
    cmd.create_virtual_environment(force=False)
    return buf.getvalue()


def test_darwin_with_x86_64_checks_for_rosetta(tmp_path, monkeypatch):
    """Baseline: system == "Darwin" True, arch == "x86_64" True -> the
    Rosetta-detection hardware check runs (sysctl.proc_translated)."""
    out = _create_venv_arch_check(
        tmp_path, monkeypatch, system="Darwin", arch="x86_64", sysctl_output="Apple M1\n"
    )
    # Detecting Rosetta re-targets to arm64; the console reports it.
    assert "Rosetta" in out


def test_darwin_with_arm64_skips_rosetta_check(tmp_path, monkeypatch):
    """system == "Darwin" True, arch == "x86_64" False (already native
    arm64) -> the and is False, no Rosetta re-check needed. Paired with
    the baseline: only the reported arch differs, isolating that half of
    the and."""
    out = _create_venv_arch_check(tmp_path, monkeypatch, system="Darwin", arch="arm64")
    assert "Creating virtual environment" in out


def test_non_darwin_skips_rosetta_check_regardless_of_arch(tmp_path, monkeypatch):
    """system == "Darwin" is False -> the and is False regardless of
    arch (Rosetta is a macOS-specific concept). Paired with the
    baseline: only the platform differs, isolating that half of the and."""
    out = _create_venv_arch_check(tmp_path, monkeypatch, system="Linux", arch="x86_64")
    assert "Creating virtual environment" in out


# ---------------------------------------------------------------------------
# Rosetta re-targeting must build a real argv list, never a shell=True
# string: a prior version built f"arch -arm64 {python_exe} -m venv
# {venv_path}" and ran it with shell=True, so a venv_path containing a
# space (a real path, e.g. under "OneDrive - Company") silently split
# into multiple shell tokens instead of staying one argument.
# ---------------------------------------------------------------------------


def test_rosetta_venv_creation_uses_argv_list_not_shell_string(tmp_path, monkeypatch):
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(platform, "machine", lambda: "x86_64")

    # A spaced project root means create_virtual_environment's own
    # `project_root / ".venv"` (its actual venv_path, not a
    # dependency-injectable path) contains a space too.
    project_root = tmp_path / "my project"
    project_root.mkdir()
    expected_venv_path = str(project_root / ".venv")

    captured = {}

    def fake_run(cmd_args, **kwargs):
        if isinstance(cmd_args, list) and cmd_args and cmd_args[0] == "sysctl":
            return subprocess.CompletedProcess(cmd_args, returncode=0, stdout="Apple M1\n")
        captured["cmd_args"] = cmd_args
        captured["shell"] = kwargs.get("shell", False)
        return subprocess.CompletedProcess(cmd_args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    cmd = SetupCommand(CLIConfig.from_project_root(project_root))
    from io import StringIO

    from rich.console import Console

    cmd.console = Console(file=StringIO(), width=120, no_color=True)
    cmd.create_virtual_environment(force=False)

    assert captured["shell"] is not True, "venv creation must not go through shell=True"
    assert isinstance(captured["cmd_args"], list), "venv creation must pass a real argv list"
    assert expected_venv_path in captured["cmd_args"], (
        "the spaced venv path must survive as a single argv element, "
        f"got: {captured['cmd_args']}"
    )
    assert captured["cmd_args"][:2] == ["arch", "-arm64"]
