from abc import ABC, abstractmethod


class BaseModule(ABC):

    name: str = "unknown"
    version: str = "1.0.0"
    description: str = ""
    enabled_by_default: bool = False
    core: bool = False

    @abstractmethod
    async def setup(self, container, dispatcher):
        """
        Register commands,
        handlers, listeners.
        """
        pass


    async def startup(self, container):
        """
        Runs when module loads.
        """
        pass


    async def shutdown(self, container):
        """
        Runs when bot shuts down.
        """
        pass
