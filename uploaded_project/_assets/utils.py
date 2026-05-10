"""
Shared utilities: filename sanitization, franchise detection,
drive info, file type sets.
"""
from __future__ import annotations
import os, re, shutil
from pathlib import Path

VIDEO_EXTS    = {".mkv",".mp4",".avi",".m4v",".mov",".wmv",".ts",".m2ts",".webm",".divx",".flv",".rmvb",".vob"}
SUBTITLE_EXTS = {".srt",".ass",".ssa",".sub",".vtt",".idx",".sup"}
AUDIO_EXTS    = {".mp3",".flac",".aac",".m4a",".opus",".ogg",".wav"}

_WIN_ILLEGAL = {":": " -", "?": "", "*": "", '"': "'", "<": "", ">": "", "|": "", "/": ""}
_TRAIL_RE    = re.compile(r"[ \t.]+$")
_SEASON_RE   = re.compile(r"^(season|ova|specials?|extras?|bonus|films?)\s*\d*$", re.IGNORECASE)
_MOVIEDIR_RE = re.compile(
    r"^(subs?|subtitles?|extras?|featurettes?|behind.the.scenes|deleted.scenes|"
    r"interviews?|trailers?|sample|bonus|video.ts|bdmv|backup|certificate)$",
    re.IGNORECASE)
_JELLYFIN_RE = re.compile(r"^.+\s\(\d{4}\)(\s\[[\w\s\-]+\])*$", re.IGNORECASE)


def sanitize_windows_name(name: str) -> str:
    """Remove / replace characters illegal in Windows file/folder names."""
    for ch, rep in _WIN_ILLEGAL.items():
        name = name.replace(ch, rep)
    name = re.sub(r" {2,}", " ", name)
    return _TRAIL_RE.sub("", name).strip()


def is_jellyfin_folder_format(name: str) -> bool:
    """True if folder already matches 'Title (Year)' or 'Title (Year) [tag]' pattern."""
    return bool(_JELLYFIN_RE.match(name.strip()))


def has_video_files(folder: Path) -> bool:
    """True if folder directly contains at least one video file."""
    try:
        return any(f.is_file() and f.suffix.lower() in VIDEO_EXTS for f in folder.iterdir())
    except PermissionError:
        return False


def is_series_folder(folder: Path) -> bool:
    """True if children include Season / OVA / Specials dirs (anime series)."""
    try:
        return any(d.is_dir() and _SEASON_RE.match(d.name) for d in folder.iterdir())
    except PermissionError:
        return False


def collect_movie_leaves(folder: Path) -> list[Path]:
    """
    Recursively find all leaf movie/series folders under a directory.
    Handles arbitrary franchise nesting (Marvel/Avengers/film…).
    """
    if not folder.is_dir():
        return [folder]
    if has_video_files(folder):
        return [folder]

    try:
        subdirs = [c for c in folder.iterdir() if c.is_dir()]
    except PermissionError:
        return [folder]

    if not subdirs:
        return [folder]
    if any(_SEASON_RE.match(c.name) for c in subdirs):
        return [folder]                          # anime series — keep as unit
    if all(_MOVIEDIR_RE.match(c.name) for c in subdirs):
        return [folder]                          # movie-internal folders

    results: list[Path] = []
    for child in subdirs:
        results.extend(collect_movie_leaves(child))
    return results


def get_drive_info(path: str) -> tuple[int, int]:
    """Return (free_bytes, total_bytes) for the drive containing path."""
    try:
        usage = shutil.disk_usage(path)
        return usage.free, usage.total
    except Exception:
        return 0, 0


def format_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"
