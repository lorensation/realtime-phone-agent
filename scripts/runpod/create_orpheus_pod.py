from dataclasses import dataclass

import runpod

from realtime_phone_agents.config import settings


@dataclass(frozen=True)
class OrpheusDeploymentConfig:
    hf_repo: str
    hf_file: str
    env_var_name: str
    voice: str
    ctx_size: str = "0"


ORPHEUS_ENGLISH_CONFIG = OrpheusDeploymentConfig(
    hf_repo="PkmX/orpheus-3b-0.1-ft-Q8_0-GGUF",
    hf_file="orpheus-3b-0.1-ft-q8_0.gguf",
    env_var_name="ORPHEUS__API_URL",
    voice="tara",
)


def get_orpheus_deployment_config() -> OrpheusDeploymentConfig:
    return ORPHEUS_ENGLISH_CONFIG


def build_orpheus_pod_request() -> dict:
    config = get_orpheus_deployment_config()
    return {
        "name": "Orpheus Server (english)",
        "image_name": settings.runpod.orpheus_image_name,
        "gpu_type_id": settings.runpod.orpheus_gpu_type,
        "cloud_type": "SECURE",
        "gpu_count": 1,
        "volume_in_gb": 20,
        "volume_mount_path": "/workspace",
        "ports": "8080/http",
        "env": {
            "LLAMA_ARG_HF_REPO": config.hf_repo,
            "LLAMA_ARG_HF_FILE": config.hf_file,
            "LLAMA_ARG_CTX_SIZE": config.ctx_size,
            "LLAMA_ARG_N_GPU_LAYERS": "-1",
        },
    }


def main() -> None:
    if not settings.runpod.api_key:
        raise ValueError(
            "RunPod API key is required. Set RUNPOD__API_KEY in your environment."
        )

    config = get_orpheus_deployment_config()
    pod_request = build_orpheus_pod_request()

    runpod.api_key = settings.runpod.api_key

    print("Creating English Orpheus pod...")
    pod = runpod.create_pod(**pod_request)

    pod_id = pod.get("id")
    pod_url = f"https://{pod_id}-8080.proxy.runpod.net"

    print(f"Pod created: {pod_id}")
    print(f"Pod URL: {pod_url}")
    print()
    print("=" * 60)
    print("Add the following to your .env file:")
    print(f"{config.env_var_name}={pod_url}")
    print(f"# Suggested voice for Orpheus English: {config.voice}")
    print("# Spanish TTS now uses ElevenLabs. No Spanish Orpheus pod is required.")
    print("=" * 60)


if __name__ == "__main__":
    main()
