import logging
import time

from app.modules.music.models.search import (
    SearchSession,
)

from app.modules.music.models.track import Track


logger = logging.getLogger(__name__)


class SearchSessionManager:

    def __init__(
        self,
        ttl: int = 120,
    ):

        self.ttl = ttl

        self.sessions: dict[
            tuple[int, int],
            SearchSession,
        ] = {}

    def create(
        self,
        user_id: int,
        chat_id: int,
        tracks: list[Track],
    ):

        self._delete_expired()

        session = SearchSession(
            user_id=user_id,
            chat_id=chat_id,
            tracks=tracks,
            created_at=time.time(),
        )

        key = (
            user_id,
            chat_id,
        )

        self.sessions[key] = session

        logger.debug(
            "Music search session created: user=%s chat=%s",
            user_id,
            chat_id,
        )

    def get(
        self,
        user_id: int,
        chat_id: int,
    ) -> SearchSession | None:

        key = (
            user_id,
            chat_id,
            )

        session = self.sessions.get(
            key
        )

        if not session:
            return None

        if (
            time.time()
            - session.created_at
            > self.ttl
        ):

            del self.sessions[key]

            return None

        return session

    def delete(
        self,
        user_id: int,
        chat_id: int,
    ):

        self.sessions.pop(
            (user_id, chat_id),
            None,
        )

    def _delete_expired(self):
        now = time.time()
        expired = [
            key
            for key, session in self.sessions.items()
            if now - session.created_at > self.ttl
        ]

        for key in expired:
            self.sessions.pop(key, None)
