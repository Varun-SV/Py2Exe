"""QThread that moves items and emits progress signals."""
from __future__ import annotations
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
from core.mover import Mover
from core.database import Database


class MoveWorker(QThread):
    progress   = pyqtSignal(int, int, str)  # current, total, path
    item_done  = pyqtSignal(str, bool)      # path, success
    complete   = pyqtSignal(int, int)       # moved, failed
    error      = pyqtSignal(str)

    def __init__(self, db: Database,
                 items: list[dict],
                 destinations: list[dict],
                 categories: list[dict],
                 rename_map: dict[str, str]) -> None:
        """
        items       : list of scan_item dicts with 'path', 'detected_category'
        rename_map  : {original_name: chosen_name} from DB choices
        """
        super().__init__()
        self._db           = db
        self._items        = items
        self._destinations = destinations
        self._categories   = categories
        self._rename_map   = rename_map
        self._abort        = False

    def stop(self) -> None:
        self._abort = True

    def run(self) -> None:
        mover  = Mover(self._db)
        moved  = 0
        failed = 0
        total  = len(self._items)

        for idx, item in enumerate(self._items):
            if self._abort:
                break

            src      = Path(item["path"])
            category = item["detected_category"]
            new_name = self._rename_map.get(src.name) or src.name

            self.progress.emit(idx + 1, total, str(src))

            dst_dir = mover.compute_destination(
                str(src), category, self._destinations, self._categories)

            if dst_dir is None:
                self._db.add_log("move", str(src), "No destination configured", "error")
                failed += 1
                self.item_done.emit(str(src), False)
                continue

            ok = mover.move(src, dst_dir, new_name)
            if ok:
                moved += 1
                self._db.update_scan_item_status(item["id"], "moved")
            else:
                failed += 1
                self._db.update_scan_item_status(item["id"], "error")
            self.item_done.emit(str(src), ok)

        self.complete.emit(moved, failed)
