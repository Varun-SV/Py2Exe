"""
App config — paths, first-launch detection, session-only API keys.
API keys are NEVER written to disk (in-app session only).
"""
from __future__ import annotations
import os, json
from pathlib import Path


class Config:
    APP_NAME = "JellyfinOrganizer"

    def __init__(self) -> None:
        self._appdata = Path(os.environ.get("APPDATA", Path.home())) / self.APP_NAME
        self._appdata.mkdir(parents=True, exist_ok=True)
        self._api_keys: dict[str, str] = {}
        self._prefs_path = self._appdata / "prefs.json"
        self._prefs: dict = self._load_prefs()

    @property
    def app_data_dir(self) -> Path:
        return self._appdata

    @property
    def db_path(self) -> Path:
        return self._appdata / "organizer.db"

    def is_first_launch(self) -> bool:
        return not self.db_path.exists()

    def mark_launched(self) -> None:
        self._set("launched", True)

    # Session-only API keys — never persisted
    def set_api_key(self, service: str, key: str) -> None:
        self._api_keys[service] = key.strip()

    def get_api_key(self, service: str) -> str:
        return self._api_keys.get(service, "")

    def has_api_key(self, service: str) -> bool:
        return bool(self._api_keys.get(service))

    # UI prefs (geometry, last panel index…)
    def save_geometry(self, key: str, data: dict) -> None:
        self._set(f"geo_{key}", data)

    def load_geometry(self, key: str) -> dict | None:
        return self._prefs.get(f"geo_{key}")

    def get_pref(self, key: str, default=None):
        return self._prefs.get(key, default)

    def set_pref(self, key: str, value) -> None:
        self._set(key, value)

    def _load_prefs(self) -> dict:
        if self._prefs_path.exists():
            try:
                return json.loads(self._prefs_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _set(self, key: str, value) -> None:
        self._prefs[key] = value
        self._prefs_path.write_text(
            json.dumps(self._prefs, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
