from dataclasses import dataclass


COMMON_LANGUAGE_ALIASES = {
    "english": "en", "amharic": "am", "spanish": "es", "japanese": "ja",
    "french": "fr", "german": "de", "italian": "it", "portuguese": "pt",
    "arabic": "ar", "korean": "ko", "chinese": "zh", "russian": "ru",
}


@dataclass(slots=True)
class TranslationResult:
    translated_text: str
    source_code: str | None
    target_code: str
    source_name: str
    target_name: str


class LibreTranslateProvider:
    def __init__(self, http, base_url, api_key=None):
        self.http = http; self.base_url = base_url.rstrip("/"); self.api_key = api_key
        self._languages = None

    async def languages(self):
        if self._languages is None:
            data = await self.http.get_json(f"{self.base_url}/languages")
            self._languages = {item["code"].casefold(): item.get("name", item["code"]) for item in data if item.get("code")}
        return self._languages

    async def resolve_language(self, value):
        languages = await self.languages(); folded = value.casefold()
        code = COMMON_LANGUAGE_ALIASES.get(folded, folded)
        if code in languages: return code
        for candidate, name in languages.items():
            if name.casefold() == folded: return candidate
        return None

    async def translate(self, text, target):
        payload = {"q": text, "source": "auto", "target": target, "format": "text"}
        if self.api_key: payload["api_key"] = self.api_key
        data = await self.http.post_json(f"{self.base_url}/translate", json=payload)
        translated = data.get("translatedText")
        if not translated: raise RuntimeError(data.get("error") or "Translation provider returned no text")
        detected = data.get("detectedLanguage") or {}
        source = detected.get("language")
        languages = await self.languages()
        return TranslationResult(translated, source, target, languages.get(source, source or "Unknown"), languages.get(target, target))
