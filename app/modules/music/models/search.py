from dataclasses import dataclass

from app.modules.music.models.track import Track


@dataclass
class SearchSession:

    user_id: int

    chat_id: int

    tracks: list[Track]

    created_at: float