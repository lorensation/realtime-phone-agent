from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from realtime_phone_agents.config import PromptComponentSettings, settings

try:
    import opik  # noqa: F401
    from opik.api_objects import opik_client
    from opik.api_objects.prompt.client import PromptClient
except ImportError:  # pragma: no cover - depends on optional dependency wiring
    opik = None
    opik_client = None
    PromptClient = None


@dataclass(slots=True)
class ResolvedPrompt:
    key: str
    name: str
    text: str
    source: str
    commit: str | None = None
    version_id: str | None = None
    fallback_reason: str | None = None

    @property
    def telemetry(self) -> dict[str, str]:
        data = {
            f"prompt.{self.key}.name": self.name,
            f"prompt.{self.key}.source": self.source,
        }
        if self.commit:
            data[f"prompt.{self.key}.commit"] = self.commit
        if self.version_id:
            data[f"prompt.{self.key}.version_id"] = self.version_id
        if self.fallback_reason:
            data[f"prompt.{self.key}.fallback_reason"] = self.fallback_reason
        return data


class PromptProvider:
    def __init__(self, remote_enabled: bool = True):
        self.remote_enabled = remote_enabled

    def load_prompt(
        self,
        *,
        key: str,
        ref: PromptComponentSettings,
        fallback_text: str,
    ) -> ResolvedPrompt:
        if self.remote_enabled:
            remote_prompt = self._try_load_remote(key=key, ref=ref)
            if remote_prompt is not None:
                return remote_prompt

        return ResolvedPrompt(
            key=key,
            name=ref.name,
            text=fallback_text,
            source="local_fallback",
            commit=ref.commit or None,
            fallback_reason="remote_unavailable_or_missing",
        )

    def _try_load_remote(
        self,
        *,
        key: str,
        ref: PromptComponentSettings,
    ) -> ResolvedPrompt | None:
        if opik is None or PromptClient is None or opik_client is None:
            return None
        if not settings.opik.api_key or not settings.prompts.remote_enabled:
            return None

        os.environ.setdefault("OPIK_API_KEY", settings.opik.api_key)
        if settings.opik.project_name:
            os.environ.setdefault("OPIK_PROJECT_NAME", settings.opik.project_name)

        try:
            client = opik_client.get_client_cached()
            prompt_client = PromptClient(client.rest_client)
            prompt_version = self._load_prompt_version(
                prompt_client=prompt_client,
                prompt_name=ref.name,
                commit=ref.commit or None,
            )
            if prompt_version is None:
                logger.info(
                    "Opik prompt '{}' not found for component '{}'. Using fallback.",
                    ref.name,
                    key,
                )
                return None

            return ResolvedPrompt(
                key=key,
                name=ref.name,
                text=prompt_version.template,
                source="opik",
                commit=prompt_version.commit,
                version_id=prompt_version.id,
            )
        except Exception as exc:  # pragma: no cover - depends on external service
            logger.warning(
                "Failed to load Opik prompt '{}' for component '{}': {}",
                ref.name,
                key,
                exc,
            )
            return None

    def _load_prompt_version(
        self,
        *,
        prompt_client: Any,
        prompt_name: str,
        commit: str | None,
    ) -> Any | None:
        versions = prompt_client.get_all_prompt_versions(
            name=prompt_name,
            project_name=None,
        )
        if not versions:
            return None

        if commit:
            for version in versions:
                if getattr(version, "commit", None) == commit:
                    return version
            logger.info(
                "Opik prompt '{}' commit '{}' was not found in the global prompt library.",
                prompt_name,
                commit,
            )
            return None

        return max(versions, key=self._prompt_version_sort_key)

    @staticmethod
    def _prompt_version_sort_key(prompt_version: Any) -> tuple[datetime, str]:
        created_at = getattr(prompt_version, "created_at", None)
        normalized = PromptProvider._normalize_created_at(created_at)
        return normalized, getattr(prompt_version, "id", "") or ""

    @staticmethod
    def _normalize_created_at(created_at: Any) -> datetime:
        if created_at is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        if isinstance(created_at, str):
            candidate = created_at.replace("Z", "+00:00")
            try:
                parsed = datetime.fromisoformat(candidate)
            except ValueError:
                return datetime.min.replace(tzinfo=timezone.utc)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        if isinstance(created_at, datetime):
            if created_at.tzinfo is None:
                return created_at.replace(tzinfo=timezone.utc)
            return created_at
        return datetime.min.replace(tzinfo=timezone.utc)


def build_prompt_provider() -> PromptProvider:
    return PromptProvider(remote_enabled=settings.prompts.remote_enabled)
