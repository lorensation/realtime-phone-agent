from __future__ import annotations

import asyncio
import json
import threading
import traceback
from typing import AsyncGenerator, Generator

import numpy as np
import requests
from loguru import logger
from numpy.typing import NDArray

from realtime_phone_agents.tts.base import TTSModel
from realtime_phone_agents.tts.runpod.orpheus.options import (
    CUSTOM_TOKEN_PREFIX,
    OrpheusTTSOptions,
)
from realtime_phone_agents.tts.runpod.orpheus.token_decoders import (
    convert_to_audio,
)


def _validate_api_url(api_url: str) -> str:
    if not api_url or api_url.endswith("_HERE"):
        raise ValueError(
            "Orpheus API URL is required for orpheus-runpod. "
            "Set ORPHEUS__API_URL in your environment."
        )
    return api_url.rstrip("/")


class OrpheusTTSModel(TTSModel):
    """Streaming TTS client for an Orpheus llama.cpp deployment."""

    def __init__(self, options: OrpheusTTSOptions | None = None):
        self.options = options or OrpheusTTSOptions()
        self.options.api_url = _validate_api_url(self.options.api_url)

    def set_voice(self, voice: str) -> None:
        self.options.voice = voice

    def _format_prompt(self, prompt: str, voice: str) -> str:
        return f"<|audio|>{voice}: {prompt}<|eot_id|>"

    def _generate_tokens_sync(
        self,
        text: str,
        options: OrpheusTTSOptions,
    ) -> Generator[str, None, None]:
        formatted_prompt = self._format_prompt(text, options.voice)
        payload = {
            "model": options.model,
            "prompt": formatted_prompt,
            "max_tokens": options.max_tokens,
            "temperature": options.temperature,
            "top_p": options.top_p,
            "repeat_penalty": options.repetition_penalty,
            "stream": True,
        }

        response = requests.post(
            f"{options.api_url}/v1/completions",
            headers=options.headers,
            json=payload,
            stream=True,
            timeout=None,
        )
        response.raise_for_status()

        for line in response.iter_lines():
            if not line:
                continue
            line_str = line.decode("utf-8")
            if not line_str.startswith("data: "):
                continue
            data_str = line_str[6:].strip()
            if data_str == "[DONE]":
                break

            data = json.loads(data_str)
            if "choices" in data and data["choices"]:
                token_text = data["choices"][0].get("text", "")
                if token_text:
                    yield token_text

    def _turn_token_into_id(self, token_string: str, index: int) -> int | None:
        token_string = token_string.strip()
        last_token_start = token_string.rfind(CUSTOM_TOKEN_PREFIX)
        if last_token_start == -1:
            return None

        last_token = token_string[last_token_start:]
        if last_token.startswith(CUSTOM_TOKEN_PREFIX) and last_token.endswith(">"):
            try:
                number_str = last_token[14:-1]
                return int(number_str) - 10 - ((index % 7) * 4096)
            except ValueError:
                return None
        return None

    def _token_decoder_sync(
        self,
        token_gen: Generator[str, None, None],
    ) -> Generator[NDArray[np.int16], None, None]:
        buffer: list[int] = []
        count = 0

        for token_text in token_gen:
            token_id = self._turn_token_into_id(token_text, count)
            if token_id is None or token_id <= 0:
                continue

            buffer.append(token_id)
            count += 1
            if count % 7 != 0 or count <= 27:
                continue

            audio_bytes = convert_to_audio(buffer[-28:], count)
            if audio_bytes is None:
                continue

            audio_samples = np.frombuffer(audio_bytes, dtype=np.int16)
            if audio_samples.size > 0:
                yield audio_samples

    def stream_tts_sync(
        self,
        text: str,
        options: OrpheusTTSOptions | None = None,
    ) -> Generator[tuple[int, NDArray[np.int16]], None, None]:
        opts = options or self.options
        token_gen = self._generate_tokens_sync(text, opts)
        for audio_chunk in self._token_decoder_sync(token_gen):
            yield opts.sample_rate, audio_chunk

    async def stream_tts(
        self,
        text: str,
        options: OrpheusTTSOptions | None = None,
    ) -> AsyncGenerator[tuple[int, NDArray[np.int16]], None]:
        opts = options or self.options
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[tuple[int, NDArray[np.int16]] | None] = asyncio.Queue()

        def worker():
            try:
                for sample_rate, chunk in self.stream_tts_sync(text, opts):
                    asyncio.run_coroutine_threadsafe(
                        queue.put((sample_rate, chunk)), loop
                    )
            except Exception as exc:
                logger.error(f"Orpheus worker thread error: {exc}")
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
        options: OrpheusTTSOptions | None = None,
    ) -> tuple[int, NDArray[np.int16]]:
        return self.tts_blocking(text, options)

    def tts_blocking(
        self,
        text: str,
        options: OrpheusTTSOptions | None = None,
    ) -> tuple[int, NDArray[np.int16]]:
        opts = options or self.options
        sample_rate = opts.sample_rate
        audio_chunks: list[NDArray[np.int16]] = []

        try:
            for sample_rate, chunk in self.stream_tts_sync(text, opts):
                audio_chunks.append(chunk)
        except Exception as exc:
            logger.error(f"Orpheus blocking TTS error: {exc}")
            traceback.print_exc()

        audio = (
            np.concatenate(audio_chunks)
            if audio_chunks
            else np.zeros(0, dtype=np.int16)
        )
        return sample_rate, audio
