from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

import numpy as np
from numpy.typing import NDArray

AudioChunk = tuple[int, NDArray[np.int16]]


class TTSModel(ABC):
    """Abstract contract for text-to-speech providers."""

    @abstractmethod
    async def stream_tts(self, text: str, **kwargs) -> AsyncIterator[AudioChunk]:
        """Yield streaming audio chunks for the provided text."""

    @abstractmethod
    def tts(self, text: str, **kwargs) -> AudioChunk:
        """Return a complete audio response for the provided text."""
