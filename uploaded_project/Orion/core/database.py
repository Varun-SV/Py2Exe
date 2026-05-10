"""
Orion — single SQLite database for all persistent state.
Uses individual execute() calls to avoid SQL quoting issues inside executescript.
"""
from __future__ import annotations
import sqlite3
import json
from pathlib import Path
from typing import Any


class Database:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._conn: sqlite3.Connection | None = None

    def open(self) -> None:
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def close(self) -> None:
        if self._conn:
            self._conn.close()

    def _c(self) -> sqlite3.Connection:
        if not self._conn:
            raise RuntimeError("Database not opened — call open() first")
        return self._conn

    # ── Schema ─────────────────────────────────────────────────────────
    def _init_schema(self) -> None:
        c = self._c()
        c.execute("""CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT ''
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS source_folders (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            path       TEXT UNIQUE NOT NULL,
            tag        TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS destination_roots (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            drive TEXT NOT NULL,
            path  TEXT UNIQUE NOT NULL
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS categories (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            name           TEXT UNIQUE NOT NULL,
            media_type     TEXT NOT NULL DEFAULT 'movie',
            api_pref       TEXT NOT NULL DEFAULT 'tmdb',
            dest_subpath   TEXT NOT NULL DEFAULT '',
            episode_naming TEXT NOT NULL DEFAULT 'S{s:02d}E{e:02d}',
            subtitle_langs TEXT NOT NULL DEFAULT '["en"]',
            created_at     TEXT NOT NULL DEFAULT (datetime('now'))
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS scan_items (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            source_folder_id  INTEGER REFERENCES source_folders(id) ON DELETE CASCADE,
            path              TEXT UNIQUE NOT NULL,
            name              TEXT NOT NULL,
            item_type         TEXT NOT NULL DEFAULT 'folder',
            detected_category TEXT NOT NULL DEFAULT '',
            parent_path       TEXT NOT NULL DEFAULT '',
            status            TEXT NOT NULL DEFAULT 'pending',
            is_leaf           INTEGER NOT NULL DEFAULT 1,
            updated_at        TEXT NOT NULL DEFAULT (datetime('now'))
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS rename_choices (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            original_name TEXT UNIQUE NOT NULL,
            chosen_name   TEXT NOT NULL,
            media_type    TEXT NOT NULL DEFAULT '',
            source        TEXT NOT NULL DEFAULT 'user',
            created_at    TEXT NOT NULL DEFAULT (datetime('now'))
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS file_rename_choices (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            original_path TEXT UNIQUE NOT NULL,
            chosen_name   TEXT NOT NULL,
            kept_tags     TEXT NOT NULL DEFAULT '[]',
            is_versioned  INTEGER NOT NULL DEFAULT 0,
            created_at    TEXT NOT NULL DEFAULT (datetime('now'))
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS activity_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            action     TEXT NOT NULL,
            item_path  TEXT NOT NULL,
            detail     TEXT NOT NULL DEFAULT '',
            status     TEXT NOT NULL DEFAULT 'ok',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )""")
        self._conn.commit()

    # ── Settings ────────────────────────────────────────────────────────
    def setting_get(self, key: str, default: str = "") -> str:
        row = self._c().execute(
            "SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def setting_set(self, key: str, value: str) -> None:
        self._c().execute(
            "INSERT INTO settings(key,value) VALUES(?,?)"
            " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value))
        self._conn.commit()

    # ── Source folders ──────────────────────────────────────────────────
    def add_source_folder(self, path: str, tag: str = "") -> int:
        cur = self._c().execute(
            "INSERT OR IGNORE INTO source_folders(path,tag) VALUES(?,?)",
            (path, tag))
        self._conn.commit()
        return cur.lastrowid or self.get_source_folder_id(path)

    def get_source_folder_id(self, path: str) -> int:
        row = self._c().execute(
            "SELECT id FROM source_folders WHERE path=?", (path,)).fetchone()
        return row["id"] if row else -1

    def get_source_folders(self) -> list[dict]:
        return [dict(r) for r in
                self._c().execute("SELECT * FROM source_folders ORDER BY id")]

    def update_source_folder(self, fid: int, tag: str) -> None:
        self._c().execute(
            "UPDATE source_folders SET tag=? WHERE id=?", (tag, fid))
        self._conn.commit()

    def delete_source_folder(self, fid: int) -> None:
        self._c().execute("DELETE FROM source_folders WHERE id=?", (fid,))
        self._conn.commit()

    # ── Destination roots ───────────────────────────────────────────────
    def upsert_destination(self, drive: str, path: str) -> None:
        self._c().execute(
            "INSERT INTO destination_roots(drive,path) VALUES(?,?)"
            " ON CONFLICT(path) DO UPDATE SET drive=excluded.drive",
            (drive, path))
        self._conn.commit()

    def get_destinations(self) -> list[dict]:
        return [dict(r) for r in
                self._c().execute(
                    "SELECT * FROM destination_roots ORDER BY drive")]

    def delete_destination(self, did: int) -> None:
        self._c().execute(
            "DELETE FROM destination_roots WHERE id=?", (did,))
        self._conn.commit()

    # ── Categories ──────────────────────────────────────────────────────
    def add_category(self, name: str, media_type: str,
                     api_pref: str = "tmdb",
                     dest_subpath: str = "") -> int:
        cur = self._c().execute(
            "INSERT OR IGNORE INTO categories"
            "(name,media_type,api_pref,dest_subpath) VALUES(?,?,?,?)",
            (name, media_type, api_pref, dest_subpath))
        self._conn.commit()
        return cur.lastrowid or 0

    def get_categories(self) -> list[dict]:
        return [dict(r) for r in
                self._c().execute("SELECT * FROM categories ORDER BY name")]

    def update_category(self, cid: int, **kwargs: Any) -> None:
        sets = ", ".join(f"{k}=?" for k in kwargs)
        self._c().execute(
            f"UPDATE categories SET {sets} WHERE id=?",
            (*kwargs.values(), cid))
        self._conn.commit()

    def delete_category(self, cid: int) -> None:
        self._c().execute("DELETE FROM categories WHERE id=?", (cid,))
        self._conn.commit()

    def get_category(self, name: str) -> dict | None:
        row = self._c().execute(
            "SELECT * FROM categories WHERE name=?", (name,)).fetchone()
        return dict(row) if row else None

    # ── Scan items ──────────────────────────────────────────────────────
    def clear_scan_items(self) -> None:
        self._c().execute("DELETE FROM scan_items")
        self._conn.commit()

    def add_scan_item(self, source_folder_id: int, path: str, name: str,
                      item_type: str, detected_category: str = "",
                      parent_path: str = "", is_leaf: bool = True) -> int:
        cur = self._c().execute(
            "INSERT OR REPLACE INTO scan_items"
            "(source_folder_id,path,name,item_type,"
            " detected_category,parent_path,is_leaf)"
            " VALUES(?,?,?,?,?,?,?)",
            (source_folder_id, path, name, item_type,
             detected_category, parent_path, 1 if is_leaf else 0))
        self._conn.commit()
        return cur.lastrowid

    def get_scan_items(self, status: str | None = None,
                       category: str | None = None) -> list[dict]:
        q, p = "SELECT * FROM scan_items WHERE 1=1", []
        if status:
            q += " AND status=?";   p.append(status)
        if category:
            q += " AND detected_category=?"; p.append(category)
        return [dict(r) for r in
                self._c().execute(q + " ORDER BY name", p)]

    def update_scan_item_status(self, item_id: int, status: str) -> None:
        self._c().execute(
            "UPDATE scan_items SET status=?, updated_at=datetime('now')"
            " WHERE id=?",
            (status, item_id))
        self._conn.commit()

    # ── Rename choices ──────────────────────────────────────────────────
    def get_rename_choice(self, original_name: str) -> dict | None:
        row = self._c().execute(
            "SELECT * FROM rename_choices WHERE original_name=?",
            (original_name,)).fetchone()
        return dict(row) if row else None

    def set_rename_choice(self, original_name: str, chosen_name: str,
                          media_type: str = "",
                          source: str = "user") -> None:
        self._c().execute(
            "INSERT INTO rename_choices"
            "(original_name,chosen_name,media_type,source) VALUES(?,?,?,?)"
            " ON CONFLICT(original_name)"
            " DO UPDATE SET chosen_name=excluded.chosen_name,"
            "               source=excluded.source",
            (original_name, chosen_name, media_type, source))
        self._conn.commit()

    def get_all_rename_choices(self) -> list[dict]:
        return [dict(r) for r in
                self._c().execute(
                    "SELECT * FROM rename_choices ORDER BY original_name")]

    def delete_rename_choice(self, original_name: str) -> None:
        self._c().execute(
            "DELETE FROM rename_choices WHERE original_name=?",
            (original_name,))
        self._conn.commit()

    # ── File rename choices ─────────────────────────────────────────────
    def get_file_rename_choice(self, original_path: str) -> dict | None:
        row = self._c().execute(
            "SELECT * FROM file_rename_choices WHERE original_path=?",
            (original_path,)).fetchone()
        return dict(row) if row else None

    def set_file_rename_choice(self, original_path: str, chosen_name: str,
                               kept_tags: list[str],
                               is_versioned: bool = False) -> None:
        self._c().execute(
            "INSERT INTO file_rename_choices"
            "(original_path,chosen_name,kept_tags,is_versioned) VALUES(?,?,?,?)"
            " ON CONFLICT(original_path)"
            " DO UPDATE SET chosen_name=excluded.chosen_name,"
            "               kept_tags=excluded.kept_tags,"
            "               is_versioned=excluded.is_versioned",
            (original_path, chosen_name,
             json.dumps(kept_tags), 1 if is_versioned else 0))
        self._conn.commit()

    # ── Activity log ────────────────────────────────────────────────────
    def add_log(self, action: str, item_path: str,
                detail: str = "", status: str = "ok") -> None:
        self._c().execute(
            "INSERT INTO activity_log(action,item_path,detail,status)"
            " VALUES(?,?,?,?)",
            (action, item_path, detail, status))
        self._conn.commit()

    def get_logs(self, limit: int = 200) -> list[dict]:
        return [dict(r) for r in
                self._c().execute(
                    "SELECT * FROM activity_log ORDER BY id DESC LIMIT ?",
                    (limit,))]

    # ── Stats ───────────────────────────────────────────────────────────
    def get_stats(self) -> dict:
        c = self._c()
        def _count(where: str = "") -> int:
            q = "SELECT COUNT(*) FROM scan_items"
            if where:
                q += " WHERE " + where
            return c.execute(q).fetchone()[0]
        return {
            "total":   _count(),
            "pending": _count("status='pending'"),
            "moved":   _count("status='moved'"),
            "errors":  _count("status='error'"),
        }
