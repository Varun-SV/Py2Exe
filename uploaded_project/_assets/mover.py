"""
File/folder moving — same-drive (os.rename, instant) vs
cross-drive (shutil.move, copies bytes).
"""
from __future__ import annotations
import os, shutil, logging
from pathlib import Path
from core.utils import sanitize_windows_name
from core.database import Database

log = logging.getLogger(__name__)


class Mover:
    def __init__(self, db: Database) -> None:
        self._db = db

    @staticmethod
    def is_same_drive(src: Path, dst: Path) -> bool:
        return src.drive.lower() == dst.drive.lower()

    def compute_destination(self, item_path: str, category_name: str,
                            destinations: list[dict],
                            categories: list[dict]) -> Path | None:
        """
        Find the destination folder for an item.
        Picks the destination root on the same drive as item if available,
        otherwise the first configured destination.
        """
        item = Path(item_path)
        item_drive = item.drive.lower()

        # Find category subpath
        subpath = ""
        for cat in categories:
            if cat["name"] == category_name:
                subpath = cat.get("dest_subpath", "") or category_name
                break

        # Prefer same-drive destination
        same_drive = [d for d in destinations if d["drive"].lower() == item_drive]
        dest_roots = same_drive or destinations
        if not dest_roots:
            return None

        root = Path(dest_roots[0]["path"])
        return root / subpath

    def move(self, src: Path, dst_dir: Path,
             new_name: str | None = None,
             progress_cb=None) -> bool:
        """
        Move src into dst_dir, optionally renaming to new_name.
        Returns True on success.
        """
        name    = sanitize_windows_name(new_name or src.name)
        dst     = dst_dir / name

        if not src.exists():
            log.warning("Source not found: %s", src)
            return False
        if dst.exists():
            log.warning("Destination exists, skipping: %s", dst)
            return False

        try:
            dst_dir.mkdir(parents=True, exist_ok=True)
            if self.is_same_drive(src, dst):
                os.rename(src, dst)
            else:
                if progress_cb:
                    progress_cb(f"Copying {src.name}…")
                shutil.move(str(src), str(dst))

            self._db.add_log("move", str(src),
                             f"→ {dst}", "ok")
            return True
        except Exception as exc:
            log.error("Move failed %s → %s: %s", src, dst, exc)
            self._db.add_log("move", str(src), str(exc), "error")
            return False
