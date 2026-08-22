import logging
from typing import Any

import aiohttp


logger = logging.getLogger(__name__)


class HttpClient:
    """Application-owned HTTP client used by external API providers."""

    def __init__(self, *, user_agent: str, timeout_seconds: float = 12):
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self._session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        if self._session and not self._session.closed:
            return
        timeout = aiohttp.ClientTimeout(
            total=self.timeout_seconds,
            connect=min(5, self.timeout_seconds),
            sock_read=self.timeout_seconds,
        )
        self._session = aiohttp.ClientSession(
            timeout=timeout,
            headers={"User-Agent": self.user_agent},
        )
        logger.info("Shared HTTP client ready")

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None
        logger.info("Shared HTTP client closed")

    @property
    def session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            raise RuntimeError("HTTP client has not been started")
        return self._session

    async def get_json(self, url: str, **kwargs) -> Any:
        async with self.session.get(url, **kwargs) as response:
            response.raise_for_status()
            return await response.json(content_type=None)

    async def post_json(self, url: str, **kwargs) -> Any:
        async with self.session.post(url, **kwargs) as response:
            response.raise_for_status()
            return await response.json(content_type=None)
