from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class STTModel(ABC):
    """Abstract contract for speech-to-text providers."""

    @abstractmethod
    def stt(self, audio_data: Any, **kwargs) -> str:
        """Return a transcription for the provided audio payload."""
