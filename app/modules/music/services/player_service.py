from pathlib import Path


class AudioPlayer:

    def __init__(
        self,
        voice_service,
    ):

        self.voice_service = (
            voice_service
        )

    async def play(
        self,
        chat_id: int,
        audio_path: str,
    ):

        path = Path(
            audio_path
        )

        if not path.is_file():

            raise FileNotFoundError(
                audio_path
            )

        if not self.voice_service.is_connected(
            chat_id
        ):

            await self.voice_service.join(
                chat_id
            )

        # Actual audio streaming will
        # be implemented next.

    async def stop(
        self,
        chat_id: int,
    ):

        # Actual stop logic will be
        # implemented next.

        pass