from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(slots=True)
class ReactionMedia:
    url: str
    source_url: str | None = None
    artist: str | None = None


class NekosBestReactionProvider:
    BASE = "https://nekos.best/api/v2"
    SUPPORTED = {"pat"}
    def __init__(self, http): self.http = http
    async def random(self, reaction):
        if reaction not in self.SUPPORTED: raise ValueError("Unsupported reaction")
        data = await self.http.get_json(f"{self.BASE}/{reaction}")
        result = next(iter(data.get("results") or []), None)
        if not result or not self._safe_url(result.get("url")): raise RuntimeError("Reaction provider returned invalid media")
        return ReactionMedia(result["url"], result.get("source_url"), result.get("artist_name"))
    @staticmethod
    def _safe_url(value):
        parsed = urlparse(value or "")
        return parsed.scheme == "https" and bool(parsed.netloc)
