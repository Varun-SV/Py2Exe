"""Shared pytest fixtures."""

import pytest
from pathlib import Path


@pytest.fixture()
def tmp_project(tmp_path: Path) -> Path:
    """Return a temp directory with a minimal valid Python script inside."""
    script = tmp_path / "hello.py"
    script.write_text('print("hello")\n', encoding="utf-8")
    return tmp_path


@pytest.fixture()
def sample_script(tmp_project: Path) -> Path:
    """Return the path to the sample script inside tmp_project."""
    return tmp_project / "hello.py"
