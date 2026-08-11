from dataclasses import asdict, dataclass, field


AUTOMOD_RULES = frozenset(
    {"flood", "repeat", "links", "caps", "words"}
)


@dataclass(slots=True)
class AutomodConfig:
    enabled: bool = False
    rules: dict[str, bool] = field(
        default_factory=lambda: {
            "flood": True,
            "repeat": True,
            "links": False,
            "caps": False,
            "words": False,
        }
    )
    blocked_words: list[str] = field(default_factory=list)
    flood_limit: int = 6
    flood_window_seconds: int = 5
    repeat_limit: int = 3
    repeat_window_seconds: int = 30
    caps_ratio: float = 0.75
    caps_min_letters: int = 12
    warning_threshold: int = 3
    mute_duration_seconds: int = 600

    @classmethod
    def from_document(cls, value: dict | None):
        defaults = cls()
        if not isinstance(value, dict):
            return defaults

        rules = defaults.rules | {
            name: bool(enabled)
            for name, enabled in value.get("rules", {}).items()
            if name in AUTOMOD_RULES
        }
        words = value.get("blocked_words", [])
        return cls(
            enabled=bool(value.get("enabled", defaults.enabled)),
            rules=rules,
            blocked_words=(
                [str(word).casefold() for word in words if str(word).strip()]
                if isinstance(words, list)
                else []
            ),
            flood_limit=int(value.get("flood_limit", defaults.flood_limit)),
            flood_window_seconds=int(
                value.get(
                    "flood_window_seconds",
                    defaults.flood_window_seconds,
                )
            ),
            repeat_limit=int(value.get("repeat_limit", defaults.repeat_limit)),
            repeat_window_seconds=int(
                value.get(
                    "repeat_window_seconds",
                    defaults.repeat_window_seconds,
                )
            ),
            caps_ratio=float(value.get("caps_ratio", defaults.caps_ratio)),
            caps_min_letters=int(
                value.get("caps_min_letters", defaults.caps_min_letters)
            ),
            warning_threshold=int(
                value.get("warning_threshold", defaults.warning_threshold)
            ),
            mute_duration_seconds=int(
                value.get(
                    "mute_duration_seconds",
                    defaults.mute_duration_seconds,
                )
            ),
        )

    def to_document(self) -> dict:
        return asdict(self)
