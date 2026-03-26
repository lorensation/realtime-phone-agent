from __future__ import annotations

from dataclasses import dataclass, field
import os
from typing import Any

from loguru import logger

from realtime_phone_agents.config import settings

try:
    import opik
except ImportError:  # pragma: no cover - exercised via runtime environment
    opik = None


@dataclass(slots=True)
class Prompt:
    """Versioned prompt wrapper with a safe fallback when Opik is unavailable."""

    name: str
    prompt: str
    metadata: dict[str, Any] | None = None
    description: str | None = None
    tags: list[str] | None = None
    project_name: str | None = None
    _opik_prompt: Any = field(init=False, default=None, repr=False)

    def __post_init__(self) -> None:
        if (
            opik is None
            or not settings.opik.api_key
            or os.environ.get("OPIK_API_KEY") != settings.opik.api_key
        ):
            return

        try:
            self._opik_prompt = opik.Prompt(
                name=self.name,
                prompt=self.prompt,
                metadata=self.metadata,
                description=self.description,
                tags=self.tags,
                project_name=self.project_name or settings.opik.project_name or None,
            )
        except Exception as exc:  # pragma: no cover - depends on external service
            logger.warning(f"Failed to register prompt '{self.name}' in Opik: {exc}")

    @property
    def text(self) -> str:
        return self.prompt

    @property
    def opik_prompt(self) -> Any:
        return self._opik_prompt

    def __str__(self) -> str:
        return self.prompt
