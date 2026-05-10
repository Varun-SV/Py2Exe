"""
AniDB client — supplementary anime + episode data.
AniDB's HTTP API requires a registered client ID.
Client must be registered at: https://anidb.net/software/add

Without registration the ban rate is very aggressive.
This client is used only for episode title fallback when AniList
doesn't have the data.
"""
from __future__ import annotations
import xml.etree.ElementTree as ET
import requests

ANIDB_URL = "http://api.anidb.net:9001/httpapi"


class AniDBClient:
    def __init__(self, client: str = "jellyfinorganizer",
                 client_ver: int = 1) -> None:
        self._client  = client
        self._ver     = client_ver
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": f"{client}/{client_ver}"})

    def _params(self, **extra) -> dict:
        return {"client": self._client, "clientver": self._ver,
                "protover": 1, **extra}

    def search_anime(self, title: str) -> list[dict]:
        """Search AniDB for an anime by title. Returns basic info dicts."""
        try:
            r = self._session.get(ANIDB_URL,
                params=self._params(request="anime", adb_request="search",
                                    pagelen=6, query=title),
                timeout=10)
            r.raise_for_status()
            root = ET.fromstring(r.text)
            results = []
            for anime in root.findall(".//anime"):
                results.append({
                    "aid":   anime.get("id"),
                    "title": anime.findtext("titles/title[@xml:lang=\'en\']") or
                             anime.findtext("titles/title") or "",
                })
            return results
        except Exception:
            return []

    def get_episode_title(self, aid: int, episode_num: int) -> str:
        """Fetch an episode title from AniDB by anime ID and episode number."""
        try:
            r = self._session.get(ANIDB_URL,
                params=self._params(request="anime", aid=aid),
                timeout=10)
            r.raise_for_status()
            root = ET.fromstring(r.text)
            for ep in root.findall(".//episode"):
                epno_el = ep.find("epno")
                if epno_el is not None and epno_el.text == str(episode_num):
                    title = ep.findtext("title[@xml:lang=\'en\']") or ep.findtext("title") or ""
                    return title
        except Exception:
            pass
        return ""
