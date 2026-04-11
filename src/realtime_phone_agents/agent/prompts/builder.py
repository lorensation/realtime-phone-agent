from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from realtime_phone_agents.agent.prompts.defaults import (
    DEFAULT_LANGUAGE_POLICY,
    LOCAL_PROMPT_FALLBACKS,
    LOCKED_LANGUAGE_POLICY,
)
from realtime_phone_agents.agent.prompts.provider import (
    ResolvedPrompt,
    build_prompt_provider,
)
from realtime_phone_agents.config import settings

LockedLanguage = Literal["english", "spanish"] | None


@dataclass(slots=True)
class BuiltPrompt:
    text: str
    components: dict[str, ResolvedPrompt]

    @property
    def telemetry(self) -> dict[str, str]:
        payload: dict[str, str] = {}
        for prompt in self.components.values():
            payload.update(prompt.telemetry)
        return payload


@lru_cache(maxsize=3)
def build_system_prompt(language_lock: LockedLanguage = None) -> BuiltPrompt:
    provider = build_prompt_provider()
    components = {
        "core": provider.load_prompt(
            key="core",
            ref=settings.prompts.core,
            fallback_text=LOCAL_PROMPT_FALLBACKS["core"],
        ),
        "retrieval": provider.load_prompt(
            key="retrieval",
            ref=settings.prompts.retrieval,
            fallback_text=LOCAL_PROMPT_FALLBACKS["retrieval"],
        ),
        "escalation": provider.load_prompt(
            key="escalation",
            ref=settings.prompts.escalation,
            fallback_text=LOCAL_PROMPT_FALLBACKS["escalation"],
        ),
        "style": provider.load_prompt(
            key="style",
            ref=settings.prompts.style,
            fallback_text=LOCAL_PROMPT_FALLBACKS["style"],
        ),
    }

    language_policy = (
        LOCKED_LANGUAGE_POLICY[language_lock]
        if language_lock is not None
        else DEFAULT_LANGUAGE_POLICY
    )
    prompt_text = "\n\n".join(
        [
            components["core"].text.strip(),
            components["retrieval"].text.strip(),
            components["escalation"].text.strip(),
            components["style"].text.strip(),
            language_policy.strip(),
        ]
    ).strip()
    return BuiltPrompt(text=prompt_text, components=components)
