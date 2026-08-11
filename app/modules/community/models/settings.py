from dataclasses import asdict, dataclass


@dataclass(slots=True)
class CommunitySettings:
    chat_id: int
    welcome_enabled: bool = True
    goodbye_enabled: bool = False
    welcome_message: str | None = None
    goodbye_message: str | None = None
    rules: str | None = None
    verification_enabled: bool = False
    verification_timeout_seconds: int = 300
    delete_service_messages: bool = False

    @classmethod
    def from_document(cls, chat_id: int, document: dict | None):
        if not document:
            return cls(chat_id=chat_id)
        return cls(
            chat_id=chat_id,
            welcome_enabled=bool(document.get("welcome_enabled", True)),
            goodbye_enabled=bool(document.get("goodbye_enabled", False)),
            welcome_message=document.get("welcome_message"),
            goodbye_message=document.get("goodbye_message"),
            rules=document.get("rules"),
            verification_enabled=bool(
                document.get("verification_enabled", False)
            ),
            verification_timeout_seconds=max(
                30,
                min(
                    3600,
                    int(document.get("verification_timeout_seconds", 300)),
                ),
            ),
            delete_service_messages=bool(
                document.get("delete_service_messages", False)
            ),
        )

    def to_document(self) -> dict:
        return asdict(self)
