"""
AniList GraphQL client — anime search + episode titles. No API key needed.
"""
from __future__ import annotations
import requests
from api.tmdb import Candidate

ANILIST_URL = "https://graphql.anilist.co"

_SEARCH_QUERY = """
query ($search: String) {
  Page(perPage: 6) {
    media(search: $search, type: ANIME) {
      id
      title { romaji english native }
      startDate { year }
      coverImage { medium }
      format
      episodes
    }
  }
}
"""

_EPISODE_QUERY = """
query ($id: Int, $ep: Int) {
  AiringSchedule(mediaId: $id, episode: $ep) { episode airingAt }
}
"""


class AniListClient:
    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    def _post(self, query: str, variables: dict) -> dict:
        r = self._session.post(ANILIST_URL,
                               json={"query": query, "variables": variables},
                               timeout=8)
        r.raise_for_status()
        return r.json()

    def search_anime(self, title: str) -> list[Candidate]:
        try:
            data = self._post(_SEARCH_QUERY, {"search": title})
            out  = []
            for m in data["data"]["Page"]["media"]:
                english = m["title"]["english"] or ""
                romaji  = m["title"]["romaji"]  or ""
                name    = english or romaji
                yr      = (m.get("startDate") or {}).get("year")
                cover   = (m.get("coverImage") or {}).get("medium")
                out.append(Candidate(
                    name=name, year=yr, media_type="anime",
                    tmdb_id=m.get("id"),
                    poster_url=cover,
                    source="anilist",
                    extra={"romaji": romaji, "episodes": m.get("episodes")},
                ))
            return out
        except Exception:
            return []
