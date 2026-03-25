from fastrtc import get_stt_model as get_fastrtc_stt_model

from realtime_phone_agents.stt.base import STTModel


class MoonshineSTT(STTModel):
    """Local Moonshine STT exposed through FastRTC."""

    def __init__(self):
        self.moonshine_client = get_fastrtc_stt_model()

    def stt(self, audio_data) -> str:
        return self.moonshine_client.stt(audio_data)
