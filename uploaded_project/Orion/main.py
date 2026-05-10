"""
Orion — Media Library Organizer
Entry point: initialise app, open DB, show wizard or main window.
"""
from __future__ import annotations
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from core.config import Config
from core.database import Database
from ui.styles import DARK_STYLESHEET


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Orion")
    app.setOrganizationName("Orion")
    app.setQuitOnLastWindowClosed(False)   # stay alive in system tray
    app.setStyleSheet(DARK_STYLESHEET)

    config = Config()
    db     = Database(config.db_path)
    db.open()

    first_launch = config.is_first_launch()

    if first_launch:
        from ui.wizard import SetupWizard
        wizard = SetupWizard(db, config)
        if wizard.exec() != wizard.DialogCode.Accepted:
            db.close()
            sys.exit(0)
        config.mark_launched()

    from ui.main_window import MainWindow
    window = MainWindow(db, config)
    window.show()

    code = app.exec()
    db.close()
    sys.exit(code)


if __name__ == "__main__":
    main()
