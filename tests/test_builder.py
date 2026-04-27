"""Unit tests for Python_to_exe_maker.builder — all subprocess calls are mocked."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from Python_to_exe_maker.builder import (
    build_exe,
    check_needs_refactoring,
    ensure_pyinstaller,
    get_output_extension,
)


# ---------------------------------------------------------------------------
# get_output_extension
# ---------------------------------------------------------------------------


def test_get_output_extension_windows() -> None:
    with patch.object(sys, "platform", "win32"):
        assert get_output_extension() == ".exe"


def test_get_output_extension_linux() -> None:
    with patch.object(sys, "platform", "linux"):
        assert get_output_extension() == ""


def test_get_output_extension_macos() -> None:
    with patch.object(sys, "platform", "darwin"):
        assert get_output_extension() == ""


# ---------------------------------------------------------------------------
# ensure_pyinstaller
# ---------------------------------------------------------------------------


@patch("Python_to_exe_maker.builder.subprocess.run")
@patch("Python_to_exe_maker.builder.importlib.util.find_spec", return_value=None)
def test_ensure_pyinstaller_installs_when_missing(
    mock_find: MagicMock, mock_run: MagicMock
) -> None:
    ensure_pyinstaller()
    mock_run.assert_called_once_with(
        [sys.executable, "-m", "pip", "install", "pyinstaller"],
        check=True,
    )


@patch("Python_to_exe_maker.builder.subprocess.run")
@patch("Python_to_exe_maker.builder.importlib.util.find_spec", return_value=MagicMock())
def test_ensure_pyinstaller_skips_when_present(
    mock_find: MagicMock, mock_run: MagicMock
) -> None:
    ensure_pyinstaller()
    mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# check_needs_refactoring
# ---------------------------------------------------------------------------


@patch("Python_to_exe_maker.builder.subprocess.run")
def test_check_needs_refactoring_returns_issues(
    mock_run: MagicMock, tmp_project: Path
) -> None:
    mock_run.return_value = MagicMock(stdout="hello.py:1:1: E302 expected 2 blank lines\n")
    issues = check_needs_refactoring(tmp_project)
    assert len(issues) == 1
    assert "E302" in issues[0]


@patch("Python_to_exe_maker.builder.subprocess.run")
def test_check_needs_refactoring_returns_empty_when_clean(
    mock_run: MagicMock, tmp_project: Path
) -> None:
    mock_run.return_value = MagicMock(stdout="")
    issues = check_needs_refactoring(tmp_project)
    assert issues == []


# ---------------------------------------------------------------------------
# build_exe
# ---------------------------------------------------------------------------


def test_build_exe_raises_for_missing_script(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        build_exe(tmp_path / "nonexistent.py", tmp_path)


def test_build_exe_raises_for_non_py_file(tmp_path: Path) -> None:
    bad = tmp_path / "script.txt"
    bad.write_text("hello", encoding="utf-8")
    with pytest.raises(ValueError, match=r"Expected a \.py file"):
        build_exe(bad, tmp_path)


@patch("Python_to_exe_maker.builder.shutil.rmtree")
@patch("Python_to_exe_maker.builder.subprocess.run")
def test_build_exe_calls_pyinstaller_with_correct_args(
    mock_run: MagicMock,
    mock_rmtree: MagicMock,
    sample_script: Path,
    tmp_project: Path,
) -> None:
    ext = get_output_extension()
    dist_dir = tmp_project / "dist"
    dist_dir.mkdir()
    binary_in_dist = dist_dir / f"hello{ext}"
    binary_in_dist.write_bytes(b"\x7fELF")  # fake binary content

    build_exe(sample_script, tmp_project)

    pyinstaller_call = mock_run.call_args_list[0]
    args = pyinstaller_call[0][0]
    assert sys.executable in args
    assert "-m" in args
    assert "PyInstaller" in args
    assert "--onefile" in args
    assert str(sample_script) in args


@patch("Python_to_exe_maker.builder.shutil.rmtree")
@patch("Python_to_exe_maker.builder.subprocess.run")
def test_build_exe_cleans_up_artifacts(
    mock_run: MagicMock,
    mock_rmtree: MagicMock,
    sample_script: Path,
    tmp_project: Path,
) -> None:
    ext = get_output_extension()
    dist_dir = tmp_project / "dist"
    dist_dir.mkdir()
    (dist_dir / f"hello{ext}").write_bytes(b"\x7fELF")

    build_exe(sample_script, tmp_project)

    # hook file should be gone
    assert not (tmp_project / "hook-inputhook.py").exists()
    # rmtree should have been called for build/ and dist/
    assert mock_rmtree.call_count >= 1


@patch("Python_to_exe_maker.builder.subprocess.run", side_effect=Exception("pyinstaller crashed"))
def test_build_exe_cleans_up_on_failure(
    mock_run: MagicMock, sample_script: Path, tmp_project: Path
) -> None:
    with pytest.raises(Exception, match="pyinstaller crashed"):
        build_exe(sample_script, tmp_project)
    # hook file must be cleaned up even on failure
    assert not (tmp_project / "hook-inputhook.py").exists()
