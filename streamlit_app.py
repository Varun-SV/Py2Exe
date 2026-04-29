"""Streamlit web app for Py2Exe.

Users upload a ZIP of their Python project, configure build options, and the app:
1. Checks for flake8 refactoring issues
2. Pushes the project to a temporary GitHub branch
3. Triggers a GitHub Actions matrix build (ubuntu + windows)
4. Returns download buttons for both the Linux binary and Windows .exe
5. Deletes the temporary branch when done
"""

import io
import os
import re
import tempfile
import time
import zipfile
from pathlib import Path

import requests
import streamlit as st

from Python_to_exe_maker.builder import check_needs_refactoring

# ---------------------------------------------------------------------------
# Configuration (set these as secrets in Streamlit Community Cloud)
# ---------------------------------------------------------------------------
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "varun-sv/py2exe")
API_BASE = f"https://api.github.com/repos/{GITHUB_REPO}"
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------


def _get_default_branch() -> str:
    resp = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}", headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()["default_branch"]


def _get_branch_sha(branch: str) -> str:
    resp = requests.get(f"{API_BASE}/git/ref/heads/{branch}", headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()["object"]["sha"]


def create_branch(branch: str) -> None:
    """Create *branch* from the default branch HEAD."""
    base = _get_default_branch()
    sha = _get_branch_sha(base)
    resp = requests.post(
        f"{API_BASE}/git/refs",
        headers=HEADERS,
        json={"ref": f"refs/heads/{branch}", "sha": sha},
        timeout=15,
    )
    resp.raise_for_status()


def push_files_to_branch(branch: str, files: dict[str, bytes]) -> None:
    """Upload *files* (path → content) to *branch* via the Contents API."""
    import base64

    for rel_path, content in files.items():
        encoded = base64.b64encode(content).decode()
        resp = requests.put(
            f"{API_BASE}/contents/uploaded_project/{rel_path}",
            headers=HEADERS,
            json={
                "message": f"chore: upload {rel_path}",
                "content": encoded,
                "branch": branch,
            },
            timeout=30,
        )
        resp.raise_for_status()


def trigger_workflow(
    branch: str,
    main_file: str,
    exe_name: str,
    python_version: str,
    bundle_type: str,
    windowed: bool,
    icon_file: str,
    asset_files: str,
) -> None:
    """Dispatch the build workflow on *branch*."""
    resp = requests.post(
        f"{API_BASE}/actions/workflows/build.yml/dispatches",
        headers=HEADERS,
        json={
            "ref": branch,
            "inputs": {
                "branch": branch,
                "main_file": main_file,
                "exe_name": exe_name,
                "python_version": python_version,
                "bundle_type": bundle_type,
                "windowed": "true" if windowed else "false",
                "icon_file": icon_file,
                "asset_files": asset_files,
            },
        },
        timeout=15,
    )
    resp.raise_for_status()


def _find_run_id(branch: str, dispatch_time: float, timeout: int = 30) -> int:
    """Poll until a workflow run for *branch* appears; return its run_id."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(
            f"{API_BASE}/actions/runs",
            headers=HEADERS,
            params={"branch": branch, "event": "workflow_dispatch", "per_page": 5},
            timeout=15,
        )
        resp.raise_for_status()
        runs = resp.json().get("workflow_runs", [])
        for run in runs:
            if run["created_at"] and run["head_branch"] == branch:
                created = time.mktime(time.strptime(run["created_at"], "%Y-%m-%dT%H:%M:%SZ"))
                if created >= dispatch_time - 5:
                    return int(run["id"])
        time.sleep(3)
    raise TimeoutError("Timed out waiting for workflow run to appear.")


def poll_run(run_id: int, timeout: int = 600) -> str:
    """Block until the run finishes; return its conclusion string."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(f"{API_BASE}/actions/runs/{run_id}", headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data["status"] == "completed":
            return data.get("conclusion") or "failure"
        time.sleep(10)
    raise TimeoutError("Build timed out after 10 minutes.")


def get_artifact_urls(run_id: int) -> dict[str, str]:
    """Return {'linux': url, 'windows': url} for the run's artifacts."""
    resp = requests.get(f"{API_BASE}/actions/runs/{run_id}/artifacts", headers=HEADERS, timeout=15)
    resp.raise_for_status()
    urls: dict[str, str] = {}
    for art in resp.json().get("artifacts", []):
        name: str = art["name"]
        url: str = art["archive_download_url"]
        if "ubuntu" in name:
            urls["linux"] = url
        elif "windows" in name:
            urls["windows"] = url
    return urls


def fetch_artifact_bytes(url: str) -> bytes:
    """Download artifact ZIP content server-side using the GitHub token."""
    resp = requests.get(url, headers=HEADERS, timeout=120, allow_redirects=True)
    resp.raise_for_status()
    return resp.content


def delete_branch(branch: str) -> None:
    """Delete *branch* from the remote; silently ignore 404/422."""
    resp = requests.delete(f"{API_BASE}/git/refs/heads/{branch}", headers=HEADERS, timeout=15)
    if resp.status_code not in (204, 404, 422):
        resp.raise_for_status()


def list_python_files(data: bytes) -> list[str]:
    """Return sorted list of .py file paths found inside a ZIP."""
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        return sorted(n for n in zf.namelist() if n.endswith(".py"))


def sanitize_name(raw: str, fallback: str) -> str:
    """Strip unsafe characters from an executable name."""
    name = re.sub(r"[^\w\-]", "_", raw.strip())
    return name or fallback


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Py2Exe", page_icon=":package:", layout="centered")
st.title("Py2Exe — Python to Executable Converter")
st.caption(
    "Upload your Python project as a ZIP, configure the build options, "
    "and get a **Linux binary** + **Windows .exe** via GitHub Actions — free."
)

if not GITHUB_TOKEN:
    st.error(
        "GITHUB_TOKEN is not configured. "
        "Add it under Streamlit Community Cloud → App Settings → Secrets."
    )
    st.stop()

# --- ZIP upload ---
uploaded = st.file_uploader("Upload Python project (.zip)", type="zip")

# Reset stale downloads when a new file is uploaded
if uploaded:
    if st.session_state.get("last_zip") != uploaded.name:
        st.session_state.pop("artifacts", None)
        st.session_state["last_zip"] = uploaded.name

# --- Options (only shown after a ZIP is uploaded) ---
if uploaded:
    zip_bytes = uploaded.getvalue()
    py_files = list_python_files(zip_bytes)
    if not py_files:
        st.error("No Python files found inside the ZIP.")
        st.stop()

    st.divider()
    st.subheader("Build options")

    # Section 1 — main file
    main_file = st.selectbox("Main Python file (entry point)", py_files)

    # Section 2 — output settings
    col1, col2 = st.columns(2)
    with col1:
        exe_name_raw = st.text_input(
            "Executable name",
            value=Path(main_file).stem,
            max_chars=50,
            help="Name of the output binary. Special characters are replaced with underscores.",
        )
        exe_name = sanitize_name(exe_name_raw, Path(main_file).stem)
        if exe_name != exe_name_raw:
            st.caption(f"Will be saved as: `{exe_name}`")
    with col2:
        py_version_label = st.selectbox(
            "Python version",
            ["3.11 (default)", "3.12", "3.10", "3.9"],
        )
        python_version = py_version_label.split()[0]

    # Section 3 — PyInstaller options
    col3, col4 = st.columns(2)
    with col3:
        bundle_label = st.radio(
            "Bundle type",
            ["Single file (--onefile)", "Folder bundle (--onedir)"],
            help="Single file is easiest to distribute; folder bundle starts faster.",
        )
        bundle_type = "onefile" if "onefile" in bundle_label else "onedir"
    with col4:
        windowed = st.toggle(
            "Hide console window",
            help="Use for GUI apps (Tkinter, PyQt, etc.). Console output will not be visible.",
        )

    # Section 4 — assets (advanced)
    with st.expander("Advanced — icon & extra assets"):
        st.info(
            "Include a `requirements.txt` in your ZIP to bundle third-party libraries "
            "(e.g. numpy, requests).",
            icon="ℹ️",
        )
        icon_uploaded = st.file_uploader(
            "App icon (optional)",
            type=["ico", "png", "jpg", "jpeg"],
            help="Applied to both the Linux binary and Windows .exe.",
        )
        extra_assets = st.file_uploader(
            "Extra files to bundle (optional)",
            accept_multiple_files=True,
            help="Config files, images, fonts, etc. — bundled into the executable root.",
        )

    st.divider()
    build_clicked = st.button("Build", type="primary", use_container_width=True)
else:
    build_clicked = False
    main_file = ""
    exe_name = "output"
    python_version = "3.11"
    bundle_type = "onefile"
    windowed = False
    icon_uploaded = None
    extra_assets = []

# ---------------------------------------------------------------------------
# Build pipeline
# ---------------------------------------------------------------------------

if uploaded and build_clicked:
    # Collect files to push
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        try:
            with zipfile.ZipFile(io.BytesIO(uploaded.getvalue())) as zf:
                zf.extractall(tmp_path)
        except zipfile.BadZipFile:
            st.error("The uploaded file is not a valid ZIP archive.")
            st.stop()

        script_path = tmp_path / main_file
        if not script_path.exists():
            st.error(f"Main file **{main_file}** was not found inside the ZIP.")
            st.stop()

        # --- Code quality check ---
        with st.spinner("Checking code quality…"):
            issues = check_needs_refactoring(tmp_path)
        if issues:
            st.warning(f"**{len(issues)} flake8 issue(s) found** — proceeding anyway")
            with st.expander("View issues"):
                st.code("\n".join(issues), language="text")
        else:
            st.success("Code quality check passed")

        # --- Collect files ---
        files_to_push: dict[str, bytes] = {
            str(f.relative_to(tmp_path)): f.read_bytes() for f in tmp_path.rglob("*") if f.is_file()
        }

        # Icon
        icon_filename = ""
        if icon_uploaded:
            ext = Path(icon_uploaded.name).suffix.lower()
            icon_filename = f"_icon{ext}"
            files_to_push[icon_filename] = icon_uploaded.getvalue()

        # Extra assets
        asset_names: list[str] = []
        for asset in extra_assets or []:
            files_to_push[f"_assets/{asset.name}"] = asset.getvalue()
            asset_names.append(asset.name)
        asset_files_input = ",".join(asset_names)

        branch = f"build-{int(time.time())}"

        try:
            with st.spinner(f"Uploading {len(files_to_push)} file(s) to GitHub…"):
                create_branch(branch)
                push_files_to_branch(branch, files_to_push)

            with st.spinner("Triggering GitHub Actions build…"):
                dispatch_time = time.time()
                trigger_workflow(
                    branch,
                    main_file,
                    exe_name,
                    python_version,
                    bundle_type,
                    windowed,
                    icon_filename,
                    asset_files_input,
                )
                run_id = _find_run_id(branch, dispatch_time)

            with st.spinner("Building on ubuntu-latest + windows-latest (est. ~2 min)…"):
                conclusion = poll_run(run_id, timeout=600)

            if conclusion != "success":
                st.error("Build failed. Please check your code and try again.")
                delete_branch(branch)
                st.stop()

            with st.spinner("Fetching built binaries…"):
                artifact_urls = get_artifact_urls(run_id)
                artifacts: dict[str, bytes] = {}
                if "linux" in artifact_urls:
                    artifacts["linux"] = fetch_artifact_bytes(artifact_urls["linux"])
                if "windows" in artifact_urls:
                    artifacts["windows"] = fetch_artifact_bytes(artifact_urls["windows"])

        except Exception as exc:  # noqa: BLE001
            delete_branch(branch)
            st.error(f"Build failed: {exc}")
            st.stop()

        delete_branch(branch)

        st.session_state["artifacts"] = artifacts
        st.session_state["exe_name"] = exe_name
        st.session_state["bundle_type"] = bundle_type

# ---------------------------------------------------------------------------
# Download section (persists across reruns via session_state)
# ---------------------------------------------------------------------------

if "artifacts" in st.session_state:
    artifacts = st.session_state["artifacts"]
    _exe = st.session_state.get("exe_name", "output")
    _bundle = st.session_state.get("bundle_type", "onefile")
    suffix = "-folder" if _bundle == "onedir" else ""

    st.success("Build complete! Download your binaries below.")
    col_l, col_w = st.columns(2)
    with col_l:
        if "linux" in artifacts:
            st.download_button(
                "⬇ Download Linux binary",
                data=artifacts["linux"],
                file_name=f"{_exe}-linux{suffix}.zip",
                mime="application/zip",
                use_container_width=True,
            )
        else:
            st.warning("Linux binary not available.")
    with col_w:
        if "windows" in artifacts:
            st.download_button(
                "⬇ Download Windows .exe",
                data=artifacts["windows"],
                file_name=f"{_exe}-windows{suffix}.zip",
                mime="application/zip",
                use_container_width=True,
            )
        else:
            st.warning("Windows .exe not available.")

    st.caption("Each archive contains the built binary. Artifacts expire after **1 day**.")

    if st.button("Build another", use_container_width=True):
        st.session_state.pop("artifacts", None)
        st.session_state.pop("exe_name", None)
        st.session_state.pop("bundle_type", None)
        st.session_state.pop("last_zip", None)
        st.rerun()
