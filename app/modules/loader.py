from app.modules.base import BaseModule


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

            print(
                f"Loading module: "
                f"{module.name}"
            )

            await module.setup(
                dispatcher
            )

            await module.startup()

    async def shutdown(self):

        for module in self.modules.values():

            await module.shutdown()
            
module_loader = ModuleLoader()