"""Activity log panel — searchable, filterable."""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QComboBox, QAbstractItemView,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from core.database import Database


class LogPanel(QWidget):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self._db = db
        self._setup_ui()

    def _setup_ui(self) -> None:
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("Activity log")
        title.setStyleSheet("font-size:17px; font-weight:500; color:#fff;")
        hdr.addWidget(title)
        hdr.addStretch()
        self._refresh_btn = QPushButton("↻  Refresh")
        self._refresh_btn.clicked.connect(self._load)
        hdr.addWidget(self._refresh_btn)
        clear_btn = QPushButton("Clear log")
        clear_btn.setObjectName("btn_danger")
        clear_btn.clicked.connect(self._clear)
        hdr.addWidget(clear_btn)
        v.addLayout(hdr)

        # Filters
        frow = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search path or detail…")
        self._search.textChanged.connect(self._filter)
        frow.addWidget(self._search, 1)
        self._status_filter = QComboBox()
        self._status_filter.addItems(["All", "ok", "error", "warning"])
        self._status_filter.currentTextChanged.connect(self._filter)
        frow.addWidget(self._status_filter)
        self._action_filter = QComboBox()
        self._action_filter.addItems(["All actions", "move", "rename", "scan", "skip"])
        self._action_filter.currentTextChanged.connect(self._filter)
        frow.addWidget(self._action_filter)
        v.addLayout(frow)

        # Table
        self._tbl = QTableWidget(0, 5)
        self._tbl.setHorizontalHeaderLabels(
            ["Timestamp", "Action", "Path", "Detail", "Status"])
        self._tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl.setAlternatingRowColors(False)
        v.addWidget(self._tbl, 1)

        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet("color:rgba(255,255,255,0.3); font-size:11px;")
        v.addWidget(self._count_lbl)

        self._all_logs: list[dict] = []
        self._load()

    def _load(self) -> None:
        self._all_logs = self._db.get_logs(500)
        self._filter()

    def _filter(self) -> None:
        query  = self._search.text().lower()
        status = self._status_filter.currentText()
        action = self._action_filter.currentText()
        rows   = []
        for log in self._all_logs:
            if status != "All" and log["status"] != status:
                continue
            if action not in ("All actions", "") and log["action"] != action:
                continue
            if query and query not in (log.get("item_path", "") + log.get("detail", "")).lower():
                continue
            rows.append(log)

        STATUS_COLORS = {"ok": "#28c840", "error": "#ff5f57", "warning": "#febc2e"}
        self._tbl.setRowCount(0)
        for log in rows:
            r = self._tbl.rowCount()
            self._tbl.insertRow(r)
            ts = log.get("created_at", "")[:19]
            for col, val in enumerate([ts, log["action"], log["item_path"],
                                       log.get("detail", ""), log["status"]]):
                item = QTableWidgetItem(str(val))
                item.setForeground(
                    QColor(STATUS_COLORS.get(log["status"], "rgba(255,255,255,0.5)")))
                self._tbl.setItem(r, col, item)

        self._count_lbl.setText(f"{len(rows)} entries")

    def _clear(self) -> None:
        self._db._c().execute("DELETE FROM activity_log")
        self._db._conn.commit()
        self._all_logs = []
        self._tbl.setRowCount(0)
        self._count_lbl.setText("0 entries")

    def on_shown(self) -> None:
        self._load()
