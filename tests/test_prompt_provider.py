import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import realtime_phone_agents.agent.prompts.provider as provider_module
from realtime_phone_agents.agent.prompts.provider import PromptProvider
from realtime_phone_agents.config import PromptComponentSettings


class PromptProviderTests(unittest.TestCase):
    def test_local_fallback_when_opik_is_unavailable(self):
        fake_settings = SimpleNamespace(
            opik=SimpleNamespace(api_key="", project_name=""),
            prompts=SimpleNamespace(remote_enabled=True),
        )

        with (
            patch.object(provider_module, "settings", fake_settings),
            patch.object(provider_module, "opik", None),
            patch.object(provider_module, "PromptClient", None),
            patch.object(provider_module, "opik_client", None),
        ):
            provider = PromptProvider(remote_enabled=True)
            prompt = provider.load_prompt(
                key="core",
                ref=PromptComponentSettings(name="blue.core"),
                fallback_text="local fallback",
            )

        self.assertEqual(prompt.source, "local_fallback")
        self.assertEqual(prompt.text, "local fallback")

    def test_remote_prompt_fetch_uses_pinned_commit(self):
        fake_settings = SimpleNamespace(
            opik=SimpleNamespace(api_key="opik-key", project_name="hotel-project"),
            prompts=SimpleNamespace(remote_enabled=True),
        )
        fake_prompt_client = MagicMock()
        fake_prompt_client.get_all_prompt_versions.return_value = [
            SimpleNamespace(
                template="older prompt body",
                commit="commit-000",
                id="version-000",
                created_at=datetime(2026, 4, 10, 10, 0, tzinfo=timezone.utc),
            ),
            SimpleNamespace(
                template="remote prompt body",
                commit="commit-123",
                id="version-456",
                created_at=datetime(2026, 4, 11, 10, 0, tzinfo=timezone.utc),
            ),
        ]
        fake_client_factory = MagicMock()
        fake_client_factory.rest_client = object()

        with (
            patch.object(provider_module, "settings", fake_settings),
            patch.object(provider_module, "opik", object()),
            patch.object(provider_module, "PromptClient", return_value=fake_prompt_client),
            patch.object(
                provider_module,
                "opik_client",
                SimpleNamespace(get_client_cached=MagicMock(return_value=fake_client_factory)),
            ),
        ):
            provider = PromptProvider(remote_enabled=True)
            prompt = provider.load_prompt(
                key="core",
                ref=PromptComponentSettings(
                    name="blue_sardine.receptionist.core",
                    commit="commit-123",
                ),
                fallback_text="local fallback",
            )

        self.assertEqual(prompt.source, "opik")
        self.assertEqual(prompt.text, "remote prompt body")
        fake_prompt_client.get_all_prompt_versions.assert_called_once_with(
            name="blue_sardine.receptionist.core",
            project_name="hotel-project",
        )

    def test_remote_prompt_fetch_uses_latest_project_scoped_version_when_unpinned(self):
        fake_settings = SimpleNamespace(
            opik=SimpleNamespace(api_key="opik-key", project_name="hotel-project"),
            prompts=SimpleNamespace(remote_enabled=True),
        )
        fake_prompt_client = MagicMock()
        fake_prompt_client.get_all_prompt_versions.return_value = [
            SimpleNamespace(
                template="older prompt body",
                commit="commit-001",
                id="version-001",
                created_at="2026-04-10T10:00:00+00:00",
            ),
            SimpleNamespace(
                template="latest prompt body",
                commit="commit-002",
                id="version-002",
                created_at="2026-04-11T10:00:00+00:00",
            ),
        ]
        fake_client_factory = MagicMock()
        fake_client_factory.rest_client = object()

        with (
            patch.object(provider_module, "settings", fake_settings),
            patch.object(provider_module, "opik", object()),
            patch.object(provider_module, "PromptClient", return_value=fake_prompt_client),
            patch.object(
                provider_module,
                "opik_client",
                SimpleNamespace(get_client_cached=MagicMock(return_value=fake_client_factory)),
            ),
        ):
            provider = PromptProvider(remote_enabled=True)
            prompt = provider.load_prompt(
                key="style",
                ref=PromptComponentSettings(name="blue_sardine.receptionist.style"),
                fallback_text="local fallback",
            )

        self.assertEqual(prompt.source, "opik")
        self.assertEqual(prompt.text, "latest prompt body")
        self.assertEqual(prompt.commit, "commit-002")
