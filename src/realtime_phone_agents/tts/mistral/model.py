from __future__ import annotations

import asyncio
import base64
import json
from collections.abc import AsyncIterator

import httpx
import numpy as np
from loguru import logger

from realtime_phone_agents.tts.base import AudioChunk, TTSModel
from realtime_phone_agents.tts.mistral.options import MistralTTSOptions


def _float32_bytes_to_int16(audio_bytes: bytes) -> np.ndarray:
    if not audio_bytes:
        return np.zeros(0, dtype=np.int16)

    complete_bytes = (len(audio_bytes) // 4) * 4
    if complete_bytes <= 0:
        return np.zeros(0, dtype=np.int16)

    float_audio = np.frombuffer(audio_bytes[:complete_bytes], dtype="<f4")
    clipped_audio = np.clip(float_audio, -1.0, 1.0)
    return (clipped_audio * np.iinfo(np.int16).max).astype(np.int16)


def _extract_audio_data(payload: dict) -> str | None:
    if "audio_data" in payload:
        return payload["audio_data"]

    for key in ("data", "delta", "chunk"):
        value = payload.get(key)
        if isinstance(value, dict) and "audio_data" in value:
            return value["audio_data"]

    return None


class MistralVoxtralTTSModel(TTSModel):
    """Streaming TTS client for Mistral's Voxtral speech API."""

    def __init__(
        self,
        options: MistralTTSOptions | None = None,
        *,
        language: str | None = None,
    ) -> None:
        self.options = options or MistralTTSOptions()
        self.language = (language or "").lower()

        if not self.options.api_key:
            raise ValueError(
                "Mistral API key is required for mistral-voxtral. "
                "Set MISTRAL__API_KEY in your environment."
            )

        self.base_url = self.options.base_url.rstrip("/")
        self.voice_id = self._resolve_voice_id()
        if not self.voice_id:
            raise ValueError(
                "A Mistral voice ID is required for mistral-voxtral. "
                "Set MISTRAL__VOICE_ID or a language-specific override in your environment."
            )

        if self.options.response_format.lower() != "pcm":
            raise ValueError(
                "This project currently supports Mistral TTS with MISTRAL__RESPONSE_FORMAT=pcm only."
            )

    def _resolve_voice_id(self) -> str:
        if self.language.startswith("en") and self.options.voice_id_en:
            return self.options.voice_id_en
        if self.language.startswith("es") and self.options.voice_id_es:
            return self.options.voice_id_es
        return self.options.voice_id

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.options.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }

    def _payload(self, text: str) -> dict[str, object]:
        return {
            "model": self.options.tts_model,
            "input": text.strip(),
            "voice_id": self.voice_id,
            "response_format": self.options.response_format,
            "stream": True,
        }

    async def stream_tts(self, text: str, **kwargs) -> AsyncIterator[AudioChunk]:
        cleaned_text = (text or "").strip()
        if not cleaned_text:
            logger.warning("Empty text provided to Mistral Voxtral TTS")
            return

        data_lines: list[str] = []
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0, read=60.0)
        ) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/audio/speech",
                headers=self._headers(),
                json=self._payload(cleaned_text),
            ) as response:
                response.raise_for_status()
                async for raw_line in response.aiter_lines():
                    line = (raw_line or "").strip()
                    if not line:
                        if not data_lines:
                            continue

                        data_str = "\n".join(data_lines).strip()
                        data_lines.clear()

                        if data_str == "[DONE]":
                            break

                        try:
                            payload = json.loads(data_str)
                        except json.JSONDecodeError:
                            logger.debug(
                                "Skipping non-JSON Mistral speech event: {}", data_str
                            )
                            continue

                        audio_data = _extract_audio_data(payload)
                        if not audio_data:
                            continue

                        audio_bytes = base64.b64decode(audio_data)
                        audio_chunk = _float32_bytes_to_int16(audio_bytes)
                        if audio_chunk.size > 0:
                            yield self.options.sample_rate_hz, audio_chunk
                        continue

                    if line.startswith("data:"):
                        data_lines.append(line[5:].strip())

                if data_lines:
                    data_str = "\n".join(data_lines).strip()
                    if data_str and data_str != "[DONE]":
                        try:
                            payload = json.loads(data_str)
                        except json.JSONDecodeError:
                            payload = {}

                        audio_data = _extract_audio_data(payload)
                        if audio_data:
                            audio_bytes = base64.b64decode(audio_data)
                            audio_chunk = _float32_bytes_to_int16(audio_bytes)
                            if audio_chunk.size > 0:
                                yield self.options.sample_rate_hz, audio_chunk

    def tts(self, text: str, **kwargs) -> AudioChunk:
        async def collect() -> AudioChunk:
            sample_rate = self.options.sample_rate_hz
            audio_chunks: list[np.ndarray] = []

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
                "MistralVoxtralTTSModel.tts() cannot run inside an active event loop. "
                "Use stream_tts() instead."
            ) from exc
