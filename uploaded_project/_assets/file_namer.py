"""
Video file renaming logic:
- Detect if file is already in Jellyfin format → skip
- Parse quality/edition tags from filename
- Format new Jellyfin-compliant filename
- Handle multiple copies (versioning)
"""
from __future__ import annotations
import re
from pathlib import Path
from guessit import guessit
from core.utils import sanitize_windows_name, VIDEO_EXTS

# Matches: "Title (Year).ext" or "Title (Year) [tag] [tag2].ext"
_JELLYFIN_FILE_RE = re.compile(
    r"^.+\s\(\d{4}\)(\s\[[\w\s\-]+\])*\.\w+$", re.IGNORECASE)

# Tag keys guessit returns that we expose to the user
TAG_MAP = {
    "screen_size":     "Resolution",   # 1080p, 4K, 720p
    "dynamic_range":   "HDR",          # HDR, HDR10, DV
    "source":          "Source",       # BluRay, WEBRip, WEB-DL
    "audio_codec":     "Audio",        # DTS, DD5.1, TrueHD
    "video_codec":     "Codec",        # x264, x265, HEVC
    "edition":         "Edition",      # Director\'s Cut, Extended
    "part":            "Part",         # Part 1, Part 2
    "release_group":   "Group",        # release group tag
}

# Tags always included automatically (not shown in checklist)
AUTO_INCLUDE_TAGS = {"screen_size"}


class FileTags:
    def __init__(self, raw: dict) -> None:
        self.raw = raw   # guessit output dict

    def available(self) -> dict[str, str]:
        """Return {tag_key: display_value} for all detected tags."""
        out = {}
        for key, label in TAG_MAP.items():
            val = self.raw.get(key)
            if val:
                out[key] = str(val) if not isinstance(val, list) else ", ".join(str(v) for v in val)
        return out

    def format_bracket(self, chosen_keys: list[str]) -> str:
        """Build '[tag1] [tag2]' string from chosen tag keys."""
        parts = []
        for key in chosen_keys:
            val = self.raw.get(key)
            if val:
                parts.append(str(val) if not isinstance(val, list) else str(val[0]))
        return " ".join(f"[{p}]" for p in parts)


class FileNamer:
    # ── Detection ──────────────────────────────────────────────────────
    @staticmethod
    def is_jellyfin_format(filename: str) -> bool:
        """True if file already matches Jellyfin naming (skip renaming)."""
        return bool(_JELLYFIN_FILE_RE.match(filename.strip()))

    @staticmethod
    def parse_tags(filepath: Path) -> FileTags:
        """Extract guessit metadata from a file path."""
        info = guessit(filepath.name)
        return FileTags(dict(info))

    # ── Versioning detection ────────────────────────────────────────────
    @staticmethod
    def find_video_files(folder: Path) -> list[Path]:
        """Return all video files directly inside a folder."""
        return [f for f in folder.iterdir()
                if f.is_file() and f.suffix.lower() in VIDEO_EXTS]

    @staticmethod
    def is_multi_version(folder: Path) -> bool:
        """True if folder contains more than one video file (multiple versions)."""
        return len(FileNamer.find_video_files(folder)) > 1

    # ── Formatting ─────────────────────────────────────────────────────
    @staticmethod
    def format_single(title: str, year: int | None,
                      kept_tag_values: list[str],
                      ext: str) -> str:
        """
        Build a Jellyfin-format filename.
        e.g. format_single("Inception", 2010, ["1080p", "HDR"], ".mkv")
             -> "Inception (2010) [1080p] [HDR].mkv"
        """
        base = f"{title} ({year})" if year else title
        brackets = " ".join(f"[{v}]" for v in kept_tag_values)
        name = f"{base} {brackets}".strip() if brackets else base
        return sanitize_windows_name(name) + ext

    @staticmethod
    def format_versioned(title: str, year: int | None,
                         version_label: str, ext: str) -> str:
        """
        Build a versioned Jellyfin filename:
        "Inception (2010) [1080p].mkv"
        """
        base = f"{title} ({year})" if year else title
        name = f"{base} [{version_label}]"
        return sanitize_windows_name(name) + ext

    @staticmethod
    def format_episode(show_name: str, season: int, episode: int,
                       ep_title: str = "",
                       pattern: str = "S{s:02d}E{e:02d}",
                       ext: str = ".mkv") -> str:
        """
        Format: "Show Name - S01E01 - Episode Title.mkv"
        or "Anime Name - S01E01.mkv"
        """
        se = pattern.format(s=season, e=episode)
        parts = [sanitize_windows_name(show_name), se]
        if ep_title:
            parts.append(sanitize_windows_name(ep_title))
        return " - ".join(parts) + ext
