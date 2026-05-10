"""Dashboard panel — stats, drive usage, sources, categories, activity."""
from __future__ import annotations
import shutil
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QGridLayout, QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal
from core.config import Config
from core.database import Database
from core.utils import format_bytes


class StatCard(QFrame):
    def __init__(self, label: str, value: str, color: str = "#fff", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 12, 14, 12)
        self._lbl = QLabel(label)
        self._lbl.setStyleSheet("color:rgba(255,255,255,0.35); font-size:10px; letter-spacing:0.05em;")
        v.addWidget(self._lbl)
        self._val = QLabel(value)
        self._val.setStyleSheet(f"color:{color}; font-size:22px; font-weight:500;")
        v.addWidget(self._val)

    def update_value(self, value: str) -> None:
        self._val.setText(value)


class DriveBar(QWidget):
    def __init__(self, drive: str, path: str, parent=None):
        super().__init__(parent)
        self._path = path
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 2, 0, 2)
        self._name = QLabel(f"{drive}  {path}")
        self._name.setStyleSheet("color:rgba(255,255,255,0.5); font-size:11px;")
        self._name.setFixedWidth(240)
        h.addWidget(self._name)
        from PyQt6.QtWidgets import QProgressBar
        self._bar = QProgressBar()
        self._bar.setFixedHeight(4)
        self._bar.setTextVisible(False)
        h.addWidget(self._bar, 1)
        self._pct = QLabel()
        self._pct.setFixedWidth(70)
        self._pct.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._pct.setStyleSheet("color:rgba(255,255,255,0.3); font-size:10px;")
        h.addWidget(self._pct)
        self.refresh()

    def refresh(self) -> None:
        try:
            usage = shutil.disk_usage(self._path)
            pct   = int((usage.used / usage.total) * 100)
            self._bar.setMaximum(100)
            self._bar.setValue(pct)
            color = "#ff5f57" if pct > 95 else "#febc2e" if pct > 80 else "#28c840"
            self._bar.setStyleSheet(
                f"QProgressBar::chunk{{background:{color};border-radius:2px;}}"
                "QProgressBar{background:rgba(255,255,255,0.07);border:none;border-radius:2px;}")
            self._pct.setText(f"{format_bytes(usage.free)} free")
        except Exception:
            self._bar.setValue(0)
            self._pct.setText("—")


class DashboardPanel(QWidget):
    def __init__(self, db: Database, config: Config, parent=None):
        super().__init__(parent)
        self._db     = db
        self._config = config
        self._setup_ui()

    def _setup_ui(self) -> None:
        # Outer scroll
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        v = QVBoxLayout(content)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(16)

        # Header row
        hdr = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setStyleSheet("font-size:17px; font-weight:500; color:#fff;")
        hdr.addWidget(title)
        hdr.addStretch()
        self._refresh_btn = QPushButton("↻  Refresh")
        self._refresh_btn.clicked.connect(self.refresh)
        hdr.addWidget(self._refresh_btn)
        v.addLayout(hdr)

        # Stat cards
        grid = QGridLayout()
        grid.setSpacing(10)
        self._stat_total   = StatCard("Total items",  "—")
        self._stat_pending = StatCard("Pending",       "—", "#febc2e")
        self._stat_moved   = StatCard("Organised",     "—", "#28c840")
        self._stat_issues  = StatCard("Issues",        "—", "#ff5f57")
        for col, card in enumerate([self._stat_total, self._stat_pending,
                                     self._stat_moved, self._stat_issues]):
            grid.addWidget(card, 0, col)
        v.addLayout(grid)

        # Bottom split: left (drives + sources) | right (categories + activity)
        split = QHBoxLayout()
        split.setSpacing(14)
        split.addWidget(self._build_left(), 1)
        split.addWidget(self._build_right(), 1)
        v.addLayout(split)
        v.addStretch()

        self.refresh()

    def _build_left(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)

        # Drives
        drives_card = QFrame()
        drives_card.setObjectName("card")
        dv = QVBoxLayout(drives_card)
        dv.setContentsMargins(14, 12, 14, 12)
        dv.addWidget(self._section_label("DRIVES"))
        self._drives_layout = QVBoxLayout()
        self._drives_layout.setSpacing(6)
        dv.addLayout(self._drives_layout)
        v.addWidget(drives_card)

        # Source folders
        src_card = QFrame()
        src_card.setObjectName("card")
        sv = QVBoxLayout(src_card)
        sv.setContentsMargins(14, 12, 14, 12)
        sv.addWidget(self._section_label("SOURCE FOLDERS"))
        self._src_list = QListWidget()
        self._src_list.setMaximumHeight(140)
        sv.addWidget(self._src_list)
        v.addWidget(src_card)
        return w

    def _build_right(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)

        # Categories
        cat_card = QFrame()
        cat_card.setObjectName("card")
        cv = QVBoxLayout(cat_card)
        cv.setContentsMargins(14, 12, 14, 12)
        cv.addWidget(self._section_label("CATEGORIES"))
        self._cat_list = QListWidget()
        self._cat_list.setMaximumHeight(130)
        cv.addWidget(self._cat_list)
        v.addWidget(cat_card)

        # Activity
        act_card = QFrame()
        act_card.setObjectName("card")
        av = QVBoxLayout(act_card)
        av.setContentsMargins(14, 12, 14, 12)
        av.addWidget(self._section_label("RECENT ACTIVITY"))
        self._act_list = QListWidget()
        self._act_list.setMaximumHeight(150)
        av.addWidget(self._act_list)
        v.addWidget(act_card)
        return w

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color:rgba(255,255,255,0.28); font-size:10px; "
                          "letter-spacing:0.06em; margin-bottom:6px;")
        return lbl

    # ── Data refresh ───────────────────────────────────────────────────
    def refresh(self) -> None:
        stats = self._db.get_stats()
        self._stat_total.update_value(str(stats["total"]))
        self._stat_pending.update_value(str(stats["pending"]))
        self._stat_moved.update_value(str(stats["moved"]))
        self._stat_issues.update_value(str(stats["errors"]))
        self._refresh_drives()
        self._refresh_sources()
        self._refresh_categories()
        self._refresh_activity()

    def _refresh_drives(self) -> None:
        while self._drives_layout.count():
            item = self._drives_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        dsts = self._db.get_destinations()
        for dst in dsts:
            bar = DriveBar(dst["drive"], dst["path"])
            self._drives_layout.addWidget(bar)
        if not dsts:
            self._drives_layout.addWidget(
                QLabel("No destinations configured"))

    def _refresh_sources(self) -> None:
        self._src_list.clear()
        for sf in self._db.get_source_folders():
            tag  = f"[{sf['tag']}]  " if sf["tag"] else ""
            item = QListWidgetItem(f"  {tag}{sf['path']}")
            self._src_list.addItem(item)

    def _refresh_categories(self) -> None:
        self._cat_list.clear()
        cats  = self._db.get_categories()
        items = self._db.get_scan_items()
        counts: dict[str, int] = {}
        for it in items:
            counts[it["detected_category"]] = counts.get(it["detected_category"], 0) + 1
        for cat in cats:
            n    = counts.get(cat["name"], 0)
            item = QListWidgetItem(f"  {cat['name']}   {n}")
            self._cat_list.addItem(item)

    def _refresh_activity(self) -> None:
        self._act_list.clear()
        logs = self._db.get_logs(20)
        icons = {"ok": "✓", "error": "✗", "warning": "⚠"}
        colors = {"ok": "#28c840", "error": "#ff5f57", "warning": "#febc2e"}
        for entry in logs:
            icon  = icons.get(entry["status"], "·")
            color = colors.get(entry["status"], "rgba(255,255,255,0.3)")
            item  = QListWidgetItem(f"  {icon}  {entry['action']}  {entry['item_path'][:48]}")
            item.setForeground(
                __import__("PyQt6.QtGui", fromlist=["QColor"]).QColor(color))
            self._act_list.addItem(item)

    def on_shown(self) -> None:
        self.refresh()
