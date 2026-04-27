"""Core build logic for Py2Exe — importable by CLI and Streamlit app."""

import importlib.util
import logging
import shutil
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)

HOOK_CONTENT = (
    "from PyInstaller.utils.hooks import collect_submodules\n"
    "hiddenimports = collect_submodules('IPython.lib.inputhook')\n"
)


def get_output_extension() -> str:
    """Return the binary extension for the current platform."""
    return ".exe" if sys.platform == "win32" else ""


def ensure_pyinstaller() -> None:
    """Install PyInstaller if it is not already present."""
    if importlib.util.find_spec("PyInstaller") is None:
        log.info("PyInstaller not found — installing...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pyinstaller"],
            check=True,
        )


def check_needs_refactoring(project_dir: Path) -> list[str]:
    """Run flake8 on *project_dir* and return a list of violation strings.

    An empty list means the code is clean.
    """
    result = subprocess.run(
        [sys.executable, "-m", "flake8", str(project_dir)],
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def build_exe(script_path: Path, output_dir: Path) -> Path:
    """Build a single-file binary for the current platform.

    Args:
        script_path: Absolute path to the Python script to compile.
        output_dir:  Directory where the final binary will be placed.

    Returns:
        Path to the produced binary.

    Raises:
        FileNotFoundError: If *script_path* does not exist.
        ValueError: If *script_path* is not a .py file.
        subprocess.CalledProcessError: If PyInstaller fails.
    """
    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")
    if script_path.suffix != ".py":
        raise ValueError(f"Expected a .py file, got: {script_path}")

    hook_file = output_dir / "hook-inputhook.py"
    hook_file.write_text(HOOK_CONTENT, encoding="utf-8")

    dist_dir = output_dir / "dist"
    build_dir = output_dir / "build"

    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "PyInstaller",
                "--onefile",
                f"--additional-hooks-dir={output_dir}",
                "--distpath",
                str(dist_dir),
                "--workpath",
                str(build_dir),
                str(script_path),
            ],
            cwd=output_dir,
            check=True,
        )

        ext = get_output_extension()
        built = dist_dir / (script_path.stem + ext)
        dest = output_dir / (script_path.stem + ext)
        built.replace(dest)
        log.info("Binary written to: %s", dest)
        return dest

    finally:
        hook_file.unlink(missing_ok=True)
        spec_file = output_dir / (script_path.stem + ".spec")
        spec_file.unlink(missing_ok=True)
        for artifact in (build_dir, dist_dir):
            if artifact.exists():
                shutil.rmtree(artifact)
