"""Scan panel — manage scans, show progress, surface category suggestions."""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QProgressBar, QFrame,
    QDialog, QTableWidget, QTableWidgetItem, QComboBox,
    QHeaderView, QAbstractItemView,
)
from PyQt6.QtCore import Qt, pyqtSignal
from core.config import Config
from core.database import Database
from workers.scan_worker import ScanWorker


class ScanPanel(QWidget):
    scan_complete = pyqtSignal()

    def __init__(self, db: Database, config: Config, parent=None):
        super().__init__(parent)
        self._db      = db
        self._config  = config
        self._worker: ScanWorker | None = None
        self._suggestions: list[dict] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(14)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("Scan")
        title.setStyleSheet("font-size:17px; font-weight:500; color:#fff;")
        hdr.addWidget(title)
        hdr.addStretch()
        self._deep_btn = QPushButton("Deep scan  (+ API lookups)")
        self._deep_btn.clicked.connect(lambda: self._start_scan(deep=True))
        hdr.addWidget(self._deep_btn)
        self._scan_btn = QPushButton("Scan now")
        self._scan_btn.setObjectName("btn_accent")
        self._scan_btn.clicked.connect(lambda: self._start_scan(deep=False))
        hdr.addWidget(self._scan_btn)
        v.addLayout(hdr)

        # Progress
        self._prog_lbl = QLabel("")
        self._prog_lbl.setStyleSheet("color:rgba(255,255,255,0.4); font-size:11px;")
        v.addWidget(self._prog_lbl)
        self._prog_bar = QProgressBar()
        self._prog_bar.setFixedHeight(4)
        self._prog_bar.setVisible(False)
        v.addWidget(self._prog_bar)

        # Source folder status list
        src_card = QFrame()
        src_card.setObjectName("card")
        sv = QVBoxLayout(src_card)
        sv.setContentsMargins(14, 12, 14, 12)
        sv.addWidget(self._section_lbl("SOURCE FOLDERS"))
        self._src_list = QListWidget()
        self._src_list.setAlternatingRowColors(False)
        sv.addWidget(self._src_list)
        v.addWidget(src_card)

        # Recent scan results
        res_card = QFrame()
        res_card.setObjectName("card")
        rv = QVBoxLayout(res_card)
        rv.setContentsMargins(14, 12, 14, 12)
        row = QHBoxLayout()
        row.addWidget(self._section_lbl("LAST SCAN RESULTS"))
        row.addStretch()
        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet("color:rgba(255,255,255,0.3); font-size:11px;")
        row.addWidget(self._count_lbl)
        rv.addLayout(row)
        self._result_list = QListWidget()
        rv.addWidget(self._result_list, 1)
        v.addWidget(res_card, 1)

        self._refresh_sources()

    def _section_lbl(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet("color:rgba(255,255,255,0.28); font-size:10px; letter-spacing:0.06em; margin-bottom:4px;")
        return l

    def _refresh_sources(self) -> None:
        self._src_list.clear()
        for sf in self._db.get_source_folders():
            tag  = f"  [{sf['tag']}]" if sf["tag"] else ""
            item = QListWidgetItem(f"  {sf['path']}{tag}")
            self._src_list.addItem(item)

    def _start_scan(self, deep: bool = False) -> None:
        if self._worker and self._worker.isRunning():
            return
        self._db.clear_scan_items()
        self._result_list.clear()
        self._prog_bar.setVisible(True)
        self._prog_bar.setRange(0, 0)
        self._scan_btn.setEnabled(False)
        self._deep_btn.setEnabled(False)
        self._suggestions = []

        cats = self._db.get_categories()
        sfs  = self._db.get_source_folders()

        self._worker = ScanWorker(self._db, sfs, cats, pre_scan_only=False)
        self._worker.progress.connect(self._on_progress)
        self._worker.item_found.connect(self._on_item_found)
        self._worker.suggestions.connect(self._on_suggestions)
        self._worker.complete.connect(self._on_complete)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, msg: str) -> None:
        self._prog_lbl.setText(msg)

    def _on_item_found(self, item: dict) -> None:
        cat  = item["category"] or "unclassified"
        name = item["name"]
        li   = QListWidgetItem(f"  {cat}  ·  {name}")
        li.setForeground(
            __import__("PyQt6.QtGui", fromlist=["QColor"]).QColor("rgba(255,255,255,0.55)"))
        self._result_list.addItem(li)
        n = self._result_list.count()
        self._count_lbl.setText(f"{n} item(s)")

    def _on_suggestions(self, sug: list) -> None:
        self._suggestions.extend(sug)
        if self._suggestions:
            self._show_category_dialog()

    def _on_complete(self, total: int) -> None:
        self._prog_bar.setVisible(False)
        self._prog_bar.setRange(0, 1)
        self._scan_btn.setEnabled(True)
        self._deep_btn.setEnabled(True)
        self._prog_lbl.setText(f"Scan complete — {total} item(s) found.")
        self._db.add_log("scan", "all", f"{total} items", "ok")
        self.scan_complete.emit()

    def _on_error(self, msg: str) -> None:
        self._prog_lbl.setText(f"Error: {msg}")

    def _show_category_dialog(self) -> None:
        dlg = CategorySuggestionDialog(self._suggestions, self._db, self)
        dlg.exec()
        self._suggestions = []

    def on_shown(self) -> None:
        self._refresh_sources()


class CategorySuggestionDialog(QDialog):
    def __init__(self, suggestions: list[dict], db: Database, parent=None):
        super().__init__(parent)
        self._db  = db
        self._sug = suggestions
        self.setWindowTitle("Detected categories — review & confirm")
        self.setMinimumSize(560, 380)
        self._setup_ui()

    def _setup_ui(self) -> None:
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(10)
        lbl = QLabel("The following categories were detected. Review and confirm which to add.")
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color:rgba(255,255,255,0.5); font-size:12px;")
        v.addWidget(lbl)

        self._tbl = QTableWidget(0, 4)
        self._tbl.setHorizontalHeaderLabels(["Folder", "Media type", "API", "Destination subfolder"])
        self._tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        v.addWidget(self._tbl, 1)

        for sug in self._sug:
            r = self._tbl.rowCount()
            self._tbl.insertRow(r)
            self._tbl.setItem(r, 0, QTableWidgetItem(sug["name"]))
            mt = QComboBox()
            for t in ("movie", "series", "anime", "anime_film"):
                mt.addItem(t)
            mt.setCurrentText(sug.get("media_type", "movie"))
            self._tbl.setCellWidget(r, 1, mt)
            ap = QComboBox()
            for a in ("tmdb", "anilist", "anidb", "both"):
                ap.addItem(a)
            ap.setCurrentText(sug.get("api_pref", "tmdb"))
            self._tbl.setCellWidget(r, 2, ap)
            self._tbl.setItem(r, 3, QTableWidgetItem(sug["name"]))

        row = QHBoxLayout()
        skip = QPushButton("Skip all")
        skip.clicked.connect(self.reject)
        row.addWidget(skip)
        row.addStretch()
        ok = QPushButton("Add selected")
        ok.setObjectName("btn_accent")
        ok.clicked.connect(self._save)
        row.addWidget(ok)
        v.addLayout(row)

    def _save(self) -> None:
        for r in range(self._tbl.rowCount()):
            name = (self._tbl.item(r, 0) or QTableWidgetItem()).text().strip()
            if not name:
                continue
            mtype = self._tbl.cellWidget(r, 1).currentText()
            api   = self._tbl.cellWidget(r, 2).currentText()
            dest  = (self._tbl.item(r, 3) or QTableWidgetItem()).text().strip()
            self._db.add_category(name, mtype, api, dest)
        self.accept()
