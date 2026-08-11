import asyncio

from app.modules.music.services.music_service import (
    MusicService,
)


async def main():

    service = MusicService(
        "storage/music"
    )

    tracks = await service.search(
        "The Weeknd Blinding Lights",
        limit=1,
    )

    if not tracks:

        print("No tracks found.")

        return

    track = tracks[0]

    print(
        f"Downloading: {track.title}"
    )

    path = await service.download(
        track
    )

    print(
        f"Saved to: {path}"
    )


if __name__ == "__main__":

    asyncio.run(main())