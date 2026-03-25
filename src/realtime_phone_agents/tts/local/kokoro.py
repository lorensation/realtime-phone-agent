import asyncio

from fastrtc import get_tts_model as get_fastrtc_tts_model

from realtime_phone_agents.tts.base import TTSModel


class KokoroTTSModel(TTSModel):
    """Local Kokoro TTS exposed through FastRTC."""

    def __init__(self):
        self.model = get_fastrtc_tts_model()

    def tts(self, text: str):
        return self.model.tts(text)

    async def stream_tts(self, text: str, **kwargs):
        stream = self.model.stream_tts(text)
        if hasattr(stream, "__aiter__"):
            async for chunk in stream:
                yield chunk
            return

        for chunk in stream:
            yield chunk
            await asyncio.sleep(0)
