from __future__ import annotations

import argparse
import os

from opik.api_objects import opik_client

from realtime_phone_agents.agent.prompts.defaults import LOCAL_PROMPT_FALLBACKS
from realtime_phone_agents.config import settings


PROMPT_DESCRIPTIONS = {
    "core": "Core receptionist behavior and role definition.",
    "retrieval": "Grounding, factual retrieval, and answer shaping rules.",
    "escalation": "Escalation and uncertainty handling for hotel calls.",
    "style": "Spoken-language style rules for phone-safe outputs.",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Publish the local receptionist prompts to the Opik global prompt library."
    )
    parser.add_argument(
        "--change-description",
        default="Refine spoken-phone behavior, multilingual boundaries, and smoother fallback guidance.",
        help="Version note stored on the created prompt versions.",
    )
    return parser


def main() -> int:
    if not settings.opik.api_key:
        raise ValueError("OPIK__API_KEY is required to sync prompts.")

    os.environ["OPIK_API_KEY"] = settings.opik.api_key
    if settings.opik.project_name:
        os.environ["OPIK_PROJECT_NAME"] = settings.opik.project_name

    client = opik_client.get_client_cached()
    prompts_client = client.get_prompts_client()
    args = build_parser().parse_args()

    refs = {
        "core": settings.prompts.core,
        "retrieval": settings.prompts.retrieval,
        "escalation": settings.prompts.escalation,
        "style": settings.prompts.style,
    }

    for key, ref in refs.items():
        version = prompts_client.create_prompt(
            name=ref.name,
            prompt=LOCAL_PROMPT_FALLBACKS[key],
            metadata={"component": key, "channel": "voice", "hotel": "blue-sardine"},
            description=PROMPT_DESCRIPTIONS[key],
            change_description=args.change_description,
            tags=["voice-agent", "hotel", "spoken"],
            project_name=None,
        )
        print(f"{key}: {ref.name} -> commit={getattr(version, 'commit', '')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
