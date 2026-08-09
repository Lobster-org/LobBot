from dataclasses import dataclass


@dataclass
class UserContext:

    user: dict | None

    group: dict | None