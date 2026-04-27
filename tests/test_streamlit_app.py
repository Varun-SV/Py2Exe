"""Smoke tests for streamlit_app — verifies it parses without import errors."""

import importlib
import sys
from unittest.mock import MagicMock, patch


def test_streamlit_app_imports_without_error() -> None:
    """streamlit_app.py must be importable (all top-level imports resolve)."""
    # Stub out heavy / network-bound modules before importing
    streamlit_mock = MagicMock()
    requests_mock = MagicMock()

    with (
        patch.dict(
            sys.modules,
            {
                "streamlit": streamlit_mock,
                "requests": requests_mock,
            },
        ),
        patch.dict("os.environ", {"GITHUB_TOKEN": "fake-token"}),
    ):
        if "streamlit_app" in sys.modules:
            del sys.modules["streamlit_app"]
        import streamlit_app  # noqa: F401 — import side-effect is the test

    assert True  # reached here without ImportError
