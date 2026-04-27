"""Smoke tests for streamlit_app — verifies it parses without import errors."""

import sys
from unittest.mock import MagicMock, patch


def test_streamlit_app_imports_without_error() -> None:
    """streamlit_app.py must be importable without triggering the build flow."""
    streamlit_mock = MagicMock()
    requests_mock = MagicMock()

    # file_uploader returns None → `uploaded and build_clicked` is False, so
    # the build body never executes during the import-level top-level Streamlit run.
    streamlit_mock.file_uploader.return_value = None
    streamlit_mock.button.return_value = False
    streamlit_mock.stop.side_effect = SystemExit  # mirrors real st.stop() behaviour

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

    assert True  # reached here without ImportError or unexpected exception
