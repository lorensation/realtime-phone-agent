from realtime_phone_agents.stt.base import STTModel
from realtime_phone_agents.stt.groq.whisper import WhisperGroqSTT
from realtime_phone_agents.stt.local.moonshine import MoonshineSTT
from realtime_phone_agents.stt.runpod import FasterWhisperSTT


def get_stt_model(model_name: str) -> STTModel:
    """Return the configured STT provider by name."""
    if model_name == "whisper-groq":
        return WhisperGroqSTT()
    if model_name == "faster-whisper":
        return FasterWhisperSTT()
    if model_name == "moonshine":
        return MoonshineSTT()
    raise ValueError(
        "Invalid STT model name: "
        f"{model_name}. Available: moonshine, whisper-groq, faster-whisper"
    )
