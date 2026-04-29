"""Streamlit web app for Py2Exe.

Users upload a ZIP of their Python project, specify the main file, and the app:
1. Checks for flake8 refactoring issues
2. Pushes the project to a temporary GitHub branch
3. Triggers a GitHub Actions matrix build (ubuntu + windows)
4. Returns download links for both the Linux binary and Windows .exe
5. Deletes the temporary branch when done
"""

import os
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


def trigger_workflow(branch: str, main_file: str) -> None:
    """Dispatch the build workflow on *branch*."""
    resp = requests.post(
        f"{API_BASE}/actions/workflows/build.yml/dispatches",
        headers=HEADERS,
        json={
            "ref": branch,
            "inputs": {"branch": branch, "main_file": main_file},
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
    """Block until the run finishes; return 'success' or 'failure'."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(f"{API_BASE}/actions/runs/{run_id}", headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        status = data["status"]
        conclusion = data.get("conclusion")
        if status == "completed":
            return conclusion or "failure"
        time.sleep(10)
    raise TimeoutError("Build timed out after 10 minutes.")


def get_artifact_urls(run_id: int) -> dict[str, str]:
    """Return a dict with keys 'linux' and 'windows' mapping to artifact download URLs."""
    resp = requests.get(f"{API_BASE}/actions/runs/{run_id}/artifacts", headers=HEADERS, timeout=15)
    resp.raise_for_status()
    artifacts = resp.json().get("artifacts", [])
    urls: dict[str, str] = {}
    for art in artifacts:
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
    """Delete *branch* from the remote; silently ignore 404."""
    resp = requests.delete(f"{API_BASE}/git/refs/heads/{branch}", headers=HEADERS, timeout=15)
    if resp.status_code not in (204, 404, 422):
        resp.raise_for_status()


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Py2Exe", page_icon=":package:", layout="centered")
st.title("Py2Exe — Python to Executable Converter")
st.caption(
    "Upload your Python project as a ZIP. "
    "We'll check code quality, then build a **Linux binary** and a **Windows .exe** "
    "via GitHub Actions — both free."
)
st.info(
    "**Tip:** If your project uses third-party libraries (e.g. `numpy`, `requests`), "
    "include a `requirements.txt` in your ZIP so they are bundled into the executable.",
    icon="ℹ️",
)

if not GITHUB_TOKEN:
    st.error(
        "GITHUB_TOKEN is not configured. "
        "Add it under Streamlit Community Cloud → App Settings → Secrets."
    )
    st.stop()

uploaded = st.file_uploader("Upload Python project (.zip)", type="zip")
main_file = st.text_input("Main Python file inside the ZIP", value="main.py", max_chars=200)

build_clicked = st.button("Check & Build", type="primary", disabled=not uploaded)

if uploaded and build_clicked:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # --- Extract ZIP ---
        try:
            with zipfile.ZipFile(uploaded) as zf:
                zf.extractall(tmp_path)
        except zipfile.BadZipFile:
            st.error("The uploaded file is not a valid ZIP archive.")
            st.stop()

        script_path = tmp_path / main_file
        if not script_path.exists():
            st.error(f"Main file **{main_file}** was not found inside the ZIP.")
            st.stop()

        # --- Refactoring check ---
        with st.spinner("Checking code quality..."):
            issues = check_needs_refactoring(tmp_path)

        if issues:
            st.warning(f"**{len(issues)} flake8 issue(s) found:**")
            st.code("\n".join(issues), language="text")
            ignore = st.button("Ignore issues and build anyway")
            if not ignore:
                st.info(
                    "Fix the issues above, re-upload, and try again — or click 'Ignore' to build now."
                )
                st.stop()
        else:
            st.success("No refactoring issues found.")

        # --- Collect files to upload ---
        files_to_push: dict[str, bytes] = {
            str(f.relative_to(tmp_path)): f.read_bytes() for f in tmp_path.rglob("*") if f.is_file()
        }

        branch = f"build-{int(time.time())}"

        try:
            with st.spinner("Creating temporary build branch..."):
                create_branch(branch)

            with st.spinner(f"Uploading {len(files_to_push)} file(s) to GitHub..."):
                push_files_to_branch(branch, files_to_push)

            dispatch_time = time.time()
            with st.spinner("Triggering GitHub Actions build..."):
                trigger_workflow(branch, main_file)

            with st.spinner("Waiting for build to start..."):
                run_id = _find_run_id(branch, dispatch_time)

            progress_bar = st.progress(0, text="Building on ubuntu-latest + windows-latest...")
            for pct in range(10, 91, 10):
                time.sleep(12)
                progress_bar.progress(pct, text="Building on ubuntu-latest + windows-latest...")

            with st.spinner("Waiting for build to complete..."):
                conclusion = poll_run(run_id, timeout=600)

            progress_bar.progress(100, text="Done!")

        except Exception as exc:  # noqa: BLE001
            delete_branch(branch)
            st.error(f"Build failed: {exc}")
            st.stop()

        # Always clean up the temp branch
        delete_branch(branch)

        if conclusion != "success":
            st.error(
                f"GitHub Actions build finished with status **{conclusion}**. "
                f"[View run logs](https://github.com/{GITHUB_REPO}/actions/runs/{run_id})"
            )
            st.stop()

        artifact_urls = get_artifact_urls(run_id)

        artifacts: dict[str, bytes] = {}
        with st.spinner("Fetching built binaries..."):
            if "linux" in artifact_urls:
                artifacts["linux"] = fetch_artifact_bytes(artifact_urls["linux"])
            if "windows" in artifact_urls:
                artifacts["windows"] = fetch_artifact_bytes(artifact_urls["windows"])

        st.session_state["artifacts"] = artifacts

if "artifacts" in st.session_state:
    artifacts = st.session_state["artifacts"]
    st.success("Build complete! Download your binaries below.")
    col1, col2 = st.columns(2)
    with col1:
        if "linux" in artifacts:
            st.download_button(
                "Download Linux binary",
                data=artifacts["linux"],
                file_name="linux-binary.zip",
                mime="application/zip",
            )
        else:
            st.warning("Linux binary not available.")
    with col2:
        if "windows" in artifacts:
            st.download_button(
                "Download Windows .exe",
                data=artifacts["windows"],
                file_name="windows-exe.zip",
                mime="application/zip",
            )
        else:
            st.warning("Windows .exe not available.")
    st.caption("Archives contain the built binary. Links expire after **1 day**.")
