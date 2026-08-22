from datetime import datetime, timezone
from time import monotonic


class AFKService:
    def __init__(self, repository, events, clock=None, monotonic_clock=monotonic):
        self.repository, self.events = repository, events; self.clock = clock or (lambda: datetime.now(timezone.utc)); self.monotonic = monotonic_clock
        self._notifications = {}; self.notification_cooldown = 30
    async def start(self, chat_id, user, status, reason):
        record = await self.repository.set(chat_id, user, status, reason)
        await self.events.emit("afk.started", {"chat_id": chat_id, "user_id": user.id, "status": status, "has_reason": bool(reason)})
        return record
    async def end(self, chat_id, user_id):
        record = await self.repository.clear(chat_id, user_id)
        if record: await self.events.emit("afk.ended", {"chat_id": chat_id, "user_id": user_id, "seconds_away": self.elapsed_seconds(record)})
        return record
    async def targets(self, message):
        found = {}
        reply_user = getattr(getattr(message, "reply_to_message", None), "from_user", None)
        if reply_user and not reply_user.is_bot:
            record = await self.repository.get(message.chat.id, reply_user.id)
            if record: found[reply_user.id] = record
        for entity in getattr(message, "entities", None) or []:
            kind = getattr(entity.type, "value", entity.type)
            if kind == "text_mention" and entity.user:
                record = await self.repository.get(message.chat.id, entity.user.id)
            elif kind == "mention":
                username = entity.extract_from(message.text or "").lstrip("@")
                record = await self.repository.find_username(message.chat.id, username)
            else: continue
            if record: found[record["user_id"]] = record
        return list(found.values())
    async def mention(self, message, record):
        key = (message.chat.id, message.from_user.id, record["user_id"]); now = self.monotonic()
        notify = self._notifications.get(key, 0) <= now
        if notify: self._notifications[key] = now + self.notification_cooldown
        snippet = (message.text or message.caption or "")[:300]
        await self.repository.add_mention(message.chat.id, record["user_id"], {
            "from_user_id": message.from_user.id, "from_name": message.from_user.full_name,
            "message_id": message.message_id, "snippet": snippet, "created_at": self.clock(),
        })
        await self.events.emit("afk.user_mentioned", {"chat_id": message.chat.id, "user_id": record["user_id"], "mentioned_by": message.from_user.id})
        return notify
    def elapsed_seconds(self, record):
        started = record.get("started_at") or self.clock()
        if started.tzinfo is None: started = started.replace(tzinfo=timezone.utc)
        return max(0, int((self.clock() - started).total_seconds()))
    @staticmethod
    def duration(seconds):
        if seconds < 60: return f"{seconds} seconds"
        if seconds < 3600: return f"{seconds // 60} minutes"
        if seconds < 86400: return f"{seconds // 3600} hours"
        return f"{seconds // 86400} days"
    def shutdown(self): self._notifications.clear()
