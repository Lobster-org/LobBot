import re
from dataclasses import dataclass


@dataclass(slots=True)
class Definition:
    word: str
    definition: str
    example: str | None
    author: str | None
    thumbs_up: int
    thumbs_down: int
    url: str | None


class UrbanDictionaryProvider:
    URL = "https://api.urbandictionary.com/v0/define"
    def __init__(self, http): self.http = http
    async def search(self, term):
        data = await self.http.get_json(self.URL, params={"term": term})
        results = []
        for value in data.get("list", []) if isinstance(data, dict) else []:
            if not isinstance(value, dict) or not value.get("definition"): continue
            clean = lambda text: re.sub(r"\[([^]]+)]", r"\1", text or "").strip()
            results.append(Definition(
                word=value.get("word") or term, definition=clean(value["definition"]),
                example=clean(value.get("example")) or None, author=value.get("author"),
                thumbs_up=int(value.get("thumbs_up") or 0), thumbs_down=int(value.get("thumbs_down") or 0),
                url=value.get("permalink"),
            ))
        return results
