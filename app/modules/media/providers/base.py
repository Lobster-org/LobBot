from abc import ABC, abstractmethod


class MediaProvider(ABC):
    @abstractmethod
    async def search(self, kind: str, query: str) -> list:
        raise NotImplementedError

    async def details(self, kind: str, item_id: str):
        raise NotImplementedError
