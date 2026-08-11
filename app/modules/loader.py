import logging

from app.modules.base import BaseModule


logger = logging.getLogger(__name__)


class ModuleLoader:
    def __init__(self):
        self.modules: dict[str, BaseModule] = {}
        self._setup_modules: list[BaseModule] = []
        self._started_modules: list[BaseModule] = []
        self._stopped_modules: set[str] = set()

    def register(self, module: BaseModule):
        if module.name in self.modules:
            raise ValueError(
                f"Module '{module.name}' is already registered."
            )

        if self._setup_modules or self._started_modules:
            raise RuntimeError(
                "Modules cannot be registered after lifecycle startup"
            )

        self.modules[module.name] = module

    def get(self, name: str):
        return self.modules.get(name)

    def all(self):
        return list(self.modules.values())

    def exists(self, name: str) -> bool:
        return name in self.modules

    async def setup(self, container, dispatcher):
        for module in self.modules.values():
            if module in self._setup_modules:
                continue

            logger.info(
                "Setting up module: name=%s version=%s",
                module.name,
                module.version,
            )

            try:
                await module.setup(container, dispatcher)
            except Exception:
                logger.exception(
                    "Module setup failed: name=%s",
                    module.name,
                )
                raise

            self._setup_modules.append(module)
            logger.info("Module setup complete: name=%s", module.name)

    async def startup(self, container):
        for module in self._setup_modules:
            if module in self._started_modules:
                continue

            logger.info("Starting module: name=%s", module.name)

            try:
                await module.startup(container)
            except Exception:
                logger.exception(
                    "Module startup failed: name=%s",
                    module.name,
                )
                raise

            self._started_modules.append(module)
            logger.info("Module started: name=%s", module.name)

    async def shutdown(self, container):
        for module in reversed(self._started_modules):
            if module.name in self._stopped_modules:
                continue

            try:
                await module.shutdown(container)
            except Exception:
                logger.exception(
                    "Module shutdown failed: name=%s",
                    module.name,
                )
            finally:
                self._stopped_modules.add(module.name)

            logger.info("Module stopped: name=%s", module.name)


module_loader = ModuleLoader()
