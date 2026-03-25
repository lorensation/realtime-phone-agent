from __future__ import annotations

import asyncio
import base64
import json
import threading
import traceback
from typing import AsyncGenerator, Generator

import httpx
import numpy as np
from loguru import logger
from numpy.typing import NDArray

from realtime_phone_agents.tts.base import TTSModel
from realtime_phone_agents.tts.togetherai.options import (
    DEFAULT_VOICES,
    TogetherTTSOptions,
)


class TogetherTTSModel(TTSModel):
    """Streaming Together AI TTS client."""

    channels = 1
    bits_per_sample = 16
    min_chunk_size = 1024

    def __init__(self, options: TogetherTTSOptions | None = None):
        self.options = options or TogetherTTSOptions()
        if not self.options.api_key:
            raise ValueError(
                "Together AI API key is required for together TTS. "
                "Set TOGETHER__API_KEY in your environment."
            )
        if not self.options.voice:
            self.options.voice = DEFAULT_VOICES.get(self.options.model, "tara")

    def set_voice(self, voice: str) -> None:
        self.options.voice = voice

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.options.api_key}",
            "Content-Type": "application/json",
        }

    def _stream_audio_sync(
        self,
        text: str,
        options: TogetherTTSOptions,
    ) -> Generator[NDArray[np.int16], None, None]:
        payload = {
            "model": options.model,
            "input": text.strip(),
            "voice": options.voice,
            "stream": True,
            "response_format": "raw",
            "response_encoding": "pcm_s16le",
            "sample_rate": options.sample_rate,
        }

        pcm_buffer = b""
        speech_url = f"{options.api_url.rstrip('/')}/audio/speech"
        with httpx.Client(
            timeout=httpx.Timeout(300.0, connect=10.0),
            headers=self._get_headers(),
        ) as client:
            with client.stream("POST", speech_url, json=payload) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").lower()
                if "text/event-stream" in content_type:
                    chunk_iter = self._iter_sse_audio_chunks(response)
                else:
                    chunk_iter = response.iter_bytes()

                for chunk in chunk_iter:
                    if not chunk:
                        continue
                    pcm_buffer += chunk
                    if len(pcm_buffer) < self.min_chunk_size:
                        continue

                    complete_bytes = (len(pcm_buffer) // 2) * 2
                    if complete_bytes <= 0:
                        continue
                    audio_chunk = np.frombuffer(
                        pcm_buffer[:complete_bytes], dtype=np.int16
                    )
                    yield audio_chunk
                    pcm_buffer = pcm_buffer[complete_bytes:]

                if pcm_buffer:
                    complete_bytes = (len(pcm_buffer) // 2) * 2
                    if complete_bytes > 0:
                        yield np.frombuffer(pcm_buffer[:complete_bytes], dtype=np.int16)

    def _iter_sse_audio_chunks(
        self, response: httpx.Response
    ) -> Generator[bytes, None, None]:
        data_lines: list[str] = []

        for raw_line in response.iter_lines():
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
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
                    logger.debug("Skipping non-JSON Together SSE payload: %s", data_str)
                    continue

                delta = payload.get("delta")
                if not delta:
                    continue

                try:
                    yield base64.b64decode(delta)
                except Exception as exc:
                    logger.warning(f"Failed to decode Together audio delta: {exc}")
                continue

            if line.startswith("data:"):
                data_lines.append(line[5:].strip())

        if data_lines:
            data_str = "\n".join(data_lines).strip()
            if data_str and data_str != "[DONE]":
                try:
                    payload = json.loads(data_str)
                    delta = payload.get("delta")
                    if delta:
                        yield base64.b64decode(delta)
                except Exception as exc:
                    logger.warning(
                        f"Failed to parse trailing Together SSE payload: {exc}"
                    )

    def stream_tts_sync(
        self,
        text: str,
        options: TogetherTTSOptions | None = None,
    ) -> Generator[tuple[int, NDArray[np.int16]], None, None]:
        opts = options or self.options
        if not text or not text.strip():
            logger.warning("Empty text provided to Together AI TTS")
            return

        for audio_chunk in self._stream_audio_sync(text, opts):
            yield opts.sample_rate, audio_chunk

    async def stream_tts(
        self,
        text: str,
        options: TogetherTTSOptions | None = None,
    ) -> AsyncGenerator[tuple[int, NDArray[np.int16]], None]:
        opts = options or self.options
        if not text or not text.strip():
            logger.warning("Empty text provided to Together AI TTS")
            return

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[tuple[int, NDArray[np.int16]] | None] = asyncio.Queue()

        def worker():
            try:
                for sample_rate, chunk in self.stream_tts_sync(text, opts):
                    asyncio.run_coroutine_threadsafe(
                        queue.put((sample_rate, chunk)), loop
                    )
            except Exception as exc:
                logger.error(f"Together AI worker thread error: {exc}")
                traceback.print_exc()
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        threading.Thread(target=worker, daemon=True).start()

        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

    def tts(
        self,
        text: str,
        options: TogetherTTSOptions | None = None,
    ) -> tuple[int, NDArray[np.int16]]:
        opts = options or self.options
        sample_rate = opts.sample_rate
        audio_chunks: list[NDArray[np.int16]] = []

        try:
            for sample_rate, chunk in self.stream_tts_sync(text, opts):
                audio_chunks.append(chunk)
        except Exception as exc:
            logger.error(f"Together AI TTS error: {exc}")
            traceback.print_exc()

        audio = (
            np.concatenate(audio_chunks)
            if audio_chunks
            else np.zeros(0, dtype=np.int16)
        )
        return sample_rate, audio
