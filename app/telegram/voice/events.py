import logging

from pytgcalls.types import (
    StreamEnded,
)


logger = logging.getLogger(__name__)


class VoiceEventHandler:

    def __init__(
        self,
        voice_calls,
        playback_service,
    ):

        self.voice_calls = voice_calls
        self.playback_service = (
            playback_service
        )


    def register(self):

        @self.voice_calls.on_update()
        async def handle_update(
            client,
            update,
        ):

            if not isinstance(
                update,
                StreamEnded,
            ):
                return


            if (
                update.stream_type
                != StreamEnded.Type.AUDIO
            ):
                return


            chat_id = update.chat_id


            logger.info(
                "Audio stream ended: chat=%s",
                chat_id,
            )


            try:
                await (
                    self.playback_service
                    .handle_stream_end(
                        chat_id
                    )
                )
            except Exception:
                logger.exception(
                    "Failed to handle stream end: chat=%s",
                    chat_id,
                )
