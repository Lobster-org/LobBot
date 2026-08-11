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
from app.modules.moderation.module import (
    ModerationModule,
)


def register_modules(loader=module_loader):

    if loader.all():
        return loader

    loader.register(
        StartModule()
    )

    loader.register(
        HelpModule()
    )

    loader.register(
        GroupModule()
    )

    loader.register(
        ManagementModule()
    )

    loader.register(
        MusicModule()
    )

    loader.register(
        ModerationModule()
    )

    return loader
