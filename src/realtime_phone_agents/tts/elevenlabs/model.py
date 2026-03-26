from __future__ import annotations

import asyncio
import audioop
from collections.abc import AsyncIterator

import httpx
import numpy as np
from loguru import logger
from numpy.typing import NDArray

from realtime_phone_agents.config import settings
from realtime_phone_agents.tts.base import AudioChunk, TTSModel

ELEVEN_TTS_STREAM_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"


def _parse_output_format(output_format: str) -> tuple[str, int]:
    normalized = (output_format or "").strip().lower()
    if normalized.startswith("pcm_"):
        return "pcm", int(normalized.split("_", 1)[1])
    if normalized == "ulaw_8000":
        return "ulaw", 8000
    raise ValueError(
        "Unsupported ElevenLabs output format: "
        f"{output_format}. Supported formats here are pcm_* and ulaw_8000."
    )


def ulaw_bytes_to_int16(ulaw_bytes: bytes) -> NDArray[np.int16]:
    linear_pcm = audioop.ulaw2lin(ulaw_bytes, 2)
    return np.frombuffer(linear_pcm, dtype=np.int16)


class ElevenLabsTTSModel(TTSModel):
    """Streaming ElevenLabs TTS client for the Spanish telephony path."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model_id: str | None = None,
        voice_id: str | None = None,
        output_format: str | None = None,
        language_code: str = "es",
        apply_text_normalization: str = "auto",
    ) -> None:
        self.api_key = api_key or settings.elevenlabs.api_key
        self.model_id = model_id or settings.elevenlabs.model_id
        self.voice_id = voice_id or settings.elevenlabs.voice_id_es
        self.output_format = output_format or settings.elevenlabs.output_format
        self.language_code = language_code
        self.apply_text_normalization = apply_text_normalization
        self.encoding, self.sample_rate = _parse_output_format(self.output_format)

        if not self.api_key:
            raise ValueError(
                "ElevenLabs API key is required for elevenlabs-es. "
                "Set ELEVENLABS__API_KEY in your environment."
            )
        if not self.voice_id:
            raise ValueError(
                "ElevenLabs voice id is required for elevenlabs-es. "
                "Set ELEVENLABS__VOICE_ID_ES in your environment."
            )

    def _request_payload(
        self,
        text: str,
        *,
        previous_text: str | None = None,
        next_text: str | None = None,
    ) -> dict[str, str]:
        payload = {
            "text": text.strip(),
            "model_id": self.model_id,
            "language_code": self.language_code,
            "apply_text_normalization": self.apply_text_normalization,
        }
        if previous_text:
            payload["previous_text"] = previous_text
        if next_text:
            payload["next_text"] = next_text
        return payload

    async def stream_tts(
        self,
        text: str,
        **kwargs,
    ) -> AsyncIterator[AudioChunk]:
        cleaned_text = (text or "").strip()
        if not cleaned_text:
            logger.warning("Empty text provided to ElevenLabs TTS")
            return

        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/octet-stream",
        }
        params = {"output_format": self.output_format}
        payload = self._request_payload(
            cleaned_text,
            previous_text=kwargs.get("previous_text"),
            next_text=kwargs.get("next_text"),
        )

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0, read=60.0)
        ) as client:
            async with client.stream(
                "POST",
                ELEVEN_TTS_STREAM_URL.format(voice_id=self.voice_id),
                headers=headers,
                params=params,
                json=payload,
            ) as response:
                response.raise_for_status()
                pcm_buffer = b""
                async for chunk in response.aiter_bytes():
                    if not chunk:
                        continue

                    if self.encoding == "ulaw":
                        yield self.sample_rate, ulaw_bytes_to_int16(chunk)
                        continue

                    pcm_buffer += chunk
                    complete_bytes = (len(pcm_buffer) // 2) * 2
                    if complete_bytes <= 0:
                        continue

                    audio_chunk = np.frombuffer(
                        pcm_buffer[:complete_bytes], dtype=np.int16
                    )
                    yield self.sample_rate, audio_chunk
                    pcm_buffer = pcm_buffer[complete_bytes:]

                if self.encoding == "pcm" and pcm_buffer:
                    complete_bytes = (len(pcm_buffer) // 2) * 2
                    if complete_bytes > 0:
                        yield self.sample_rate, np.frombuffer(
                            pcm_buffer[:complete_bytes], dtype=np.int16
                        )

    def tts(self, text: str, **kwargs) -> AudioChunk:
        async def collect() -> AudioChunk:
            sample_rate = self.sample_rate
            audio_chunks: list[NDArray[np.int16]] = []

            async for sample_rate, chunk in self.stream_tts(text, **kwargs):
                audio_chunks.append(chunk)

            audio = (
                np.concatenate(audio_chunks)
                if audio_chunks
                else np.zeros(0, dtype=np.int16)
            )
            return sample_rate, audio

        try:
            return asyncio.run(collect())
        except RuntimeError as exc:
            raise RuntimeError(
                "ElevenLabsTTSModel.tts() cannot run inside an active event loop. "
                "Use stream_tts() instead."
            ) from exc
