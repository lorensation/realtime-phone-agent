import runpod

from realtime_phone_agents.config import settings

if not settings.runpod.api_key:
    raise ValueError(
        "RunPod API key is required. Set RUNPOD__API_KEY in your environment."
    )

runpod.api_key = settings.runpod.api_key

print("Creating Faster Whisper pod...")
pod = runpod.create_pod(
    name="Faster Whisper Server",
    image_name="theneuralmaze/faster-whisper-server:latest",
    gpu_type_id=settings.runpod.faster_whisper_gpu_type,
    cloud_type="SECURE",
    gpu_count=1,
    volume_in_gb=20,
    volume_mount_path="/workspace",
    ports="8000/http",
)

pod_id = pod.get("id")
pod_url = f"https://{pod_id}-8000.proxy.runpod.net"

print(f"Pod created: {pod_id}")
print(f"Pod URL: {pod_url}")
print()
print("=" * 60)
print("Add the following to your .env file:")
print(f"FASTER_WHISPER__API_URL={pod_url}")
print("=" * 60)
