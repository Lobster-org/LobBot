from abc import ABC, abstractmethod


class BaseModule(ABC):

    name: str = "unknown"
    version: str = "1.0.0"
    description: str = ""
    enabled_by_default: bool = False
    core: bool = False

    @abstractmethod
    async def setup(self, dispatcher):
        """
        Register commands,
        handlers, listeners.
        """
        pass


    async def startup(self):
        """
        Runs when module loads.
        """
        pass


    async def shutdown(self):
        """
        Runs when bot shuts down.
        """
        pass