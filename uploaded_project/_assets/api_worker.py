"""QThread that fetches API candidates for a single rename item."""
from __future__ import annotations
from PyQt6.QtCore import QThread, pyqtSignal
from core.renamer import Renamer
from api.tmdb import Candidate


class ApiWorker(QThread):
    candidates_ready = pyqtSignal(list)   # list[Candidate]
    error            = pyqtSignal(str)

    def __init__(self, renamer: Renamer,
                 folder_name: str,
                 media_type: str,
                 api_pref: str = "tmdb") -> None:
        super().__init__()
        self._renamer     = renamer
        self._folder_name = folder_name
        self._media_type  = media_type
        self._api_pref    = api_pref

    def run(self) -> None:
        try:
            candidates = self._renamer.get_candidates(
                self._folder_name, self._media_type, self._api_pref)
            self.candidates_ready.emit(candidates)
        except Exception as exc:
            self.error.emit(str(exc))
