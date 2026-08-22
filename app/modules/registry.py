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
from app.modules.community.module import CommunityModule
from app.modules.economy.module import EconomyModule
from app.modules.games.module import GamesModule
from app.modules.media.module import MediaModule
from app.modules.dictionary.module import DictionaryModule
from app.modules.translation.module import TranslationModule
from app.modules.afk.module import AFKModule
from app.modules.reactions.module import ReactionsModule


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
        CommunityModule()
    )

    loader.register(
        EconomyModule()
    )

    loader.register(
        GamesModule()
    )

    loader.register(
        ModerationModule()
    )

    loader.register(MediaModule())
    loader.register(DictionaryModule())
    loader.register(TranslationModule())
    loader.register(ReactionsModule())
    # Keep the catch-all AFK observer last so feature command routers run first.
    loader.register(AFKModule())

    return loader
