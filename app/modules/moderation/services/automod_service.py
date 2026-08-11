import asyncio
import logging
import re
from collections import defaultdict, deque
from time import monotonic

from app.core.permissions import Role
from app.modules.moderation.events import AUTOMOD_VIOLATION
from app.modules.moderation.models.automod import (
    AUTOMOD_RULES,
    AutomodConfig,
)


logger = logging.getLogger(__name__)

LINK_PATTERN = re.compile(
    r"(?:https?://|www\.|t\.me/|telegram\.me/)",
    re.IGNORECASE,
)


class AutomodService:
    CACHE_SECONDS = 60
    HISTORY_RETENTION_SECONDS = 60

    def __init__(
        self,
        repository,
        moderation_service,
        bot,
        events,
    ):
        self.repository = repository
        self.moderation = moderation_service
        self.bot = bot
        self.events = events
        self._configs: dict[int, tuple[float, AutomodConfig]] = {}
        self._flood: dict[tuple[int, int], deque[float]] = defaultdict(deque)
        self._repeat: dict[
            tuple[int, int], deque[tuple[float, str]]
        ] = defaultdict(deque)
        self._lock = asyncio.Lock()
        self._last_cleanup = monotonic()

    async def get_config(
        self,
        chat_id: int,
        refresh: bool = False,
    ) -> AutomodConfig:
        now = monotonic()
        cached = self._configs.get(chat_id)
        if not refresh and cached and cached[0] > now:
            return cached[1]

        config = AutomodConfig.from_document(
            await self.repository.get_config(chat_id)
        )
        self._configs[chat_id] = (now + self.CACHE_SECONDS, config)
        return config

    async def set_enabled(self, chat_id: int, enabled: bool):
        config = await self.get_config(chat_id)
        config.enabled = bool(enabled)
        await self._save(chat_id, config)
        return config

    async def set_rule(
        self,
        chat_id: int,
        rule: str,
        enabled: bool,
    ) -> AutomodConfig:
        if rule not in AUTOMOD_RULES:
            raise ValueError("Unknown automod rule")
        config = await self.get_config(chat_id)
        config.rules[rule] = bool(enabled)
        await self._save(chat_id, config)
        return config

    async def add_word(self, chat_id: int, word: str) -> bool:
        normalized = word.strip().casefold()
        if not normalized or len(normalized) > 100:
            raise ValueError("Blocked words must contain 1-100 characters")
        config = await self.get_config(chat_id)
        if normalized in config.blocked_words:
            return False
        config.blocked_words.append(normalized)
        config.blocked_words.sort()
        await self._save(chat_id, config)
        return True

    async def remove_word(self, chat_id: int, word: str) -> bool:
        normalized = word.strip().casefold()
        config = await self.get_config(chat_id)
        if normalized not in config.blocked_words:
            return False
        config.blocked_words.remove(normalized)
        await self._save(chat_id, config)
        return True

    async def inspect_message(self, message, permission_service):
        if (
            not message.from_user
            or message.from_user.is_bot
            or message.chat.type not in {"group", "supergroup"}
        ):
            return None

        role = await permission_service.get_role(
            message.chat.id,
            message.from_user.id,
        )
        if role != Role.MEMBER:
            return None

        config = await self.get_config(message.chat.id)
        if not config.enabled:
            return None

        text = (message.text or message.caption or "").strip()
        if not text:
            return None

        violation = await self._detect(
            message.chat.id,
            message.from_user.id,
            text,
            config,
        )
        if not violation:
            return None

        try:
            await self.bot.delete_message(
                chat_id=message.chat.id,
                message_id=message.message_id,
            )
        except Exception:
            logger.exception(
                "Automod could not delete message: chat=%s user=%s "
                "message=%s rule=%s",
                message.chat.id,
                message.from_user.id,
                message.message_id,
                violation,
            )

        reason = f"Automod: {violation}"
        await self.moderation.warn(
            message.chat.id,
            message.from_user.id,
            self.bot.id,
            reason,
        )
        warning_count = await self.moderation.warning_count(
            message.chat.id,
            message.from_user.id,
        )
        consequence = "deleted_and_warned"

        if warning_count >= config.warning_threshold:
            try:
                await self.moderation.mute(
                    message.chat.id,
                    message.from_user.id,
                    self.bot.id,
                    config.mute_duration_seconds,
                    f"Automod escalation after {warning_count} warnings",
                )
            except Exception:
                logger.exception(
                    "Automod escalation failed: chat=%s user=%s",
                    message.chat.id,
                    message.from_user.id,
                )
            else:
                await self.moderation.resolve_warnings(
                    message.chat.id,
                    message.from_user.id,
                    self.bot.id,
                )
                consequence = "muted"

        await self.events.emit(
            AUTOMOD_VIOLATION,
            {
                "chat_id": message.chat.id,
                "user_id": message.from_user.id,
                "moderator_id": self.bot.id,
                "action": "automod",
                "rule": violation,
                "reason": reason,
                "warning_count": warning_count,
                "consequence": consequence,
                "message_id": message.message_id,
            },
        )
        return violation

    async def _detect(
        self,
        chat_id: int,
        user_id: int,
        text: str,
        config: AutomodConfig,
    ) -> str | None:
        folded = text.casefold()

        if config.rules["words"] and any(
            re.search(
                rf"(?<!\w){re.escape(word)}(?!\w)",
                folded,
            )
            for word in config.blocked_words
        ):
            return "blocked_word"

        if config.rules["links"] and LINK_PATTERN.search(text):
            return "link"

        letters = [character for character in text if character.isalpha()]
        if (
            config.rules["caps"]
            and len(letters) >= config.caps_min_letters
            and sum(character.isupper() for character in letters)
            / len(letters)
            >= config.caps_ratio
        ):
            return "caps"

        now = monotonic()
        key = (chat_id, user_id)

        async with self._lock:
            self._cleanup(now)

            if config.rules["repeat"]:
                repeat = self._repeat[key]
                cutoff = now - config.repeat_window_seconds
                while repeat and repeat[0][0] < cutoff:
                    repeat.popleft()
                repeat.append((now, folded))
                if sum(value == folded for _, value in repeat) >= config.repeat_limit:
                    repeat.clear()
                    return "repeated_message"

            if config.rules["flood"]:
                flood = self._flood[key]
                cutoff = now - config.flood_window_seconds
                while flood and flood[0] < cutoff:
                    flood.popleft()
                flood.append(now)
                if len(flood) >= config.flood_limit:
                    flood.clear()
                    return "flood"

        return None

    def _cleanup(self, now: float):
        if now - self._last_cleanup < self.HISTORY_RETENTION_SECONDS:
            return
        cutoff = now - self.HISTORY_RETENTION_SECONDS
        self._flood = defaultdict(
            deque,
            {
                key: values
                for key, values in self._flood.items()
                if values and values[-1] >= cutoff
            },
        )
        self._repeat = defaultdict(
            deque,
            {
                key: values
                for key, values in self._repeat.items()
                if values and values[-1][0] >= cutoff
            },
        )
        self._last_cleanup = now

    async def _save(self, chat_id: int, config: AutomodConfig):
        await self.repository.set_config(chat_id, config.to_document())
        self._configs[chat_id] = (
            monotonic() + self.CACHE_SECONDS,
            config,
        )

    def clear(self):
        self._configs.clear()
        self._flood.clear()
        self._repeat.clear()
