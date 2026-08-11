from dataclasses import dataclass
from typing import Optional


@dataclass
class Track:
    title: str
    duration: Optional[int] = None
    artist: Optional[str] = None
    url: Optional[str] = None
    thumbnail: Optional[str] = None
    source: Optional[str] = None
    source_id: Optional[str] = None
    file_path: Optional[str] = None