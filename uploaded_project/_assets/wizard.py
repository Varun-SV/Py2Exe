"""
Orion setup wizard — shown on first launch.
5 steps: Welcome → Sources (+ pre-scan) → Categories → Destinations → API Keys → Done
"""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QFileDialog, QStackedWidget, QFrame, QComboBox, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from core.config import Config
from core.database import Database
from workers.scan_worker import ScanWorker


STEPS = ["Welcome", "Sources", "Categories", "Destinations", "API Keys", "Done"]


class WizardPage(QWidget):
    """Base class for wizard pages."""
    next_enabled = pyqtSignal(bool)


class StepIndicator(QWidget):
    def __init__(self, steps: list[str], parent=None):
        super().__init__(parent)
        self._steps   = steps
        self._current = 0
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._dots: list[QLabel] = []
        for i, name in enumerate(steps):
            if i:
                sep = QLabel("────")
                sep.setStyleSheet("color: rgba(255,255,255,0.1); font-size:10px;")
                h.addWidget(sep)
            dot = QLabel()
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dot.setFixedSize(QSize(26, 26))
            self._dots.append(dot)
            h.addWidget(dot)
        self._refresh()

    def set_step(self, idx: int) -> None:
        self._current = idx
        self._refresh()

    def _refresh(self) -> None:
        for i, dot in enumerate(self._dots):
            if i < self._current:
                dot.setText("✓")
                dot.setStyleSheet(
                    "background:rgba(0,164,220,0.25);color:#00a4dc;"
                    "border-radius:13px;font-size:12px;")
            elif i == self._current:
                dot.setText(str(i + 1))
                dot.setStyleSheet(
                    "background:#00a4dc;color:#fff;"
                    "border-radius:13px;font-size:11px;font-weight:500;")
            else:
                dot.setText(str(i + 1))
                dot.setStyleSheet(
                    "background:rgba(255,255,255,0.08);color:rgba(255,255,255,0.3);"
                    "border-radius:13px;font-size:11px;")


class SetupWizard(QDialog):
    def __init__(self, db: Database, config: Config, parent=None):
        super().__init__(parent)
        self._db      = db
        self._config  = config
        self._worker: ScanWorker | None = None
        self._suggestions: list[dict] = []
        self._step = 0
        self.setWindowTitle("Orion — First Launch Setup")
        self.setMinimumSize(620, 520)
        self.setModal(True)
        self._setup_ui()

    # ── UI ────────────────────────────────────────────────────────────
    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header bar
        hdr = QFrame()
        hdr.setStyleSheet("background:#0d0d0d; border-bottom:1px solid rgba(255,255,255,0.07);")
        hdr.setFixedHeight(56)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(20, 0, 20, 0)
        logo = QLabel("✦ ORION")
        logo.setStyleSheet("color:#00a4dc; font-size:13px; font-weight:500; letter-spacing:3px;")
        hl.addWidget(logo)
        hl.addStretch()
        self._step_lbl = QLabel("Step 1 of 6")
        self._step_lbl.setStyleSheet("color:rgba(255,255,255,0.3); font-size:11px;")
        hl.addWidget(self._step_lbl)
        root.addWidget(hdr)

        # Indicator
        ind_wrap = QWidget()
        ind_wrap.setStyleSheet("background: #111;")
        ind_lay = QHBoxLayout(ind_wrap)
        ind_lay.setContentsMargins(20, 14, 20, 14)
        self._indicator = StepIndicator(STEPS)
        ind_lay.addWidget(self._indicator)
        root.addWidget(ind_wrap)

        # Pages
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: #151515;")
        self._pages = [
            self._page_welcome(),
            self._page_sources(),
            self._page_categories(),
            self._page_destinations(),
            self._page_api_keys(),
            self._page_done(),
        ]
        for p in self._pages:
            self._stack.addWidget(p)
        root.addWidget(self._stack, 1)

        # Footer
        footer = QFrame()
        footer.setStyleSheet("background:#0d0d0d; border-top:1px solid rgba(255,255,255,0.07);")
        footer.setFixedHeight(56)
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(20, 0, 20, 0)
        self._btn_back = QPushButton("← Back")
        self._btn_back.setVisible(False)
        self._btn_back.clicked.connect(self._go_back)
        fl.addWidget(self._btn_back)
        fl.addStretch()
        self._btn_next = QPushButton("Get Started →")
        self._btn_next.setObjectName("btn_accent")
        self._btn_next.setFixedWidth(140)
        self._btn_next.clicked.connect(self._go_next)
        fl.addWidget(self._btn_next)
        root.addWidget(footer)

    # ── Pages ─────────────────────────────────────────────────────────
    def _page_welcome(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.setSpacing(12)
        icon = QLabel("✦")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size:48px; color:#00a4dc; margin-bottom:8px;")
        v.addWidget(icon)
        title = QLabel("Welcome to Orion")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:22px; font-weight:500; color:#fff;")
        v.addWidget(title)
        sub = QLabel("Your Jellyfin media library organizer. Scan, rename, and organise your collection in a few steps.")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color:rgba(255,255,255,0.45); font-size:13px; line-height:1.6;")
        sub.setWordWrap(True)
        v.addWidget(sub)
        return w

    def _page_sources(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(28, 24, 28, 24)
        v.setSpacing(12)
        v.addWidget(self._heading("Add source folders",
            "Add every folder that contains media you want to organise."))
        self._src_list = QListWidget()
        self._src_list.setAlternatingRowColors(False)
        v.addWidget(self._src_list, 1)
        row = QHBoxLayout()
        self._src_tag = QLineEdit()
        self._src_tag.setPlaceholderText("Tag (optional, e.g. NAS, HDD)")
        self._src_tag.setFixedWidth(180)
        row.addWidget(self._src_tag)
        row.addStretch()
        add_btn = QPushButton("+ Browse & add")
        add_btn.setObjectName("btn_accent")
        add_btn.clicked.connect(self._add_source)
        row.addWidget(add_btn)
        del_btn = QPushButton("Remove selected")
        del_btn.setObjectName("btn_danger")
        del_btn.clicked.connect(self._del_source)
        row.addWidget(del_btn)
        v.addLayout(row)
        self._scan_status = QLabel("")
        self._scan_status.setStyleSheet("color:rgba(255,255,255,0.3); font-size:11px;")
        v.addWidget(self._scan_status)
        return w

    def _page_categories(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(28, 24, 28, 24)
        v.setSpacing(12)
        v.addWidget(self._heading("Review detected categories",
            "Categories were identified from your folder structure. Edit names, types and API preferences."))
        self._cat_table = QTableWidget(0, 4)
        self._cat_table.setHorizontalHeaderLabels(["Folder name", "Media type", "API", "Destination subfolder"])
        self._cat_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._cat_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._cat_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._cat_table.setAlternatingRowColors(False)
        v.addWidget(self._cat_table, 1)
        row = QHBoxLayout()
        add_cat = QPushButton("+ Add manually")
        add_cat.clicked.connect(self._add_category_row)
        row.addWidget(add_cat)
        del_cat = QPushButton("Remove row")
        del_cat.setObjectName("btn_danger")
        del_cat.clicked.connect(self._del_category_row)
        row.addWidget(del_cat)
        row.addStretch()
        v.addLayout(row)
        return w

    def _page_destinations(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(28, 24, 28, 24)
        v.setSpacing(12)
        v.addWidget(self._heading("Set destination roots",
            "Choose where organised media lands on each drive."))
        self._dst_list = QListWidget()
        v.addWidget(self._dst_list, 1)
        row = QHBoxLayout()
        add_dst = QPushButton("+ Add destination")
        add_dst.setObjectName("btn_accent")
        add_dst.clicked.connect(self._add_destination)
        row.addWidget(add_dst)
        del_dst = QPushButton("Remove selected")
        del_dst.setObjectName("btn_danger")
        del_dst.clicked.connect(self._del_destination)
        row.addWidget(del_dst)
        row.addStretch()
        v.addLayout(row)
        return w

    def _page_api_keys(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(28, 24, 28, 24)
        v.setSpacing(16)
        v.addWidget(self._heading("API keys",
            "Optional but recommended — enables poster thumbnails and accurate renaming. Keys are session-only and never saved to disk."))

        warn = QLabel("⚠  Keys cleared when app closes. You will need to re-enter them each launch.")
        warn.setWordWrap(True)
        warn.setStyleSheet("background:rgba(254,188,46,0.08);border:1px solid rgba(254,188,46,0.2);"
                           "border-radius:6px;padding:8px 12px;color:#febc2e;font-size:12px;")
        v.addWidget(warn)

        # TMDb
        tmdb_card = self._api_card("TMDb API Key",
            "Free at themoviedb.org/settings/api — used for movie, TV and poster lookups.",
            "tmdb")
        v.addWidget(tmdb_card)

        # AniDB
        anidb_card = self._api_card("AniDB Client ID",
            "Register a client at anidb.net/software/add — used for anime episode titles.",
            "anidb_client")
        v.addWidget(anidb_card)

        note = QLabel("AniList is always active — no key required.")
        note.setStyleSheet("color:rgba(255,255,255,0.3); font-size:11px;")
        v.addWidget(note)
        v.addStretch()
        return w

    def _page_done(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.setSpacing(12)
        check = QLabel("✓")
        check.setAlignment(Qt.AlignmentFlag.AlignCenter)
        check.setStyleSheet("font-size:48px; color:#28c840; margin-bottom:8px;")
        v.addWidget(check)
        title = QLabel("All set!")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:22px; font-weight:500; color:#fff;")
        v.addWidget(title)
        self._summary_lbl = QLabel()
        self._summary_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._summary_lbl.setStyleSheet("color:rgba(255,255,255,0.4); font-size:12px; line-height:1.7;")
        self._summary_lbl.setWordWrap(True)
        v.addWidget(self._summary_lbl)
        return w

    # ── Helpers ───────────────────────────────────────────────────────
    def _heading(self, title: str, sub: str) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(3)
        t = QLabel(title)
        t.setStyleSheet("font-size:15px; font-weight:500; color:#fff;")
        v.addWidget(t)
        s = QLabel(sub)
        s.setStyleSheet("color:rgba(255,255,255,0.4); font-size:12px;")
        s.setWordWrap(True)
        v.addWidget(s)
        return w

    def _api_card(self, title: str, hint: str, key: str) -> QWidget:
        card = QFrame()
        card.setStyleSheet("background:#1e1e1e; border:1px solid rgba(255,255,255,0.07); border-radius:8px;")
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(6)
        t = QLabel(title)
        t.setStyleSheet("color:#fff; font-size:12px; font-weight:500;")
        v.addWidget(t)
        h = QLabel(hint)
        h.setStyleSheet("color:rgba(255,255,255,0.3); font-size:11px;")
        h.setWordWrap(True)
        v.addWidget(h)
        row = QHBoxLayout()
        field = QLineEdit()
        field.setEchoMode(QLineEdit.EchoMode.Password)
        field.setPlaceholderText("Paste key here…")
        field.textChanged.connect(lambda t, k=key: self._config.set_api_key(k, t))
        row.addWidget(field, 1)
        show = QPushButton("Show")
        show.setFixedWidth(60)
        show.clicked.connect(lambda _, f=field: f.setEchoMode(
            QLineEdit.EchoMode.Normal if f.echoMode() == QLineEdit.EchoMode.Password
            else QLineEdit.EchoMode.Password))
        row.addWidget(show)
        v.addLayout(row)
        return card

    # ── Source management ─────────────────────────────────────────────
    def _add_source(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select source folder")
        if not path:
            return
        tag = self._src_tag.text().strip()
        fid = self._db.add_source_folder(path, tag)
        item = QListWidgetItem(f"{'[' + tag + ']  ' if tag else ''}{path}")
        item.setData(Qt.ItemDataRole.UserRole, fid)
        self._src_list.addItem(item)
        # Pre-scan for category suggestions
        self._run_prescan(path)

    def _del_source(self) -> None:
        for item in self._src_list.selectedItems():
            fid = item.data(Qt.ItemDataRole.UserRole)
            if fid:
                self._db.delete_source_folder(fid)
            self._src_list.takeItem(self._src_list.row(item))

    def _run_prescan(self, path: str) -> None:
        self._scan_status.setText("Scanning for categories…")
        from pathlib import Path
        cats = self._db.get_categories()
        sf   = self._db.get_source_folders()
        self._worker = ScanWorker(self._db, sf, cats, pre_scan_only=True)
        self._worker.suggestions.connect(self._on_suggestions)
        self._worker.complete.connect(lambda _: self._scan_status.setText("Scan complete."))
        self._worker.start()

    def _on_suggestions(self, suggestions: list) -> None:
        for sug in suggestions:
            self._suggestions.append(sug)
        self._scan_status.setText(f"Found {len(self._suggestions)} category/categories.")

    # ── Category management ───────────────────────────────────────────
    def _populate_category_table(self) -> None:
        self._cat_table.setRowCount(0)
        for sug in self._suggestions:
            self._add_category_row_data(
                sug["name"], sug.get("media_type", "movie"),
                sug.get("api_pref", "tmdb"), sug["name"])

    def _add_category_row(self) -> None:
        self._add_category_row_data("", "movie", "tmdb", "")

    def _add_category_row_data(self, name: str, mtype: str,
                                api: str, dest: str) -> None:
        r = self._cat_table.rowCount()
        self._cat_table.insertRow(r)
        self._cat_table.setItem(r, 0, QTableWidgetItem(name))

        mtype_cb = QComboBox()
        for t in ("movie", "series", "anime", "anime_film"):
            mtype_cb.addItem(t)
        mtype_cb.setCurrentText(mtype)
        self._cat_table.setCellWidget(r, 1, mtype_cb)

        api_cb = QComboBox()
        for a in ("tmdb", "anilist", "anidb", "both"):
            api_cb.addItem(a)
        api_cb.setCurrentText(api)
        self._cat_table.setCellWidget(r, 2, api_cb)

        self._cat_table.setItem(r, 3, QTableWidgetItem(dest or name))

    def _del_category_row(self) -> None:
        for idx in sorted(set(i.row() for i in self._cat_table.selectedItems()), reverse=True):
            self._cat_table.removeRow(idx)

    # ── Destination management ────────────────────────────────────────
    def _add_destination(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select destination root")
        if not path:
            return
        from pathlib import Path
        drive = Path(path).drive
        self._db.upsert_destination(drive, path)
        item = QListWidgetItem(f"{drive}  →  {path}")
        self._dst_list.addItem(item)

    def _del_destination(self) -> None:
        for item in self._dst_list.selectedItems():
            self._dst_list.takeItem(self._dst_list.row(item))

    # ── Navigation ────────────────────────────────────────────────────
    def _go_next(self) -> None:
        if self._step == len(STEPS) - 1:
            self._finish()
            return
        if self._step == 1:
            self._populate_category_table()
        if self._step == len(STEPS) - 2:
            self._save_categories()
            self._update_summary()

        self._step += 1
        self._stack.setCurrentIndex(self._step)
        self._indicator.set_step(self._step)
        self._step_lbl.setText(f"Step {self._step + 1} of {len(STEPS)}")
        self._btn_back.setVisible(self._step > 0)
        if self._step == len(STEPS) - 1:
            self._btn_next.setText("Open Dashboard →")
        else:
            self._btn_next.setText("Next →")

    def _go_back(self) -> None:
        if self._step <= 0:
            return
        self._step -= 1
        self._stack.setCurrentIndex(self._step)
        self._indicator.set_step(self._step)
        self._step_lbl.setText(f"Step {self._step + 1} of {len(STEPS)}")
        self._btn_back.setVisible(self._step > 0)
        self._btn_next.setText("Next →")

    def _save_categories(self) -> None:
        for r in range(self._cat_table.rowCount()):
            name = (self._cat_table.item(r, 0) or QTableWidgetItem()).text().strip()
            if not name:
                continue
            mtype = self._cat_table.cellWidget(r, 1).currentText()
            api   = self._cat_table.cellWidget(r, 2).currentText()
            dest  = (self._cat_table.item(r, 3) or QTableWidgetItem()).text().strip()
            self._db.add_category(name, mtype, api, dest)

    def _update_summary(self) -> None:
        srcs = len(self._db.get_source_folders())
        dsts = len(self._db.get_destinations())
        cats = len(self._db.get_categories())
        tmdb = "✓" if self._config.has_api_key("tmdb") else "not set"
        self._summary_lbl.setText(
            f"{srcs} source folder(s), {dsts} destination(s), {cats} categories. TMDb: {tmdb}. AniList: always active.")

    def _finish(self) -> None:
        self._config.mark_launched()
        self.accept()
