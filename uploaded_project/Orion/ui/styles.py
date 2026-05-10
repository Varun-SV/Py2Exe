"""Orion dark theme — Jellyfin-inspired QSS stylesheet."""

ACCENT   = "#00a4dc"
BG_WIN   = "#111111"
BG_PANEL = "#171717"
BG_CARD  = "#1e1e1e"
BG_INPUT = "#141414"
BG_HOVER = "#252525"
FG_PRI   = "#ffffff"
FG_SEC   = "rgba(255,255,255,0.55)"
FG_MUT   = "rgba(255,255,255,0.28)"
BORDER   = "rgba(255,255,255,0.09)"
SUCCESS  = "#28c840"
WARN     = "#febc2e"
DANGER   = "#ff5f57"

DARK_STYLESHEET = f"""
QMainWindow, QDialog {{
    background: {BG_WIN};
}}
QWidget {{
    background: transparent;
    color: {FG_PRI};
    font-family: "Segoe UI", "SF Pro Text", system-ui, sans-serif;
    font-size: 13px;
}}
QScrollArea, QScrollArea > QWidget > QWidget {{
    background: transparent;
    border: none;
}}

/* ── Sidebar ── */
#sidebar {{
    background: #0d0d0d;
    border-right: 1px solid {BORDER};
}}
#sidebar QPushButton {{
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 8px;
    color: {FG_MUT};
}}
#sidebar QPushButton:hover {{
    background: {BG_HOVER};
    color: {FG_SEC};
}}
#sidebar QPushButton:checked {{
    background: rgba(0,164,220,0.15);
    color: {ACCENT};
}}

/* ── Cards / panels ── */
#card {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}
#card_accent {{
    background: {BG_CARD};
    border: 1px solid rgba(0,164,220,0.25);
    border-radius: 10px;
}}

/* ── Buttons ── */
QPushButton {{
    background: {BG_HOVER};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 14px;
    color: {FG_SEC};
}}
QPushButton:hover {{
    background: #2e2e2e;
    color: {FG_PRI};
    border-color: rgba(255,255,255,0.18);
}}
QPushButton:pressed {{
    background: #222;
}}
QPushButton#btn_accent {{
    background: {ACCENT};
    border: none;
    color: #fff;
    font-weight: 500;
}}
QPushButton#btn_accent:hover {{
    background: #0092c7;
}}
QPushButton#btn_danger {{
    background: transparent;
    border: 1px solid rgba(255,95,87,0.35);
    color: {DANGER};
}}
QPushButton#btn_danger:hover {{
    background: rgba(255,95,87,0.1);
}}
QPushButton:disabled {{
    opacity: 0.4;
}}

/* ── Inputs ── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    color: {FG_PRI};
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QTextEdit:focus {{
    border-color: rgba(0,164,220,0.5);
}}
QComboBox {{
    background: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 10px;
    color: {FG_PRI};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    selection-background-color: rgba(0,164,220,0.2);
}}

/* ── Lists / Tables ── */
QListWidget, QTreeWidget, QTableWidget {{
    background: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    outline: none;
}}
QListWidget::item, QTreeWidget::item, QTableWidget::item {{
    padding: 6px 8px;
    border-radius: 4px;
    color: {FG_SEC};
}}
QListWidget::item:selected, QTreeWidget::item:selected {{
    background: rgba(0,164,220,0.18);
    color: {FG_PRI};
}}
QListWidget::item:hover, QTreeWidget::item:hover {{
    background: {BG_HOVER};
    color: {FG_PRI};
}}
QTableWidget::item:selected {{
    background: rgba(0,164,220,0.18);
}}
QHeaderView::section {{
    background: {BG_CARD};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 6px 10px;
    color: {FG_MUT};
    font-size: 11px;
    letter-spacing: 0.05em;
}}

/* ── Progress bar ── */
QProgressBar {{
    background: rgba(255,255,255,0.07);
    border: none;
    border-radius: 3px;
    height: 4px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 3px;
}}

/* ── Tabs ── */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    background: {BG_PANEL};
}}
QTabBar::tab {{
    background: transparent;
    padding: 8px 16px;
    color: {FG_MUT};
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{
    color: {ACCENT};
    border-bottom: 2px solid {ACCENT};
}}
QTabBar::tab:hover {{
    color: {FG_SEC};
}}

/* ── ScrollBar ── */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: rgba(255,255,255,0.15);
    border-radius: 3px;
    min-height: 40px;
}}
QScrollBar::handle:vertical:hover {{
    background: rgba(255,255,255,0.25);
}}
QScrollBar::add-line, QScrollBar::sub-line {{ background: none; border: none; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
}}
QScrollBar::handle:horizontal {{
    background: rgba(255,255,255,0.15);
    border-radius: 3px;
}}

/* ── Status bar ── */
QStatusBar {{
    background: #0d0d0d;
    border-top: 1px solid {BORDER};
    color: {FG_MUT};
    font-size: 11px;
}}

/* ── Splitter ── */
QSplitter::handle {{
    background: {BORDER};
    width: 1px;
}}

/* ── Check / Radio ── */
QCheckBox {{ spacing: 6px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 4px;
    background: {BG_INPUT};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
    image: url(none);
}}

/* ── Tooltip ── */
QToolTip {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    color: {FG_PRI};
    border-radius: 5px;
    padding: 4px 8px;
}}

/* ── Message box ── */
QMessageBox {{
    background: {BG_CARD};
}}
QMessageBox QPushButton {{
    min-width: 80px;
}}

/* ── Group box ── */
QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
    color: {FG_SEC};
    font-size: 11px;
    letter-spacing: 0.06em;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
    color: {FG_MUT};
    font-size: 11px;
}}
"""
