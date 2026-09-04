"""
Coverage for path_manager.py, which persists a venv's bin directory onto
the user's PATH (via the Windows registry or a shell rc file) so `tren`
works from any terminal without activating the venv first.

Every test here goes through the module's pure decision logic
(is_on_path, _detect_shell_rc_file) or a real filesystem write scoped
to tmp_path -- none of them touch the real Windows registry or the
real user's actual shell rc file.
"""

import os
import sys

import pytest

from platforms.cli.core import path_manager


class TestIsOnPath:
    def test_bin_dir_present_is_detected(self, tmp_path):
        bin_dir = tmp_path / "venv" / "bin"
        path_value = os.pathsep.join(["/usr/bin", str(bin_dir), "/usr/local/bin"])
        assert path_manager.is_on_path(bin_dir, path_value) is True

    def test_bin_dir_absent_is_not_detected(self, tmp_path):
        bin_dir = tmp_path / "venv" / "bin"
        other_dir = tmp_path / "venv" / "elsewhere"
        path_value = os.pathsep.join(["/usr/bin", str(other_dir)])
        assert path_manager.is_on_path(bin_dir, path_value) is False

    def test_empty_path_value(self, tmp_path):
        bin_dir = tmp_path / "venv" / "bin"
        assert path_manager.is_on_path(bin_dir, "") is False

    @pytest.mark.skipif(sys.platform != "win32", reason="case-insensitivity is Windows-only behavior")
    def test_case_insensitive_on_windows(self, tmp_path):
        bin_dir = tmp_path / "Venv" / "Scripts"
        path_value = str(bin_dir).upper()
        assert path_manager.is_on_path(bin_dir, path_value) is True


class TestDetectShellRcFile:
    def test_zsh_maps_to_zshrc(self, monkeypatch):
        monkeypatch.setenv("SHELL", "/bin/zsh")
        assert path_manager._detect_shell_rc_file().name == ".zshrc"

    def test_bash_maps_to_bashrc(self, monkeypatch):
        monkeypatch.setenv("SHELL", "/bin/bash")
        assert path_manager._detect_shell_rc_file().name == ".bashrc"

    def test_unknown_shell_falls_back_to_profile(self, monkeypatch):
        monkeypatch.setenv("SHELL", "/bin/fish")
        assert path_manager._detect_shell_rc_file().name == ".profile"

    def test_missing_shell_var_falls_back_to_profile(self, monkeypatch):
        monkeypatch.delenv("SHELL", raising=False)
        assert path_manager._detect_shell_rc_file().name == ".profile"


class TestPersistUnix:
    def test_appends_marked_export_line_to_empty_rc_file(self, tmp_path):
        rc_file = tmp_path / ".bashrc"
        bin_dir = tmp_path / "venv" / "bin"

        success, message = path_manager._persist_unix(bin_dir, rc_file=rc_file)

        assert success is True
        content = rc_file.read_text(encoding="utf-8")
        assert path_manager._MARKER_START in content
        assert path_manager._MARKER_END in content
        assert str(bin_dir) in content
        assert str(rc_file) in message

    def test_appends_to_existing_rc_file_without_clobbering_it(self, tmp_path):
        rc_file = tmp_path / ".bashrc"
        rc_file.write_text("alias ll='ls -la'\n", encoding="utf-8")
        bin_dir = tmp_path / "venv" / "bin"

        path_manager._persist_unix(bin_dir, rc_file=rc_file)

        content = rc_file.read_text(encoding="utf-8")
        assert "alias ll='ls -la'" in content
        assert path_manager._MARKER_START in content

    def test_second_run_does_not_duplicate_the_marker(self, tmp_path):
        rc_file = tmp_path / ".bashrc"
        bin_dir = tmp_path / "venv" / "bin"

        path_manager._persist_unix(bin_dir, rc_file=rc_file)
        first_content = rc_file.read_text(encoding="utf-8")

        success, message = path_manager._persist_unix(bin_dir, rc_file=rc_file)

        assert success is True
        assert "already configured" in message
        assert rc_file.read_text(encoding="utf-8") == first_content
        assert first_content.count(path_manager._MARKER_START) == 1

    def test_no_trailing_newline_in_existing_file_still_produces_valid_syntax(self, tmp_path):
        rc_file = tmp_path / ".bashrc"
        rc_file.write_text("alias ll='ls -la'", encoding="utf-8")  # no trailing newline
        bin_dir = tmp_path / "venv" / "bin"

        path_manager._persist_unix(bin_dir, rc_file=rc_file)

        content = rc_file.read_text(encoding="utf-8")
        # The pre-existing line and the new export must not have been
        # concatenated onto the same line.
        assert "alias ll='ls -la'\n" in content
        assert f'export PATH="{bin_dir}:$PATH"' in content


class TestAddBinDirToPath:
    def test_already_on_path_short_circuits_without_touching_anything(self, monkeypatch, tmp_path):
        bin_dir = tmp_path / "venv" / "bin"
        monkeypatch.setattr(path_manager, "is_on_path", lambda *a, **k: True)

        success, message = path_manager.add_bin_dir_to_path(bin_dir)

        assert success is True
        assert "already" in message

    def test_dispatches_to_windows_persister_on_windows(self, monkeypatch, tmp_path):
        bin_dir = tmp_path / "venv" / "Scripts"
        monkeypatch.setattr(path_manager, "is_on_path", lambda *a, **k: False)
        monkeypatch.setattr(path_manager, "is_windows", lambda: True)
        called = {}

        def fake_windows(target):
            called["bin_dir"] = target
            return True, "added via registry"

        monkeypatch.setattr(path_manager, "_persist_windows", fake_windows)

        success, message = path_manager.add_bin_dir_to_path(bin_dir)

        assert success is True
        assert called["bin_dir"] == bin_dir.resolve()
        assert message == "added via registry"

    def test_dispatches_to_unix_persister_off_windows(self, monkeypatch, tmp_path):
        bin_dir = tmp_path / "venv" / "bin"
        monkeypatch.setattr(path_manager, "is_on_path", lambda *a, **k: False)
        monkeypatch.setattr(path_manager, "is_windows", lambda: False)
        called = {}

        def fake_unix(target):
            called["bin_dir"] = target
            return True, "added via rc file"

        monkeypatch.setattr(path_manager, "_persist_unix", fake_unix)

        success, message = path_manager.add_bin_dir_to_path(bin_dir)

        assert success is True
        assert called["bin_dir"] == bin_dir.resolve()
        assert message == "added via rc file"
