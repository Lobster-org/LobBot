from html import escape
from random import SystemRandom

from app.modules.welcome.events import MEMBER_JOINED
from app.modules.welcome.messages import OPENINGS, PUNCHLINES


class WelcomeService:
    def __init__(self, bot, events, randomizer=None):
        self.bot = bot
        self.events = events
        self.randomizer = randomizer or SystemRandom()

    def introduction_for(self, user) -> str:
        display_name = escape(user.full_name or "mysterious stranger")
        mention = (
            f'<a href="tg://user?id={user.id}">{display_name}</a>'
        )
        opening = self.randomizer.choice(OPENINGS).format(name=mention)
        punchline = self.randomizer.choice(PUNCHLINES)
        return f"{opening}\n\n{punchline}"

    async def welcome(self, chat_id: int, user):
        text = self.introduction_for(user)
        await self.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
        )
        await self.events.emit(
            MEMBER_JOINED,
            {
                "chat_id": chat_id,
                "user_id": user.id,
                "username": user.username,
            },
        )
        return text
