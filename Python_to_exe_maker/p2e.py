"""CLI entry point — thin wrapper over builder.py."""

import logging
import sys
from pathlib import Path

from Python_to_exe_maker.builder import (
    build_exe,
    check_needs_refactoring,
    ensure_pyinstaller,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def main() -> None:
    ensure_pyinstaller()

    raw = input("Python script (with location): ").strip()
    script_path = Path(raw).resolve()

    issues = check_needs_refactoring(script_path.parent)
    if issues:
        log.warning("Refactoring issues found:\n%s", "\n".join(issues))
        answer = input("Proceed anyway? [y/N]: ").strip().lower()
        if answer != "y":
            sys.exit(0)

    try:
        binary = build_exe(script_path, script_path.parent)
        log.info("Done! Binary saved to: %s", binary)
    except (FileNotFoundError, ValueError) as exc:
        log.error("%s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
