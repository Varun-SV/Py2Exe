"""
Rename panel — Q6-B grid sidebar design.
Left: list of all items grouped by status.
Right: candidate cards with async poster thumbnails.
"""
from __future__ import annotations
import io, threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QScrollArea,
    QSplitter, QProgressBar, QSizePolicy, QLineEdit, QInputDialog,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject
from PyQt6.QtGui import QColor, QPixmap, QImage

from core.config import Config
from core.database import Database
from core.renamer import Renamer
from core.utils import sanitize_windows_name
from api.tmdb import TMDbClient, Candidate
from api.anilist import AniListClient
from workers.api_worker import ApiWorker
from workers.move_worker import MoveWorker


class PosterSignal(QObject):
    ready = pyqtSignal(str, bytes)  # url, image bytes


class CandidateCard(QFrame):
    selected = pyqtSignal(object)  # Candidate

    def __init__(self, candidate: Candidate, with_year: bool, parent=None):
        super().__init__(parent)
        self._candidate = candidate
        self.setFixedWidth(116)
        self.setObjectName("candidate_card")
        self.setStyleSheet(
            "#candidate_card{background:#1e1e1e;border:1.5px solid rgba(255,255,255,0.1);"
            "border-radius:8px;}"
            "#candidate_card:hover{border-color:#00a4dc;background:#252525;cursor:pointer;}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        v = QVBoxLayout(self)
        v.setContentsMargins(5, 5, 5, 6)
        v.setSpacing(4)

        self._poster = QLabel("🎬")
        self._poster.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._poster.setFixedSize(QSize(106, 156))
        self._poster.setStyleSheet("background:#161616; border-radius:5px; "
                                   "font-size:28px; color:rgba(255,255,255,0.15);")
        v.addWidget(self._poster)

        display = candidate.display(with_year)
        rom = candidate.extra.get("romaji", "")
        text = display + (f"\n{rom}" if rom and rom != candidate.name else "")
        name_lbl = QLabel(text)
        name_lbl.setWordWrap(True)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setStyleSheet("color:rgba(255,255,255,0.7); font-size:10px; line-height:1.4;")
        name_lbl.setMaximumWidth(106)
        v.addWidget(name_lbl)

        if candidate.poster_url:
            self._load_poster(candidate.poster_url)

    def _load_poster(self, url: str) -> None:
        sig = PosterSignal(self)
        sig.ready.connect(self._on_poster)

        def _fetch():
            try:
                import requests
                data = requests.get(url, timeout=6).content
                sig.ready.emit(url, data)
            except Exception:
                pass
        threading.Thread(target=_fetch, daemon=True).start()

    def _on_poster(self, url: str, data: bytes) -> None:
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(data)).convert("RGB").resize((106, 156))
            qimg = QImage(img.tobytes(), 106, 156, 106 * 3, QImage.Format.Format_RGB888)
            self._poster.setPixmap(QPixmap.fromImage(qimg))
            self._poster.setText("")
        except Exception:
            pass

    def highlight(self, on: bool) -> None:
        color = "#00a4dc" if on else "rgba(255,255,255,0.1)"
        self.setStyleSheet(
            f"#candidate_card{{background:{'#1a2a34' if on else '#1e1e1e'};"
            f"border:2px solid {color};border-radius:8px;}}")

    def mousePressEvent(self, event) -> None:
        self.selected.emit(self._candidate)
        super().mousePressEvent(event)


class RenamePanel(QWidget):
    def __init__(self, db: Database, config: Config, parent=None):
        super().__init__(parent)
        self._db       = db
        self._config   = config
        self._items:   list[dict] = []
        self._current: dict | None = None
        self._cards:   list[CandidateCard] = []
        self._worker:  ApiWorker | None = None
        self._move_worker: MoveWorker | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # Toolbar
        toolbar = QWidget()
        toolbar.setStyleSheet("background:#151515; border-bottom:1px solid rgba(255,255,255,0.07);")
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(16, 10, 16, 10)
        tl.setSpacing(10)

        self._prog_lbl = QLabel("No items")
        self._prog_lbl.setStyleSheet("color:rgba(255,255,255,0.45); font-size:12px;")
        tl.addWidget(self._prog_lbl)
        self._prog_bar = QProgressBar()
        self._prog_bar.setFixedHeight(3)
        self._prog_bar.setTextVisible(False)
        tl.addWidget(self._prog_bar, 1)
        self._approve_btn = QPushButton("Approve all auto-matched")
        self._approve_btn.setObjectName("btn_accent")
        self._approve_btn.clicked.connect(self._approve_all_auto)
        tl.addWidget(self._approve_btn)
        self._move_btn = QPushButton("Move all resolved →")
        self._move_btn.clicked.connect(self._start_move)
        tl.addWidget(self._move_btn)
        v.addWidget(toolbar)

        # Splitter: left list | right candidates
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle{background:rgba(255,255,255,0.07);width:1px;}")

        # Left: item list
        left = QWidget()
        left.setStyleSheet("background:#131313;")
        left.setMinimumWidth(220)
        left.setMaximumWidth(300)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(0)
        self._item_list = QListWidget()
        self._item_list.setStyleSheet(
            "QListWidget{background:transparent;border:none;outline:none;}"
            "QListWidget::item{padding:7px 12px;border-radius:0;}"
            "QListWidget::item:selected{background:rgba(0,164,220,0.15);"
            "border-right:2px solid #00a4dc;}"
            "QListWidget::item:hover{background:rgba(255,255,255,0.04);}")
        self._item_list.currentRowChanged.connect(self._on_item_selected)
        lv.addWidget(self._item_list, 1)
        splitter.addWidget(left)

        # Right: current item + candidate cards
        right = QWidget()
        right.setStyleSheet("background:#171717;")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(20, 20, 20, 16)
        rv.setSpacing(12)

        # Item info
        self._item_title = QLabel("Select an item to rename")
        self._item_title.setStyleSheet("font-size:14px; font-weight:500; color:#fff;")
        self._item_title.setWordWrap(True)
        rv.addWidget(self._item_title)
        self._item_sub = QLabel("")
        self._item_sub.setStyleSheet("font-size:11px; color:rgba(255,255,255,0.35); font-family:monospace;")
        self._item_sub.setWordWrap(True)
        rv.addWidget(self._item_sub)

        # Loading indicator
        self._loading_lbl = QLabel("Fetching candidates…")
        self._loading_lbl.setStyleSheet("color:#00a4dc; font-size:11px;")
        self._loading_lbl.setVisible(False)
        rv.addWidget(self._loading_lbl)

        # Cards scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self._cards_wrap = QWidget()
        self._cards_wrap.setStyleSheet("background:transparent;")
        self._cards_layout = QHBoxLayout(self._cards_wrap)
        self._cards_layout.setContentsMargins(0, 4, 0, 4)
        self._cards_layout.setSpacing(10)
        self._cards_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        scroll.setWidget(self._cards_wrap)
        rv.addWidget(scroll, 1)

        # Action row
        actions = QHBoxLayout()
        self._skip_btn = QPushButton("Skip")
        self._skip_btn.clicked.connect(self._skip_item)
        actions.addWidget(self._skip_btn)
        self._manual_btn = QPushButton("Enter manually")
        self._manual_btn.clicked.connect(self._manual_entry)
        actions.addWidget(self._manual_btn)
        actions.addStretch()
        self._confirm_btn = QPushButton("Confirm →")
        self._confirm_btn.setObjectName("btn_accent")
        self._confirm_btn.setEnabled(False)
        self._confirm_btn.clicked.connect(self._confirm_current)
        actions.addWidget(self._confirm_btn)
        rv.addLayout(actions)
        splitter.addWidget(right)

        splitter.setSizes([240, 700])
        v.addWidget(splitter, 1)

    # ── Data ──────────────────────────────────────────────────────────
    def refresh(self) -> None:
        self._items = self._db.get_scan_items(status="pending")
        self._populate_list()
        self._update_toolbar()

    def _populate_list(self) -> None:
        self._item_list.clear()
        resolved = self._db.get_all_rename_choices()
        resolved_names = {r["original_name"] for r in resolved}

        pending, skipped, done = [], [], []
        for item in self._items:
            if item["status"] == "moved":
                done.append(item)
            elif item["name"] in resolved_names:
                done.append(item)
            else:
                pending.append(item)

        def _section(label: str):
            li = QListWidgetItem(f"  {label}")
            li.setFlags(Qt.ItemFlag.NoItemFlags)
            li.setForeground(QColor("rgba(255,255,255,0.2)"))
            font = li.font(); font.setPointSize(9); li.setFont(font)
            self._item_list.addItem(li)

        if pending:
            _section(f"NEEDS REVIEW · {len(pending)}")
            for it in pending:
                li = QListWidgetItem(f"  {it['name']}")
                li.setData(Qt.ItemDataRole.UserRole, it)
                li.setForeground(QColor("#ffffff"))
                self._item_list.addItem(li)
        if done:
            _section(f"RESOLVED · {len(done)}")
            for it in done:
                li = QListWidgetItem(f"  {it['name']}")
                li.setData(Qt.ItemDataRole.UserRole, it)
                li.setForeground(QColor("#28c840"))
                self._item_list.addItem(li)

    def _update_toolbar(self) -> None:
        total    = len(self._items)
        resolved = len(self._db.get_all_rename_choices())
        self._prog_bar.setMaximum(max(total, 1))
        self._prog_bar.setValue(resolved)
        self._prog_lbl.setText(f"{resolved} of {total} resolved")

    def _on_item_selected(self, row: int) -> None:
        li = self._item_list.item(row)
        if not li:
            return
        item = li.data(Qt.ItemDataRole.UserRole)
        if not item:
            return
        self._current = item
        self._selected_candidate: Candidate | None = None
        self._confirm_btn.setEnabled(False)
        self._item_title.setText(item["name"])
        self._item_sub.setText(item["path"])
        self._clear_cards()

        # Check saved choice
        saved = self._db.get_rename_choice(item["name"])
        if saved:
            self._item_title.setText(f"{item['name']}  →  {saved['chosen_name']}")
            return

        # Fetch candidates
        cat = self._db.get_category(item["detected_category"])
        if not cat:
            self._load_candidates_empty()
            return
        tmdb    = TMDbClient(self._config.get_api_key("tmdb"))
        anilist = AniListClient()
        renamer = Renamer(self._db, tmdb, anilist)
        self._loading_lbl.setVisible(True)
        self._worker = ApiWorker(renamer, item["name"],
                                 cat["media_type"], cat["api_pref"])
        self._worker.candidates_ready.connect(self._on_candidates)
        self._worker.error.connect(lambda e: self._loading_lbl.setText(f"Error: {e}"))
        self._worker.start()

    def _on_candidates(self, candidates: list) -> None:
        self._loading_lbl.setVisible(False)
        if not candidates:
            self._load_candidates_empty()
            return
        if len(candidates) == 1:
            # Auto-accept
            c   = candidates[0]
            cat = self._db.get_category(
                self._current["detected_category"] if self._current else "")
            mtype = cat["media_type"] if cat else "movie"
            with_year = mtype in ("movie", "anime_film")
            name = sanitize_windows_name(c.display(with_year))
            self._db.set_rename_choice(
                self._current["name"], name, mtype, "auto")
            self._item_title.setText(f"{self._current['name']}  →  {name}  (auto)")
            self._populate_list()
            self._update_toolbar()
            return

        cat = self._db.get_category(
            self._current["detected_category"] if self._current else "")
        mtype = cat["media_type"] if cat else "movie"
        with_year = mtype in ("movie", "anime_film")
        for c in candidates:
            card = CandidateCard(c, with_year)
            card.selected.connect(self._on_card_selected)
            self._cards_layout.addWidget(card)
            self._cards.append(card)

    def _load_candidates_empty(self) -> None:
        lbl = QLabel("No API results. Use 'Enter manually' or 'Skip'.")
        lbl.setStyleSheet("color:rgba(255,255,255,0.3); font-size:12px;")
        self._cards_layout.addWidget(lbl)

    def _on_card_selected(self, candidate: Candidate) -> None:
        self._selected_candidate = candidate
        for card in self._cards:
            card.highlight(False)
        self.sender().highlight(True)
        self._confirm_btn.setEnabled(True)

    def _clear_cards(self) -> None:
        self._cards = []
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _confirm_current(self) -> None:
        if not self._current or not self._selected_candidate:
            return
        cat = self._db.get_category(self._current["detected_category"])
        mtype = cat["media_type"] if cat else "movie"
        with_year = mtype in ("movie", "anime_film")
        name = sanitize_windows_name(self._selected_candidate.display(with_year))
        self._db.set_rename_choice(self._current["name"], name, mtype, "user")
        self._populate_list()
        self._update_toolbar()
        # Auto-advance
        row = self._item_list.currentRow()
        if row + 1 < self._item_list.count():
            self._item_list.setCurrentRow(row + 1)

    def _skip_item(self) -> None:
        if not self._current:
            return
        self._db.add_log("skip", self._current["path"], "user skipped rename", "warning")
        row = self._item_list.currentRow()
        if row + 1 < self._item_list.count():
            self._item_list.setCurrentRow(row + 1)

    def _manual_entry(self) -> None:
        if not self._current:
            return
        text, ok = QInputDialog.getText(self, "Manual rename",
                                        "Enter the correct folder name:")
        if ok and text.strip():
            name = sanitize_windows_name(text.strip())
            cat  = self._db.get_category(self._current["detected_category"])
            mtype = cat["media_type"] if cat else "movie"
            self._db.set_rename_choice(self._current["name"], name, mtype, "user")
            self._populate_list()
            self._update_toolbar()

    def _approve_all_auto(self) -> None:
        """Accept all single-candidate auto-matches that haven't been decided yet."""
        undecided = [it for it in self._items
                     if not self._db.get_rename_choice(it["name"])]
        approved = 0
        for item in undecided:
            cat = self._db.get_category(item["detected_category"])
            if not cat:
                continue
            from core.renamer import Renamer
            tmdb    = TMDbClient(self._config.get_api_key("tmdb"))
            anilist = AniListClient()
            renamer = Renamer(self._db, tmdb, anilist)
            candidates = renamer.get_candidates(item["name"], cat["media_type"], cat["api_pref"])
            if len(candidates) == 1:
                with_year = cat["media_type"] in ("movie", "anime_film")
                name = sanitize_windows_name(candidates[0].display(with_year))
                self._db.set_rename_choice(item["name"], name, cat["media_type"], "auto")
                approved += 1
        self._populate_list()
        self._update_toolbar()

    def _start_move(self) -> None:
        items = self._db.get_scan_items()
        choices = {r["original_name"]: r["chosen_name"]
                   for r in self._db.get_all_rename_choices()}
        dsts  = self._db.get_destinations()
        cats  = self._db.get_categories()
        self._move_worker = MoveWorker(self._db, items, dsts, cats, choices)
        self._move_worker.complete.connect(self._on_move_done)
        self._move_worker.start()

    def _on_move_done(self, moved: int, failed: int) -> None:
        self.refresh()

    def on_shown(self) -> None:
        self.refresh()
