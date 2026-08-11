from pathlib import Path


PROJECT_ROOT = Path(
    __file__
).resolve().parents[3]


MUSIC_STORAGE_PATH = (
    PROJECT_ROOT
    / "storage"
    / "music"
)


MUSIC_STORAGE_PATH.mkdir(
    parents=True,
    exist_ok=True,
)