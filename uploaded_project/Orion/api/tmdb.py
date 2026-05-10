"""
TMDb API client — movies, TV shows, episode titles, poster URLs.
"""
from __future__ import annotations
import requests
from dataclasses import dataclass, field

TMDB_BASE   = "https://api.themoviedb.org/3"
POSTER_BASE = "https://image.tmdb.org/t/p/w185"


@dataclass
class Candidate:
    name:       str
    year:       int | None
    media_type: str          # 'movie' | 'tv' | 'anime'
    tmdb_id:    int | None   = None
    poster_url: str | None   = None
    source:     str          = "tmdb"
    extra:      dict         = field(default_factory=dict)

    def display(self, with_year: bool = True) -> str:
        if with_year and self.year:
            return f"{self.name} ({self.year})"
        return self.name


class TMDbClient:
    def __init__(self, api_key: str) -> None:
        self._key = api_key
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    def _get(self, endpoint: str, params: dict) -> dict:
        params["api_key"] = self._key
        params["language"] = "en-US"
        r = self._session.get(f"{TMDB_BASE}/{endpoint}", params=params, timeout=8)
        r.raise_for_status()
        return r.json()

    def search_movie(self, title: str, year: int | None = None) -> list[Candidate]:
        if not self._key:
            return []
        params: dict = {"query": title}
        if year:
            params["year"] = year
        try:
            data = self._get("search/movie", params)
            out  = []
            for item in data.get("results", [])[:6]:
                name   = item.get("title") or item.get("original_title", "")
                date   = item.get("release_date", "")
                yr     = int(date[:4]) if date else None
                poster = item.get("poster_path")
                out.append(Candidate(
                    name=name, year=yr, media_type="movie",
                    tmdb_id=item.get("id"),
                    poster_url=f"{POSTER_BASE}{poster}" if poster else None,
                ))
            return out
        except Exception:
            return []

    def search_tv(self, title: str, year: int | None = None) -> list[Candidate]:
        if not self._key:
            return []
        params: dict = {"query": title}
        if year:
            params["first_air_date_year"] = year
        try:
            data = self._get("search/tv", params)
            out  = []
            for item in data.get("results", [])[:6]:
                name   = item.get("name") or item.get("original_name", "")
                date   = item.get("first_air_date", "")
                yr     = int(date[:4]) if date else None
                poster = item.get("poster_path")
                out.append(Candidate(
                    name=name, year=yr, media_type="tv",
                    tmdb_id=item.get("id"),
                    poster_url=f"{POSTER_BASE}{poster}" if poster else None,
                ))
            return out
        except Exception:
            return []

    def get_episode_title(self, show_id: int, season: int, episode: int) -> str:
        """Fetch a single episode title from TMDb."""
        if not self._key:
            return ""
        try:
            data = self._get(f"tv/{show_id}/season/{season}/episode/{episode}", {})
            return data.get("name", "")
        except Exception:
            return ""

    def validate_key(self) -> bool:
        if not self._key:
            return False
        try:
            self._get("configuration", {})
            return True
        except Exception:
            return False
