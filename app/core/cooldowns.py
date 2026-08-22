from time import monotonic


class CooldownActive(Exception):
    def __init__(self, retry_after: float):
        self.retry_after = max(0, retry_after)
        super().__init__(f"Try again in {self.retry_after:.1f} seconds")


class CooldownManager:
    def __init__(self, clock=monotonic, max_entries: int = 10_000):
        self.clock = clock
        self.max_entries = max_entries
        self._deadlines: dict[object, float] = {}

    def check(self, key: object, seconds: float) -> None:
        now = self.clock()
        deadline = self._deadlines.get(key, 0)
        if deadline > now:
            raise CooldownActive(deadline - now)
        if len(self._deadlines) >= self.max_entries:
            self._deadlines = {k: v for k, v in self._deadlines.items() if v > now}
        self._deadlines[key] = now + seconds

    def clear(self) -> None:
        self._deadlines.clear()
