from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.modules.music.models.track import Track


@dataclass
class QueueItem:

    track: Track

    requested_by: int

    requested_at: datetime = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


@dataclass
class MusicQueue:

    chat_id: int

    items: list[QueueItem] = field(
        default_factory=list
    )

    current: QueueItem | None = None

    is_playing: bool = False

    is_paused: bool = False

    def add(
        self,
        item: QueueItem,
    ) -> int:

        self.items.append(item)

        return len(self.items)

    def next(self) -> QueueItem | None:

        if not self.items:

            self.current = None

            return None

        self.current = self.items.pop(0)
        self.is_paused = False

        return self.current

    def clear(self):

        self.items.clear()

        self.current = None

        self.is_playing = False
        self.is_paused = False

    def remove(
        self,
        index: int,
    ) -> QueueItem | None:

        if (
            index < 0
            or index >= len(self.items)
        ):
            return None

        return self.items.pop(index)

    def __len__(self):

        return len(self.items)
