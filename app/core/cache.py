from collections import OrderedDict
from dataclasses import dataclass
from time import monotonic
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass(slots=True)
class _CacheEntry(Generic[T]):
    value: T
    expires_at: float


class TTLCache(Generic[T]):
    """Small bounded process-local TTL/LRU cache."""

    def __init__(self, max_size: int = 256, ttl_seconds: float = 300, clock=monotonic):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.clock = clock
        self._items: OrderedDict[object, _CacheEntry[T]] = OrderedDict()

    def get(self, key: object) -> T | None:
        entry = self._items.get(key)
        if not entry:
            return None
        if entry.expires_at <= self.clock():
            self._items.pop(key, None)
            return None
        self._items.move_to_end(key)
        return entry.value

    def set(self, key: object, value: T) -> None:
        self._items[key] = _CacheEntry(value, self.clock() + self.ttl_seconds)
        self._items.move_to_end(key)
        while len(self._items) > self.max_size:
            self._items.popitem(last=False)

    def clear(self) -> None:
        self._items.clear()
