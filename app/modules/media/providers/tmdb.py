from app.modules.media.models import MediaItem
from app.modules.media.providers.base import MediaProvider


class TMDBProvider(MediaProvider):
    BASE = "https://api.themoviedb.org/3"
    IMAGE = "https://image.tmdb.org/t/p/w780"

    def __init__(self, http, token: str | None):
        self.http = http
        self.token = token

    @property
    def headers(self):
        if not self.token:
            raise RuntimeError("TMDB_BEARER_TOKEN is not configured")
        return {"Authorization": f"Bearer {self.token}"}

    async def search(self, kind: str, query: str) -> list[MediaItem]:
        media_type = "movie" if kind == "movie" else "tv"
        items = []
        for page in range(1, 6):
            data = await self.http.get_json(
                f"{self.BASE}/search/{media_type}", headers=self.headers,
                params={"query": query, "page": page, "include_adult": "false"},
            )
            for value in data.get("results", []):
                title = value.get("title") or value.get("name") or "Untitled"
                date = value.get("release_date") or value.get("first_air_date")
                items.append(MediaItem(
                    id=str(value.get("id")), kind=kind, title=title,
                    description=value.get("overview"),
                    score=value.get("vote_average") or None, rating_source="TMDB",
                    start_date=date or None,
                    poster_url=self.IMAGE + value["poster_path"] if value.get("poster_path") else None,
                    info_url=f"https://www.themoviedb.org/{media_type}/{value.get('id')}",
                ))
            if page >= int(data.get("total_pages", 1)):
                break
        return items

    async def details(self, kind: str, item_id: str) -> MediaItem:
        media_type = "movie" if kind == "movie" else "tv"
        value = await self.http.get_json(
            f"{self.BASE}/{media_type}/{item_id}", headers=self.headers,
            params={"append_to_response": "credits,videos,external_ids,content_ratings,release_dates"},
        )
        credits = value.get("credits") or {}
        crew = credits.get("crew") or []
        director = next((person.get("name") for person in crew if person.get("job") == "Director"), None)
        videos = (value.get("videos") or {}).get("results") or []
        trailer = next((video for video in videos if video.get("site") == "YouTube" and video.get("type") == "Trailer"), None)
        certification = self._certification(kind, value)
        return MediaItem(
            id=str(value.get("id")), kind=kind,
            title=value.get("title") or value.get("name") or "Untitled",
            native_title=value.get("original_title") or value.get("original_name"),
            description=value.get("overview"), score=value.get("vote_average") or None,
            rating_source="TMDB", start_date=value.get("release_date") or value.get("first_air_date"),
            end_date=value.get("last_air_date"), status=value.get("status"),
            genres=[genre.get("name") for genre in value.get("genres", []) if genre.get("name")],
            runtime_minutes=value.get("runtime") or next(iter(value.get("episode_run_time") or []), None),
            director=director, cast=[person.get("name") for person in (credits.get("cast") or [])[:5] if person.get("name")],
            seasons=value.get("number_of_seasons"), episodes=value.get("number_of_episodes"),
            country=", ".join(value.get("origin_country") or [c.get("name") for c in value.get("production_countries", [])]) or None,
            content_rating=certification,
            poster_url=self.IMAGE + value["poster_path"] if value.get("poster_path") else None,
            trailer_url=f"https://youtu.be/{trailer['key']}" if trailer else None,
            info_url=f"https://www.themoviedb.org/{media_type}/{value.get('id')}",
        )

    @staticmethod
    def _certification(kind, value):
        key = "release_dates" if kind == "movie" else "content_ratings"
        for country in (value.get(key) or {}).get("results", []):
            if country.get("iso_3166_1") != "US":
                continue
            if kind == "movie":
                return next((item.get("certification") for item in country.get("release_dates", []) if item.get("certification")), None)
            return country.get("rating")
        return None
