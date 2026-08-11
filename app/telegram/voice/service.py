import logging
from pathlib import Path

from pytgcalls.types import (
    AudioQuality,
    MediaStream,
)


logger = logging.getLogger(__name__)


class VoiceChatService:

    def __init__(
        self,
        calls,
    ):
        self.calls = calls

    async def play(
        self,
        chat_id: int,
        file_path: str,
    ):
        if not file_path:
            raise ValueError(
                "Track has no file path"
            )

        path = Path(file_path)

        if not path.is_file():
            raise FileNotFoundError(
                f"Audio file does not exist: {file_path}"
            )

        logger.info(
            "Starting voice playback: chat=%s file=%s",
            chat_id,
            path,
        )

        stream = MediaStream(
            path,
            audio_parameters=AudioQuality.HIGH,
        )

        await self.calls.play(
            chat_id,
            stream,
        )

        logger.info(
            "Voice playback started: chat=%s",
            chat_id,
        )

    async def stop(
        self,
        chat_id: int,
    ):
        logger.info(
            "Stopping voice chat: chat=%s",
            chat_id,
        )

        await self.calls.leave_call(
            chat_id,
        )

    async def pause(self, chat_id: int):
        await self.calls.pause(chat_id)

    async def resume(self, chat_id: int):
        await self.calls.resume(chat_id)
