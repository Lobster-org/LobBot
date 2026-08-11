import logging

from app.modules.base import BaseModule


logger = logging.getLogger(__name__)


class ModuleLoader:

    def __init__(self):

        self.modules: dict[
            str,
            BaseModule
        ] = {}

    def register(self, module: BaseModule):

        if module.name in self.modules:

            raise ValueError(
                f"Module '{module.name}' "
                f"is already registered."
            )

        self.modules[
            module.name
        ] = module

    def get(self, name: str):

        return self.modules.get(name)

    def all(self):

        return list(
            self.modules.values()
        )

    def exists(self, name: str) -> bool:

        return name in self.modules

    async def setup(self, dispatcher):

        for module in self.modules.values():

            logger.info(
                "Loading module: name=%s version=%s",
                module.name,
                module.version,
            )

            try:
                await module.setup(
                    dispatcher
                )

                await module.startup()
            except Exception:
                logger.exception(
                    "Module startup failed: name=%s",
                    module.name,
                )
                raise

            logger.info(
                "Loaded module: name=%s",
                module.name,
            )

    async def shutdown(self):

        for module in self.modules.values():

            try:
                await module.shutdown()
            except Exception:
                logger.exception(
                    "Module shutdown failed: name=%s",
                    module.name,
                )
            else:
                logger.info(
                    "Module stopped: name=%s",
                    module.name,
                )

module_loader = ModuleLoader()
