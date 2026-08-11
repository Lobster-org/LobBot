from app.modules.loader import module_loader

from app.modules.start.module import (
    StartModule,
)
from app.modules.help.module import (
    HelpModule,
)

from app.modules.group.module import (
    GroupModule,
)

from app.modules.management.module import (
    ManagementModule,
)

from app.modules.music.module import (
    MusicModule,
)


def register_modules():

    module_loader.register(
        StartModule()
    )

    module_loader.register(
        HelpModule()
    )

    module_loader.register(
        GroupModule()
    )

    module_loader.register(
        ManagementModule()
    )

    module_loader.register(
        MusicModule()
    )
