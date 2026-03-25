import asyncio
from typing import AsyncIterator, List

import numpy as np

from .base import AudioChunk, BaseVoiceEffect


class RingbackEffect(BaseVoiceEffect):
    """Generate a simple phone ringback tone without an external audio asset."""

    def __init__(
        self,
        max_duration_s: float = 2.0,
        target_rate: int = 16000,
        chunk_ms: int = 100,
        burst_s: float = 0.4,
        silence_s: float = 0.2,
    ):
        self.max_duration_s = max_duration_s
        self.target_rate = target_rate
        self.chunk_ms = chunk_ms
        self.burst_s = burst_s
        self.silence_s = silence_s
        self.chunks: List[AudioChunk] = self._build_chunks()

    def _build_chunks(self) -> List[AudioChunk]:
        total_samples = int(self.max_duration_s * self.target_rate)
        burst_samples = int(self.burst_s * self.target_rate)
        silence_samples = int(self.silence_s * self.target_rate)
        chunk_size = int((self.target_rate * self.chunk_ms) / 1000)

        if total_samples <= 0 or chunk_size <= 0:
            return []

        output = np.zeros(total_samples, dtype=np.float32)
        cursor = 0
        while cursor < total_samples:
            ring_end = min(cursor + burst_samples, total_samples)
            ring_samples = ring_end - cursor
            if ring_samples > 0:
                timeline = np.arange(ring_samples, dtype=np.float32) / self.target_rate
                tone = (
                    np.sin(2 * np.pi * 440 * timeline)
                    + np.sin(2 * np.pi * 480 * timeline)
                ) * 0.15
                output[cursor:ring_end] = tone.astype(np.float32, copy=False)
            cursor = ring_end + silence_samples

        chunks: List[AudioChunk] = []
        for start in range(0, total_samples, chunk_size):
            chunk = output[start : start + chunk_size]
            if len(chunk) == 0:
                continue
            chunks.append((self.target_rate, chunk))
        return chunks

    async def stream(self) -> AsyncIterator[AudioChunk]:
        for chunk in self.chunks:
            yield chunk
            await asyncio.sleep(0)
