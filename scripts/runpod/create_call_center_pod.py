from __future__ import annotations

import runpod

from realtime_phone_agents.config import settings


def _require(value: str, env_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{env_name} is required. Set it in your environment.")
    return cleaned


def build_call_center_env() -> dict[str, str]:
    return {
        "GROQ__API_KEY": settings.groq.api_key,
        "GROQ__BASE_URL": settings.groq.base_url,
        "GROQ__MODEL": settings.groq.model,
        "GROQ__STT_MODEL": settings.groq.stt_model,
        "OPENAI__API_KEY": settings.openai.api_key,
        "OPENAI__MODEL": settings.openai.model,
        "QDRANT__HOST": settings.qdrant.host,
        "QDRANT__PORT": str(settings.qdrant.port),
        "QDRANT__API_KEY": settings.qdrant.api_key,
        "QDRANT__USE_HTTPS": str(settings.qdrant.use_https).lower(),
        "KNOWLEDGE_BASE__DEFAULT_BUNDLE_PATH": settings.knowledge_base.default_bundle_path,
        "KNOWLEDGE_BASE__AUTO_INGEST_DEFAULT_BUNDLE": str(
            settings.knowledge_base.auto_ingest_default_bundle
        ).lower(),
        "KNOWLEDGE_BASE__COLLECTION_NAME": settings.knowledge_base.collection_name,
        "KNOWLEDGE_BASE__DEFAULT_HOTEL_ID": settings.knowledge_base.default_hotel_id,
        "OPIK__API_KEY": settings.opik.api_key,
        "OPIK__PROJECT_NAME": settings.opik.project_name,
        "PROMPTS__REMOTE_ENABLED": str(settings.prompts.remote_enabled).lower(),
        "PROMPTS__CORE__NAME": settings.prompts.core.name,
        "PROMPTS__CORE__COMMIT": settings.prompts.core.commit,
        "PROMPTS__RETRIEVAL__NAME": settings.prompts.retrieval.name,
        "PROMPTS__RETRIEVAL__COMMIT": settings.prompts.retrieval.commit,
        "PROMPTS__ESCALATION__NAME": settings.prompts.escalation.name,
        "PROMPTS__ESCALATION__COMMIT": settings.prompts.escalation.commit,
        "PROMPTS__STYLE__NAME": settings.prompts.style.name,
        "PROMPTS__STYLE__COMMIT": settings.prompts.style.commit,
        "CALL_FLOW__LANGUAGE_SELECTION_ENABLED": str(
            settings.call_flow.language_selection_enabled
        ).lower(),
        "CALL_FLOW__SELECTION_RETRY_LIMIT": str(
            settings.call_flow.selection_retry_limit
        ),
        "CALL_FLOW__RINGBACK_SECONDS": str(settings.call_flow.ringback_seconds),
        "CALL_FLOW__TOOL_USE_PREAMBLE_MODE": settings.call_flow.tool_use_preamble_mode,
        "CALL_FLOW__LOOKUP_SOUND_MODE": settings.call_flow.lookup_sound_mode,
        "CALL_FLOW__LOOKUP_LATENCY_THRESHOLD_MS": str(
            settings.call_flow.lookup_latency_threshold_ms
        ),
        "SERVER__PUBLIC_BASE_URL": settings.server.public_base_url,
        "STT_MODEL": settings.stt_model,
        "TTS_MODEL": settings.tts_model,
        "MISTRAL__API_KEY": settings.mistral.api_key,
        "MISTRAL__BASE_URL": settings.mistral.base_url,
        "MISTRAL__TTS_MODEL": settings.mistral.tts_model,
        "MISTRAL__VOICE_ID": settings.mistral.voice_id,
        "MISTRAL__VOICE_ID_EN": settings.mistral.voice_id_en,
        "MISTRAL__VOICE_ID_ES": settings.mistral.voice_id_es,
        "MISTRAL__RESPONSE_FORMAT": settings.mistral.response_format,
        "MISTRAL__SAMPLE_RATE_HZ": str(settings.mistral.sample_rate_hz),
    }


def build_call_center_pod_request() -> dict[str, object]:
    image_name = _require(
        settings.runpod.call_center_image_name, "RUNPOD__CALL_CENTER_IMAGE_NAME"
    )
    instance_id = _require(
        settings.runpod.call_center_instance_id, "RUNPOD__CALL_CENTER_INSTANCE_ID"
    )
    return {
        "name": "Hotel Receptionist Call Center",
        "image_name": image_name,
        "cloud_type": "SECURE",
        "volume_in_gb": settings.runpod.call_center_volume_gb,
        "volume_mount_path": settings.runpod.call_center_volume_mount_path,
        "instance_id": instance_id,
        "ports": "8000/http",
        "env": build_call_center_env(),
    }


def main() -> None:
    api_key = _require(settings.runpod.api_key, "RUNPOD__API_KEY")
    runpod.api_key = api_key

    print("Creating main call center CPU pod...")
    pod = runpod.create_pod(**build_call_center_pod_request())

    pod_id = pod.get("id")
    pod_url = f"https://{pod_id}-8000.proxy.runpod.net"

    print(f"Pod created: {pod_id}")
    print(f"Pod URL: {pod_url}")
    print()
    print("=" * 60)
    print("Recommended production values:")
    print(f"SERVER__PUBLIC_BASE_URL={pod_url}")
    print(f"# Twilio inbound webhook -> {pod_url}/voice/telephone/incoming")
    print("=" * 60)


if __name__ == "__main__":
    main()
