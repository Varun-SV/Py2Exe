"""
Scans source folders, detects categories from folder structure,
populates the database with scan items.
"""
from __future__ import annotations
import re
from pathlib import Path
from core.utils import collect_movie_leaves, is_series_folder, has_video_files, VIDEO_EXTS
from core.database import Database


# Heuristics to map folder names to likely media types
_ANIME_HINTS  = re.compile(r"anime|manga|ova|isekai|shounen|seinen|shojo", re.I)
_SERIES_HINTS = re.compile(r"series|shows?|tv", re.I)
_MOVIE_HINTS  = re.compile(r"movies?|films?|cinema", re.I)


class ScanResult:
    def __init__(self, path: str, name: str, item_type: str,
                 category: str, parent_path: str = "", is_leaf: bool = True):
        self.path        = path
        self.name        = name
        self.item_type   = item_type   # 'folder' | 'file'
        self.category    = category
        self.parent_path = parent_path
        self.is_leaf     = is_leaf


class Scanner:
    def __init__(self, db: Database) -> None:
        self._db = db

    # ── Public ─────────────────────────────────────────────────────────
    def scan(self, source_folder_id: int, root: Path,
             categories: list[dict],
             progress_cb=None) -> list[ScanResult]:
        """
        Walk root, detect categories, collect leaf items.
        progress_cb(message: str) called for UI updates.
        """
        results: list[ScanResult] = []
        cat_map = {c["name"].lower(): c for c in categories}

        try:
            top_level = sorted(root.iterdir(), key=lambda p: p.name.lower())
        except PermissionError:
            return results

        for idx, child in enumerate(top_level):
            if not child.is_dir():
                continue
            if progress_cb:
                progress_cb(f"Scanning {child.name}…")

            # Detect category from the child folder name / path
            category = self._detect_category(child, categories)

            # Collect leaf items inside this folder
            media_type = self._category_media_type(category, categories)
            if media_type in ("movie", "anime_film"):
                leaves = collect_movie_leaves(child)
                if len(leaves) == 1 and leaves[0] == child:
                    r = ScanResult(str(child), child.name, "folder", category)
                    results.append(r)
                    self._db.add_scan_item(source_folder_id, str(child),
                                           child.name, "folder", category, "", True)
                else:
                    for leaf in leaves:
                        r = ScanResult(str(leaf), leaf.name, "folder",
                                       category, str(child), True)
                        results.append(r)
                        self._db.add_scan_item(source_folder_id, str(leaf),
                                               leaf.name, "folder", category,
                                               str(child), True)
            else:
                # Series / anime: folder is the item
                r = ScanResult(str(child), child.name, "folder", category)
                results.append(r)
                self._db.add_scan_item(source_folder_id, str(child),
                                       child.name, "folder", category, "", True)

        return results

    def detect_categories_from_scan(self, root: Path) -> list[dict]:
        """
        Fast pre-scan: inspect top-level subfolders of root and
        suggest categories (name, inferred media_type) for the user to confirm.
        """
        suggestions = []
        try:
            for child in sorted(root.iterdir(), key=lambda p: p.name.lower()):
                if not child.is_dir():
                    continue
                media_type = self._infer_type(child)
                suggestions.append({
                    "name":       child.name,
                    "media_type": media_type,
                    "api_pref":   "anilist" if "anime" in media_type else "tmdb",
                    "source_root": str(root),
                })
        except PermissionError:
            pass
        return suggestions

    # ── Internal ───────────────────────────────────────────────────────
    def _detect_category(self, folder: Path, categories: list[dict]) -> str:
        """Match folder against known category names (case-insensitive partial match)."""
        name_lower = folder.name.lower()
        for cat in categories:
            if cat["name"].lower() in name_lower or name_lower in cat["name"].lower():
                return cat["name"]
        # Fallback: infer from folder name patterns
        return self._infer_type(folder)

    def _infer_type(self, folder: Path) -> str:
        name = folder.name.lower()
        if _ANIME_HINTS.search(name):
            return "anime"
        if _SERIES_HINTS.search(name):
            return "series"
        if _MOVIE_HINTS.search(name):
            return "movie"
        # Structural heuristic
        if is_series_folder(folder):
            return "series"
        return "movie"

    def _category_media_type(self, category_name: str,
                             categories: list[dict]) -> str:
        for cat in categories:
            if cat["name"] == category_name:
                return cat["media_type"]
        return "movie"
