from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.core.events import EventBus, event_bus
from app.database.mongodb import MongoDB, mongodb


@dataclass
class AppContainer:
    """Application-owned runtime dependencies shared with modules."""

    settings: Any
    mongodb: MongoDB
    event_bus: EventBus
    database: Any = None
    voice_lifecycle: Any = None
    voice_service: Any = None

    def set_database(self, database: Any) -> None:
        self.database = database

    def clear_runtime(self) -> None:
        self.database = None
        self.voice_lifecycle = None
        self.voice_service = None


def create_container() -> AppContainer:
    """Create references only; network resources start in app.main."""

    return AppContainer(
        settings=settings,
        mongodb=mongodb,
        event_bus=event_bus,
    )


container = create_container()
