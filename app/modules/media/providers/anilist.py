import re
from html import unescape

from app.modules.media.models import MediaItem
from app.modules.media.providers.base import MediaProvider


COUNTRIES = {"JP": "Japan", "KR": "South Korea", "CN": "China", "TW": "Taiwan"}


class AniListProvider(MediaProvider):
    URL = "https://graphql.anilist.co"
    QUERY = """
    query ($search: String!, $type: MediaType!, $country: CountryCode) {
      Page(page: 1, perPage: 50) {
        media(search: $search, type: $type, countryOfOrigin: $country,
              sort: [SEARCH_MATCH, POPULARITY_DESC]) {
          id title { romaji english native } description(asHtml: false)
          averageScore startDate { year month day } endDate { year month day }
          status genres episodes duration chapters volumes season countryOfOrigin
          coverImage { extraLarge large } siteUrl isAdult
          studios(isMain: true) { nodes { name } }
          trailer { id site }
          staff(perPage: 10) { edges { role node { name { full } } } }
        }
      }
    }
    """

    def __init__(self, http):
        self.http = http

    async def search(self, kind: str, query: str) -> list[MediaItem]:
        variables = {
            "search": query,
            "type": "ANIME" if kind == "anime" else "MANGA",
            "country": "KR" if kind == "manhwa" else None,
        }
        payload = await self.http.post_json(self.URL, json={"query": self.QUERY, "variables": variables})
        if payload.get("errors"):
            raise RuntimeError(payload["errors"][0].get("message", "AniList request failed"))
        records = payload.get("data", {}).get("Page", {}).get("media", []) or []
        return [self._item(kind, value) for value in records if isinstance(value, dict)]

    @classmethod
    def _item(cls, kind, value):
        title = value.get("title") or {}
        cover = value.get("coverImage") or {}
        studios = ((value.get("studios") or {}).get("nodes") or [])
        trailer = value.get("trailer") or {}
        trailer_url = None
        if trailer.get("site") == "youtube" and trailer.get("id"):
            trailer_url = f"https://youtu.be/{trailer['id']}"
        authors = []
        for edge in ((value.get("staff") or {}).get("edges") or []):
            role = (edge.get("role") or "").lower()
            name = (((edge.get("node") or {}).get("name") or {}).get("full"))
            if name and ("story" in role or "original creator" in role or "art" in role):
                authors.append(name)
        return MediaItem(
            id=str(value.get("id")), kind=kind,
            title=title.get("english") or title.get("romaji") or title.get("native") or "Untitled",
            english_title=title.get("english"), native_title=title.get("native"),
            description=cls._plain(value.get("description")),
            score=(value.get("averageScore") / 10 if value.get("averageScore") is not None else None),
            rating_source="AniList", start_date=cls._date(value.get("startDate")),
            end_date=cls._date(value.get("endDate")), status=(value.get("status") or "").replace("_", " ").title() or None,
            genres=value.get("genres") or [], episodes=value.get("episodes"), duration_minutes=value.get("duration"),
            chapters=value.get("chapters"), volumes=value.get("volumes"), season=(value.get("season") or "").title() or None,
            studio=studios[0].get("name") if studios else None,
            country=COUNTRIES.get(value.get("countryOfOrigin"), value.get("countryOfOrigin")),
            content_rating="Adult" if value.get("isAdult") else None,
            poster_url=cover.get("extraLarge") or cover.get("large"), trailer_url=trailer_url,
            info_url=value.get("siteUrl"), metadata={"authors": list(dict.fromkeys(authors))[:5]},
        )

    @staticmethod
    def _plain(value):
        if not value:
            return None
        return unescape(re.sub(r"<[^>]+>", "", value)).strip()

    @staticmethod
    def _date(value):
        if not value or not value.get("year"):
            return None
        parts = [str(value["year"])]
        if value.get("month"):
            parts.append(f"{value['month']:02d}")
        if value.get("day"):
            parts.append(f"{value['day']:02d}")
        return "-".join(parts)
