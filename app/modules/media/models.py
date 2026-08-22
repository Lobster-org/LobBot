from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class MediaItem:
    id: str
    kind: str
    title: str
    english_title: str | None = None
    native_title: str | None = None
    description: str | None = None
    score: float | None = None
    rating_source: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    status: str | None = None
    genres: list[str] = field(default_factory=list)
    episodes: int | None = None
    duration_minutes: int | None = None
    chapters: int | None = None
    volumes: int | None = None
    season: str | None = None
    studio: str | None = None
    country: str | None = None
    content_rating: str | None = None
    runtime_minutes: int | None = None
    director: str | None = None
    cast: list[str] = field(default_factory=list)
    seasons: int | None = None
    poster_url: str | None = None
    trailer_url: str | None = None
    info_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
