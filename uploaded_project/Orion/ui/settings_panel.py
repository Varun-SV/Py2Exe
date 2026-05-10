"""Settings panel — Sources, Destinations, Categories, API Keys, File Naming, Subtitles."""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTabWidget, QFrame,
    QTableWidget, QTableWidgetItem, QComboBox, QHeaderView,
    QAbstractItemView, QLineEdit, QFileDialog, QCheckBox,
    QGroupBox, QFormLayout, QSpinBox,
)
from PyQt6.QtCore import Qt
from core.config import Config
from core.database import Database


class SettingsPanel(QWidget):
    def __init__(self, db: Database, config: Config, parent=None):
        super().__init__(parent)
        self._db     = db
        self._config = config
        self._setup_ui()

    def _setup_ui(self) -> None:
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(14)

        title = QLabel("Settings")
        title.setStyleSheet("font-size:17px; font-weight:500; color:#fff;")
        v.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(self._tab_sources(),    "Sources")
        tabs.addTab(self._tab_destinations(),"Destinations")
        tabs.addTab(self._tab_categories(), "Categories")
        tabs.addTab(self._tab_api(),        "API Keys")
        tabs.addTab(self._tab_naming(),     "File naming")
        tabs.addTab(self._tab_subtitles(),  "Subtitles")
        v.addWidget(tabs, 1)

    # ── Sources tab ────────────────────────────────────────────────────
    def _tab_sources(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(10)
        v.addWidget(self._hint("All folders Orion should scan for media."))
        self._src_list = QListWidget()
        self._src_list.setAlternatingRowColors(False)
        v.addWidget(self._src_list, 1)
        row = QHBoxLayout()
        add = QPushButton("+ Add folder")
        add.setObjectName("btn_accent")
        add.clicked.connect(self._add_source)
        row.addWidget(add)
        rm = QPushButton("Remove")
        rm.setObjectName("btn_danger")
        rm.clicked.connect(self._del_source)
        row.addWidget(rm)
        row.addStretch()
        v.addLayout(row)
        self._refresh_sources()
        return w

    def _add_source(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select source folder")
        if not path:
            return
        self._db.add_source_folder(path)
        self._refresh_sources()

    def _del_source(self) -> None:
        for item in self._src_list.selectedItems():
            fid = item.data(Qt.ItemDataRole.UserRole)
            if fid:
                self._db.delete_source_folder(fid)
        self._refresh_sources()

    def _refresh_sources(self) -> None:
        self._src_list.clear()
        for sf in self._db.get_source_folders():
            tag  = f"  [{sf['tag']}]" if sf["tag"] else ""
            item = QListWidgetItem(f"  {sf['path']}{tag}")
            item.setData(Qt.ItemDataRole.UserRole, sf["id"])
            self._src_list.addItem(item)

    # ── Destinations tab ───────────────────────────────────────────────
    def _tab_destinations(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(10)
        v.addWidget(self._hint("One root folder per drive. Categories become subfolders automatically."))
        self._dst_list = QListWidget()
        v.addWidget(self._dst_list, 1)
        row = QHBoxLayout()
        add = QPushButton("+ Add destination")
        add.setObjectName("btn_accent")
        add.clicked.connect(self._add_destination)
        row.addWidget(add)
        rm = QPushButton("Remove")
        rm.setObjectName("btn_danger")
        rm.clicked.connect(self._del_destination)
        row.addWidget(rm)
        row.addStretch()
        v.addLayout(row)
        self._refresh_destinations()
        return w

    def _add_destination(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select destination root")
        if not path:
            return
        from pathlib import Path
        drive = Path(path).drive
        self._db.upsert_destination(drive, path)
        self._refresh_destinations()

    def _del_destination(self) -> None:
        for item in self._dst_list.selectedItems():
            did = item.data(Qt.ItemDataRole.UserRole)
            if did:
                self._db.delete_destination(did)
        self._refresh_destinations()

    def _refresh_destinations(self) -> None:
        self._dst_list.clear()
        for dst in self._db.get_destinations():
            item = QListWidgetItem(f"  {dst['drive']}  →  {dst['path']}")
            item.setData(Qt.ItemDataRole.UserRole, dst["id"])
            self._dst_list.addItem(item)

    # ── Categories tab ─────────────────────────────────────────────────
    def _tab_categories(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(10)
        v.addWidget(self._hint("Define how each category is identified and where it goes."))
        self._cat_tbl = QTableWidget(0, 5)
        self._cat_tbl.setHorizontalHeaderLabels(
            ["Name", "Media type", "API", "Dest subfolder", ""])
        self._cat_tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._cat_tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._cat_tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        v.addWidget(self._cat_tbl, 1)
        row = QHBoxLayout()
        add = QPushButton("+ Add category")
        add.setObjectName("btn_accent")
        add.clicked.connect(self._add_category)
        row.addWidget(add)
        save = QPushButton("Save changes")
        save.clicked.connect(self._save_categories)
        row.addWidget(save)
        row.addStretch()
        v.addLayout(row)
        self._refresh_categories()
        return w

    def _add_category(self) -> None:
        r = self._cat_tbl.rowCount()
        self._cat_tbl.insertRow(r)
        self._cat_tbl.setItem(r, 0, QTableWidgetItem("New Category"))
        self._insert_cat_combos(r, "movie", "tmdb", "")

    def _insert_cat_combos(self, r: int, mtype: str, api: str, dest: str) -> None:
        mt = QComboBox()
        for t in ("movie", "series", "anime", "anime_film"):
            mt.addItem(t)
        mt.setCurrentText(mtype)
        self._cat_tbl.setCellWidget(r, 1, mt)
        ap = QComboBox()
        for a in ("tmdb", "anilist", "anidb", "both"):
            ap.addItem(a)
        ap.setCurrentText(api)
        self._cat_tbl.setCellWidget(r, 2, ap)
        self._cat_tbl.setItem(r, 3, QTableWidgetItem(dest))
        del_btn = QPushButton("✕")
        del_btn.setObjectName("btn_danger")
        del_btn.setFixedWidth(32)
        del_btn.clicked.connect(lambda _, row=r: self._cat_tbl.removeRow(row))
        self._cat_tbl.setCellWidget(r, 4, del_btn)

    def _refresh_categories(self) -> None:
        self._cat_tbl.setRowCount(0)
        for cat in self._db.get_categories():
            r = self._cat_tbl.rowCount()
            self._cat_tbl.insertRow(r)
            self._cat_tbl.setItem(r, 0, QTableWidgetItem(cat["name"]))
            self._insert_cat_combos(r, cat["media_type"], cat["api_pref"],
                                    cat.get("dest_subpath", ""))

    def _save_categories(self) -> None:
        # Delete all and re-insert from table state
        for cat in self._db.get_categories():
            self._db.delete_category(cat["id"])
        for r in range(self._cat_tbl.rowCount()):
            name = (self._cat_tbl.item(r, 0) or QTableWidgetItem()).text().strip()
            if not name:
                continue
            mtype = self._cat_tbl.cellWidget(r, 1).currentText()
            api   = self._cat_tbl.cellWidget(r, 2).currentText()
            dest  = (self._cat_tbl.item(r, 3) or QTableWidgetItem()).text().strip()
            self._db.add_category(name, mtype, api, dest)

    # ── API Keys tab ───────────────────────────────────────────────────
    def _tab_api(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(14)

        warn = QLabel("⚠  API keys are session-only — cleared when Orion closes. Re-enter each launch.")
        warn.setWordWrap(True)
        warn.setStyleSheet("background:rgba(254,188,46,0.08);border:1px solid rgba(254,188,46,0.2);"
                           "border-radius:6px;padding:8px 12px;color:#febc2e;font-size:12px;")
        v.addWidget(warn)

        for label, hint, key in [
            ("TMDb API Key",
             "Free at themoviedb.org/settings/api — movies, TV, episode titles, posters.",
             "tmdb"),
            ("AniDB Client ID",
             "Register at anidb.net/software/add — anime episode title fallback.",
             "anidb_client"),
        ]:
            card = QFrame()
            card.setObjectName("card")
            cv = QVBoxLayout(card)
            cv.setContentsMargins(14, 12, 14, 12)
            cv.setSpacing(6)
            cv.addWidget(self._bold(label))
            h = QLabel(hint)
            h.setStyleSheet("color:rgba(255,255,255,0.3); font-size:11px;")
            h.setWordWrap(True)
            cv.addWidget(h)
            row = QHBoxLayout()
            field = QLineEdit()
            field.setEchoMode(QLineEdit.EchoMode.Password)
            field.setPlaceholderText("Paste key here…")
            field.setText(self._config.get_api_key(key))
            field.textChanged.connect(lambda t, k=key: self._config.set_api_key(k, t))
            row.addWidget(field, 1)
            show = QPushButton("Show")
            show.setFixedWidth(60)
            show.clicked.connect(lambda _, f=field: f.setEchoMode(
                QLineEdit.EchoMode.Normal if f.echoMode() == QLineEdit.EchoMode.Password
                else QLineEdit.EchoMode.Password))
            row.addWidget(show)
            cv.addLayout(row)
            v.addWidget(card)

        al_card = QFrame()
        al_card.setObjectName("card")
        alv = QVBoxLayout(al_card)
        alv.setContentsMargins(14, 12, 14, 12)
        alv.addWidget(self._bold("AniList"))
        alv.addWidget(QLabel("Always active — no key or account needed."))
        v.addWidget(al_card)
        v.addStretch()
        return w

    # ── File naming tab ────────────────────────────────────────────────
    def _tab_naming(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(14)
        v.addWidget(self._hint("Configure how video filenames are formatted."))

        grp1 = QGroupBox("Movie files")
        f1   = QFormLayout(grp1)
        self._movie_year = QCheckBox("Include year:  Movie Title (Year).mkv")
        self._movie_year.setChecked(True)
        f1.addRow(self._movie_year)
        self._movie_res  = QCheckBox("Include resolution tag:  Movie Title (Year) [1080p].mkv")
        self._movie_res.setChecked(True)
        f1.addRow(self._movie_res)
        v.addWidget(grp1)

        grp2 = QGroupBox("Episode files (series)")
        f2   = QFormLayout(grp2)
        self._ep_pattern = QLineEdit("S{s:02d}E{e:02d}")
        self._ep_pattern.setToolTip("Use {s} for season, {e} for episode number")
        f2.addRow("Pattern:", self._ep_pattern)
        self._ep_title = QCheckBox("Append episode title (requires TMDb key)")
        f2.addRow(self._ep_title)
        v.addWidget(grp2)

        grp3 = QGroupBox("Anime episode files")
        f3   = QFormLayout(grp3)
        self._anime_pattern = QLineEdit("S{s:02d}E{e:02d}")
        f3.addRow("Pattern:", self._anime_pattern)
        v.addWidget(grp3)
        v.addStretch()
        return w

    # ── Subtitles tab ──────────────────────────────────────────────────
    def _tab_subtitles(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(14)
        v.addWidget(self._hint("Configure subtitle download services and language preferences."))

        svc_card = QFrame()
        svc_card.setObjectName("card")
        sv = QVBoxLayout(svc_card)
        sv.setContentsMargins(14, 12, 14, 12)
        sv.setSpacing(8)
        sv.addWidget(self._bold("Download service"))
        self._svc_combo = QComboBox()
        for s in ("OpenSubtitles", "Subscene (scraping)", "Both", "Disabled"):
            self._svc_combo.addItem(s)
        sv.addWidget(self._svc_combo)
        self._os_key = QLineEdit()
        self._os_key.setPlaceholderText("OpenSubtitles API key (optional, higher rate limit)")
        self._os_key.setEchoMode(QLineEdit.EchoMode.Password)
        sv.addWidget(self._os_key)
        v.addWidget(svc_card)

        lang_card = QFrame()
        lang_card.setObjectName("card")
        lv = QVBoxLayout(lang_card)
        lv.setContentsMargins(14, 12, 14, 12)
        lv.setSpacing(6)
        lv.addWidget(self._bold("Preferred languages (in order)"))
        lv.addWidget(QLabel("Enter language codes separated by commas, e.g.  en, ja, hi"))
        self._lang_field = QLineEdit("en")
        lv.addWidget(self._lang_field)
        v.addWidget(lang_card)
        v.addStretch()
        return w

    # ── Helpers ────────────────────────────────────────────────────────
    def _hint(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet("color:rgba(255,255,255,0.35); font-size:12px;")
        l.setWordWrap(True)
        return l

    def _bold(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet("color:#fff; font-size:12px; font-weight:500;")
        return l

    def on_shown(self) -> None:
        self._refresh_sources()
        self._refresh_destinations()
        self._refresh_categories()
