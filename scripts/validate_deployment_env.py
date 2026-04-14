from __future__ import annotations

import argparse

from realtime_phone_agents.config import settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate environment variables required for deployment."
    )
    parser.add_argument(
        "--include-outbound",
        action="store_true",
        help="Also validate Twilio credentials required by the outbound-call CLI.",
    )
    return parser


def _value_present(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    return value is not None


def _looks_like_placeholder_base_url(base_url: str) -> bool:
    normalized = (base_url or "").strip().upper()
    return any(
        marker in normalized
        for marker in ("YOUR-RUNPOD-URL", "<RUNPOD-URL>", "YOUR_PUBLIC_BASE_URL")
    )


def _validate_required_fields(include_outbound: bool) -> list[str]:
    errors: list[str] = []

    required_values = {
        "RUNPOD__API_KEY": settings.runpod.api_key,
        "RUNPOD__CALL_CENTER_IMAGE_NAME": settings.runpod.call_center_image_name,
        "RUNPOD__CALL_CENTER_INSTANCE_ID": settings.runpod.call_center_instance_id,
        "GROQ__API_KEY": settings.groq.api_key,
        "GROQ__MODEL": settings.groq.model,
        "ELEVENLABS__API_KEY": settings.elevenlabs.api_key,
        "ELEVENLABS__VOICE_ID / per-language override": settings.elevenlabs.voice_id
        or settings.elevenlabs.voice_id_en
        or settings.elevenlabs.voice_id_es,
        "OPENAI__API_KEY": settings.openai.api_key,
        "QDRANT__HOST": settings.qdrant.host,
        "QDRANT__PORT": settings.qdrant.port,
        "KNOWLEDGE_BASE__DEFAULT_BUNDLE_PATH": settings.knowledge_base.default_bundle_path,
        "KNOWLEDGE_BASE__COLLECTION_NAME": settings.knowledge_base.collection_name,
        "KNOWLEDGE_BASE__DEFAULT_HOTEL_ID": settings.knowledge_base.default_hotel_id,
    }

    for env_name, value in required_values.items():
        if not _value_present(value):
            errors.append(f"Missing required setting: {env_name}")

    if settings.server.public_base_url and _looks_like_placeholder_base_url(
        settings.server.public_base_url
    ):
        errors.append(
            "SERVER__PUBLIC_BASE_URL must be set to a real deployed HTTPS URL, not the example placeholder."
        )

    if settings.stt_model != "whisper-groq":
        errors.append(
            f"STT_MODEL must be 'whisper-groq' for the primary deployment path, got '{settings.stt_model}'."
        )
    if settings.tts_model != "elevenlabs":
        errors.append(
            f"TTS_MODEL must be 'elevenlabs' for the primary deployment path, got '{settings.tts_model}'."
        )
    if settings.knowledge_base.auto_ingest_default_bundle:
        errors.append(
            "KNOWLEDGE_BASE__AUTO_INGEST_DEFAULT_BUNDLE must be false for the explicit-ingest production flow."
        )

    if include_outbound:
        if not settings.twilio.account_sid:
            errors.append("Missing required setting: TWILIO__ACCOUNT_SID")
        if not settings.twilio.auth_token:
            errors.append("Missing required setting: TWILIO__AUTH_TOKEN")

    return errors


def main() -> int:
    args = build_parser().parse_args()
    errors = _validate_required_fields(include_outbound=args.include_outbound)
    if errors:
        print("Deployment environment validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Deployment environment validation passed.")
    print(f"- STT_MODEL={settings.stt_model}")
    print(f"- TTS_MODEL={settings.tts_model}")
    print(f"- RunPod image={settings.runpod.call_center_image_name}")
    print(
        f"- Public base URL={settings.server.public_base_url or '(blank; forwarded headers will be used)'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
