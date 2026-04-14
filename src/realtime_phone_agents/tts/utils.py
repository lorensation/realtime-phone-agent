from loguru import logger

from realtime_phone_agents.tts.base import TTSModel
from realtime_phone_agents.tts.elevenlabs import ElevenLabsTTSModel
from realtime_phone_agents.tts.local.kokoro import KokoroTTSModel
from realtime_phone_agents.tts.mistral import MistralVoxtralTTSModel
from realtime_phone_agents.tts.runpod import OrpheusTTSModel
from realtime_phone_agents.tts.togetherai import TogetherTTSModel


def get_tts_model(model_name: str, *, language: str | None = None) -> TTSModel:
    """Return the configured TTS provider by name."""
    if model_name == "kokoro":
        return KokoroTTSModel()
    if model_name in {
        "elevenlabs",
        "elevenlabs-multilingual",
        "elevenlabs-es",
        "elevenlabs-flash",
        "elevenlabs-flash-es",
    }:
        return ElevenLabsTTSModel(language_code=language)
    if model_name in {"mistral-voxtral", "mistral", "voxtral"}:
        return MistralVoxtralTTSModel(language=language)
    if model_name == "orpheus-runpod":
        model = OrpheusTTSModel()
        logger.info("Warming up Orpheus TTS model")
        model.tts_blocking("Warm up the speech model")
        return model
    if model_name == "together":
        return TogetherTTSModel()
    raise ValueError(
        "Invalid TTS model name: "
        f"{model_name}. Available: elevenlabs, mistral-voxtral, kokoro, together, orpheus-runpod"
    )
