from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.core.cache import TTLCache
from app.core.cooldowns import CooldownActive, CooldownManager
from app.core.events import EventBus
from app.core.pagination import PaginationStore
from app.modules.afk.service import AFKService
from app.modules.dictionary.module import DictionaryService
from app.modules.dictionary.provider import UrbanDictionaryProvider
from app.modules.media.providers.anilist import AniListProvider
from app.modules.media.providers.tmdb import TMDBProvider
from app.modules.media.service import MediaService
from app.modules.media.handlers import owned_session
from app.modules.reactions.module import ReactionService
from app.modules.reactions.provider import NekosBestReactionProvider
from app.modules.translation.module import TranslationService
from app.modules.translation.provider import LibreTranslateProvider, TranslationResult


class HTTP:
    def __init__(self, response): self.response = response; self.calls = []
    async def get_json(self, url, **kwargs): self.calls.append(("get", url, kwargs)); return self.response
    async def post_json(self, url, **kwargs): self.calls.append(("post", url, kwargs)); return self.response


def test_pagination_is_bounded_owner_scoped_and_expires():
    now = [datetime.now(timezone.utc)]
    store = PaginationStore(ttl_seconds=10, max_sessions=2, clock=lambda: now[0])
    first = store.create(1, -100, "test", list(range(15)), page_size=10)
    assert first.owner_id == 1 and first.total_pages == 2 and first.page(1) == list(range(10, 15))
    assert store.get(first.id, chat_id=-200) is None
    second = store.create(2, -100, "test", [])
    now[0] += timedelta(seconds=11)
    assert store.get(second.id) is None


def test_media_callback_session_rejects_wrong_user_and_expiration():
    store = PaginationStore(ttl_seconds=60)
    session = store.create(1, -100, "anime", ["result"])
    service = SimpleNamespace(pagination=store)
    callback = SimpleNamespace(
        from_user=SimpleNamespace(id=2),
        message=SimpleNamespace(chat=SimpleNamespace(id=-100)),
    )
    found, error = owned_session(callback, service, session.id)
    assert found is None and error == "This search belongs to another user."
    store.delete(session.id)
    found, error = owned_session(callback, service, session.id)
    assert found is None and "expired" in error


def test_ttl_cache_evicts_oldest_and_cooldown_is_deterministic():
    clock = [0.0]; cache = TTLCache(max_size=1, ttl_seconds=5, clock=lambda: clock[0])
    cache.set("a", 1); cache.set("b", 2)
    assert cache.get("a") is None and cache.get("b") == 2
    cooldown = CooldownManager(clock=lambda: clock[0]); cooldown.check("u", 2)
    with pytest.raises(CooldownActive): cooldown.check("u", 2)


@pytest.mark.asyncio
async def test_anilist_search_normalizes_metadata_and_manhwa_origin():
    http = HTTP({"data": {"Page": {"media": [{
        "id": 1, "title": {"english": "Naruto", "romaji": "Naruto", "native": "ナルト"},
        "description": "A <b>ninja</b> story", "averageScore": 80,
        "startDate": {"year": 2002, "month": 10, "day": 3}, "endDate": {},
        "genres": ["Action"], "coverImage": {}, "studios": {"nodes": [{"name": "Pierrot"}]},
        "staff": {"edges": []}, "countryOfOrigin": "JP", "siteUrl": "https://anilist.co/anime/1",
    }]}}})
    provider = AniListProvider(http)
    result = await provider.search("anime", "naruto")
    assert result[0].title == "Naruto" and result[0].score == 8 and result[0].rating_source == "AniList"
    assert result[0].description == "A ninja story"
    await provider.search("manhwa", "solo leveling")
    assert http.calls[-1][2]["json"]["variables"]["country"] == "KR"


@pytest.mark.asyncio
async def test_tmdb_requires_token_and_labels_rating_tmdb():
    provider = TMDBProvider(HTTP({}), None)
    with pytest.raises(RuntimeError, match="TMDB_BEARER_TOKEN"):
        await provider.search("movie", "Interstellar")
    http = HTTP({"results": [{"id": 1, "title": "Interstellar", "vote_average": 8.7}], "total_pages": 1})
    item = (await TMDBProvider(http, "token").search("movie", "Interstellar"))[0]
    assert item.rating_source == "TMDB" and item.score == 8.7


@pytest.mark.asyncio
async def test_media_service_search_emits_event_and_uses_cache():
    class Provider:
        def __init__(self): self.calls = 0
        async def search(self, kind, query): self.calls += 1; return [SimpleNamespace(id="1", kind=kind)]
    provider = Provider(); events = EventBus(); received = []
    async def listener(event): received.append(event)
    events.subscribe("media.searched", listener)
    service = MediaService(provider, provider, events, PaginationStore())
    one = await service.search("anime", "naruto", -100, 1)
    service.cooldowns.clear()
    two = await service.search("anime", "Naruto", -100, 1)
    assert provider.calls == 1 and one.items and two.items and received[-1].payload["result_count"] == 1


@pytest.mark.asyncio
async def test_dictionary_cleans_brackets_and_handles_malformed_response():
    provider = UrbanDictionaryProvider(HTTP({"list": [{"word": "cooked", "definition": "[hopeless]", "example": "He's [cooked].", "thumbs_up": 2}]}))
    item = (await provider.search("cooked"))[0]
    assert item.definition == "hopeless" and item.example == "He's cooked."
    assert await UrbanDictionaryProvider(HTTP({"unexpected": True})).search("x") == []


@pytest.mark.asyncio
async def test_translation_parsing_direct_reply_and_explicit_target():
    class Provider:
        async def resolve_language(self, value): return {"es": "es", "spanish": "es"}.get(value.casefold())
        async def translate(self, text, target): return TranslationResult("Hola", "en", target, "English", "Spanish")
    service = TranslationService(Provider(), EventBus())
    assert await service.parse("es Hello", None) == ("es", "Hello")
    assert await service.parse("", "Hello") == ("en", "Hello")
    with pytest.raises(ValueError, match="command"): await service.parse("/ban user", None)
    result = await service.translate("Hello", "es", -100, 1)
    assert result.translated_text == "Hola"
    assert service.chunks("abcdefgh", 3) == ["abc", "def", "gh"]


class AFKRepo:
    def __init__(self): self.records = {}; self.mentions = []
    async def set(self, chat_id, user, status, reason):
        value = {"chat_id": chat_id, "user_id": user.id, "status": status, "reason": reason, "started_at": datetime.now(timezone.utc), "mentions": [], "display_name": user.full_name}
        self.records[(chat_id, user.id)] = value; return value
    async def get(self, chat_id, user_id): return self.records.get((chat_id, user_id))
    async def clear(self, chat_id, user_id): return self.records.pop((chat_id, user_id), None)
    async def add_mention(self, chat_id, user_id, mention): self.mentions.append(mention); return self.records.get((chat_id, user_id))


@pytest.mark.asyncio
async def test_afk_activation_mention_cooldown_and_clearing():
    repo = AFKRepo(); monotonic = [0.0]; service = AFKService(repo, EventBus(), monotonic_clock=lambda: monotonic[0])
    user = SimpleNamespace(id=2, full_name="Away", username="away")
    await service.start(-100, user, "brb", "food")
    message = SimpleNamespace(chat=SimpleNamespace(id=-100), from_user=SimpleNamespace(id=1, full_name="Alex"), message_id=5, text="hi", caption=None)
    record = await repo.get(-100, 2)
    assert await service.mention(message, record) is True
    assert await service.mention(message, record) is False
    assert len(repo.mentions) == 2
    assert (await service.end(-100, 2))["reason"] == "food"


@pytest.mark.asyncio
async def test_reaction_provider_validation_and_service_event():
    provider = NekosBestReactionProvider(HTTP({"results": [{"url": "https://example.com/pat.gif"}]}))
    events = EventBus(); received = []
    async def listener(event): received.append(event)
    events.subscribe("reaction.sent", listener)
    service = ReactionService(provider, None, events, None)
    media = await service.send("pat", -100, 1, 2)
    assert media.url.endswith("pat.gif") and received[0].payload["target_user_id"] == 2
    invalid = NekosBestReactionProvider(HTTP({"results": [{"url": "file:///tmp/pat.gif"}]}))
    with pytest.raises(RuntimeError, match="invalid media"):
        await invalid.random("pat")
