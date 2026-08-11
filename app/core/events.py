import inspect
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


logger = logging.getLogger(__name__)

EventHandler = Callable[["Event"], Awaitable[None]]


@dataclass(frozen=True)
class Event:
    name: str
    payload: dict[str, Any]
    created_at: datetime = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class EventBus:
    """Process-local async events with deterministic listener ordering."""

    def __init__(self):
        self._listeners: dict[
            str,
            list[EventHandler],
        ] = defaultdict(list)

    def subscribe(
        self,
        event_name: str,
        handler: EventHandler,
    ) -> bool:
        self._validate_event_name(event_name)

        if not callable(handler):
            raise TypeError(
                "Event handler must be callable"
            )

        listeners = self._listeners[event_name]

        if handler in listeners:
            return False

        listeners.append(handler)

        return True

    def unsubscribe(
        self,
        event_name: str,
        handler: EventHandler,
    ) -> bool:
        listeners = self._listeners.get(event_name)

        if not listeners or handler not in listeners:
            return False

        listeners.remove(handler)

        if not listeners:
            self._listeners.pop(event_name, None)

        return True

    async def emit(
        self,
        event_name: str,
        payload: Mapping[str, Any] | None = None,
    ) -> Event:
        self._validate_event_name(event_name)

        event = Event(
            name=event_name,
            payload=dict(payload or {}),
        )
        listeners = tuple(
            self._listeners.get(event_name, ())
        )

        logger.debug(
            "Event emitted: name=%s listeners=%s",
            event_name,
            len(listeners),
        )

        for handler in listeners:
            try:
                result = handler(event)

                if not inspect.isawaitable(result):
                    raise TypeError(
                        "Event handlers must be async"
                    )

                await result
            except Exception:
                logger.exception(
                    "Event listener failed: event=%s handler=%s",
                    event_name,
                    getattr(
                        handler,
                        "__qualname__",
                        repr(handler),
                    ),
                )

        return event

    def listener_count(
        self,
        event_name: str,
    ) -> int:
        return len(
            self._listeners.get(event_name, ())
        )

    @staticmethod
    def _validate_event_name(event_name: str):
        if (
            not isinstance(event_name, str)
            or not event_name.strip()
            or "." not in event_name
        ):
            raise ValueError(
                "Event names must be namespaced strings"
            )


event_bus = EventBus()
