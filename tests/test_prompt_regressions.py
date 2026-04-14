import unittest
from types import SimpleNamespace
from unittest.mock import patch

from realtime_phone_agents.agent.prompts.builder import build_system_prompt
from realtime_phone_agents.agent.prompts.provider import ResolvedPrompt
import realtime_phone_agents.agent.prompts.builder as builder_module
from realtime_phone_agents.agent.fastrtc_agent import normalize_spoken_text


class PromptRegressionTests(unittest.TestCase):
    def setUp(self):
        build_system_prompt.cache_clear()

    def _fake_prompt(self, key: str, text: str) -> ResolvedPrompt:
        return ResolvedPrompt(
            key=key,
            name=f"test.{key}",
            text=text,
            source="local_fallback",
        )

    def test_prompt_builder_discourages_robotic_filler(self):
        fake_provider = SimpleNamespace(
            load_prompt=lambda **kwargs: self._fake_prompt(
                kwargs["key"], kwargs["fallback_text"]
            )
        )
        fake_settings = SimpleNamespace(
            prompts=SimpleNamespace(
                core=SimpleNamespace(name="core"),
                retrieval=SimpleNamespace(name="retrieval"),
                escalation=SimpleNamespace(name="escalation"),
                style=SimpleNamespace(name="style"),
            )
        )

        with (
            patch.object(builder_module, "build_prompt_provider", return_value=fake_provider),
            patch.object(builder_module, "settings", fake_settings),
        ):
            prompt = build_system_prompt()

        lowered = prompt.text.lower()
        self.assertIn("do not sound like an ai assistant", lowered)
        self.assertIn("do not narrate your internal process", lowered)
        self.assertNotIn("i am checking the hotel information", lowered)
        self.assertNotIn("estoy revisando la informacion del hotel", lowered)

    def test_prompt_builder_adds_language_lock(self):
        fake_provider = SimpleNamespace(
            load_prompt=lambda **kwargs: self._fake_prompt(
                kwargs["key"], kwargs["fallback_text"]
            )
        )
        fake_settings = SimpleNamespace(
            prompts=SimpleNamespace(
                core=SimpleNamespace(name="core"),
                retrieval=SimpleNamespace(name="retrieval"),
                escalation=SimpleNamespace(name="escalation"),
                style=SimpleNamespace(name="style"),
            )
        )

        with (
            patch.object(builder_module, "build_prompt_provider", return_value=fake_provider),
            patch.object(builder_module, "settings", fake_settings),
        ):
            english_prompt = build_system_prompt(language_lock="english")
            spanish_prompt = build_system_prompt(language_lock="spanish")

        self.assertIn("Reply only in English", english_prompt.text)
        self.assertIn("Responda solo en espanol", spanish_prompt.text)

    def test_spoken_text_normalizer_removes_markdown_formatting(self):
        text = (
            "**Blue Apartment** - 50 m²\n"
            "- kitchen\n"
            "- balcony\n"
            "### Amenities"
        )

        normalized = normalize_spoken_text(text)

        self.assertNotIn("**", normalized)
        self.assertNotIn("###", normalized)
        self.assertNotIn("\n", normalized)
        self.assertIn("Blue Apartment", normalized)
