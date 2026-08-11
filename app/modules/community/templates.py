from html import escape
from random import SystemRandom
from string import Formatter

from app.modules.community.config import SUPPORTED_TEMPLATE_FIELDS


WELCOME_OPENINGS = (
    "🚨 Sound the tiny trumpets—{mention} has entered {group}!",
    "🎉 Plot twist: {mention} just joined {group}!",
    "🛸 The mothership has delivered {mention} safely to {group}.",
    "📢 Breaking news: {mention} discovered the join button.",
    "🧙 A mysterious spell summoned {mention} into {group}.",
    "🚪 The door creaked open and in walked {mention}.",
    "🌪️ A wild {mention} appeared! Nobody panic.",
    "🛰️ Radar confirms a new life-form in {group}: {mention}.",
    "🥁 Drumroll, please... {mention} has arrived!",
    "🧩 We found {group}'s missing piece—it was {mention}.",
)

WELCOME_PUNCHLINES = (
    "Please keep your hands inside the group at all times.",
    "We saved you a seat, but someone may have eaten it.",
    "The snacks are imaginary, but the chaos is very real.",
    "Your complimentary welcome llama is currently in transit.",
    "No pressure, but we already told everyone you're hilarious.",
    "The group warranty is now officially void.",
    "Please ignore the suspiciously enthusiastic confetti cannon.",
    "You may now pretend you understand what is happening here.",
)

GOODBYE_OPENINGS = (
    "👋 {name} has left {group}.",
    "🚪 And just like that, {name} vanished through the exit.",
    "🛸 The mothership has reclaimed {name}.",
    "📉 Our member count has misplaced {name}.",
    "🎬 {name} has exited the group, pursued by dramatic music.",
    "🧳 {name} packed their virtual bags and departed.",
    "🌫️ A puff of smoke appeared, and {name} was gone.",
    "📢 Breaking news: {name} has escaped the group chat.",
)

GOODBYE_PUNCHLINES = (
    "We shall preserve their imaginary chair.",
    "Their complimentary llama has been returned to storage.",
    "The snacks remain untouched, somehow.",
    "May their notification count finally know peace.",
    "The group warranty might recover eventually.",
    "Someone cancel the farewell confetti invoice.",
    "We give the dramatic exit a respectable 8/10.",
    "The door remains open, mostly because the hinge is broken.",
)

WELCOME_VARIATION_COUNT = len(WELCOME_OPENINGS) * len(WELCOME_PUNCHLINES)
GOODBYE_VARIATION_COUNT = len(GOODBYE_OPENINGS) * len(GOODBYE_PUNCHLINES)


class TemplateRenderer:
    def __init__(self, randomizer=None):
        self.randomizer = randomizer or SystemRandom()

    def welcome(self, custom: str | None, values: dict[str, str]) -> str:
        if custom:
            return self.render(custom, values)
        return (
            self.render(self.randomizer.choice(WELCOME_OPENINGS), values)
            + "\n\n"
            + self.render(self.randomizer.choice(WELCOME_PUNCHLINES), values)
        )

    def goodbye(self, custom: str | None, values: dict[str, str]) -> str:
        if custom:
            return self.render(custom, values)
        return (
            self.render(self.randomizer.choice(GOODBYE_OPENINGS), values)
            + "\n\n"
            + self.render(self.randomizer.choice(GOODBYE_PUNCHLINES), values)
        )

    def validate(self, template: str) -> None:
        self.render(
            template,
            {field: field for field in SUPPORTED_TEMPLATE_FIELDS},
        )

    def render(self, template: str, values: dict[str, str]) -> str:
        output = []
        try:
            parts = Formatter().parse(template)
            for literal, field, format_spec, conversion in parts:
                output.append(escape(literal))
                if field is None:
                    continue
                if (
                    field not in SUPPORTED_TEMPLATE_FIELDS
                    or format_spec
                    or conversion
                ):
                    raise ValueError(f"Unsupported template field: {field}")
                output.append(values[field])
        except (KeyError, ValueError) as error:
            raise ValueError("Invalid community message template") from error
        return "".join(output)
