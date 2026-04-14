<div align="center">
  <h1>☎️ Realtime Phone Agent ☎️</h1>
  <h3>Realtime AI voice agents with FastRTC, Superlinked, Twilio, Opik and Runpod</h3>
</div>

</br>

<p align="center">
    <img src="static/diagrams/system_architecture.png" alt="Architecture" width="600">
</p>

---

## The tech stack

<table>
  <tr>
    <th>Technology</th>
    <th>Description</th>
  </tr>
  <tr>
    <td><img src="static/fastrtc_logo.png" width="100" alt="FastRTC Logo"/></td>
    <td>The python library for real-time communication.
</td>
  </tr>
  <tr>
    <td><img src="static/superlinked_logo.png" width="100" alt="Superlinked Logo"/></td>
    <td>SSuperlinked is a Python framework for AI Engineers building high-performance search & recommendation applications that combine structured and unstructured data.

</td>
  </tr>
  <tr>
    <td><img src="static/runpod_logo.png" width="100" alt="Runpod Logo"/></td>
    <td>The end-to-end AI cloud that simplifies building and deploying models.</td>
  </tr>
  <tr>
    <td><img src="static/opik_logo.svg" width="100" alt="Opik Logo"/></td>
    <td>Debug, evaluate, and monitor your LLM applications, RAG systems, and agentic workflows with comprehensive tracing, automated evaluations, and production-ready dashboards.</td>
  </tr>
  <tr>
    <td><img src="static/twilio_logo.png" width="100" alt="Twilio Logo"/></td>
    <td>Twilio is a cloud communications platform that enables developers to build, manage, and automate voice, text, video, and other communication services through APIs.</td>
  </tr>
</table>

## Hotel KB + Prompts

The repo now ships with a hotel-specific Blue Sardine knowledge bundle at `data/blue_sardine_kb/2026-04-11`.

- Structured hotel facts stay loaded in memory for deterministic contact and policy fallbacks.
- Semantic facts, FAQs, operational notes, and dialogue exemplars are indexed through `Superlinked + Qdrant`.
- Prompt components are loaded remote-first from Opik and fall back to local prompt files if Opik is unavailable.

You can ingest the current bundle manually with:

```bash
uv run python scripts/ingest_hotel_kb.py
```

Key prompt and retrieval env vars:

```env
KNOWLEDGE_BASE__DEFAULT_BUNDLE_PATH=data/blue_sardine_kb/2026-04-11
KNOWLEDGE_BASE__COLLECTION_NAME=hotel-knowledge
PROMPTS__REMOTE_ENABLED=true
PROMPTS__CORE__NAME=blue_sardine.receptionist.core
PROMPTS__RETRIEVAL__NAME=blue_sardine.receptionist.retrieval
PROMPTS__ESCALATION__NAME=blue_sardine.receptionist.escalation
PROMPTS__STYLE__NAME=blue_sardine.receptionist.style
```

## Primary Deployment Architecture

The primary production path for this repo is now:

- Main app: one RunPod CPU pod running the FastAPI/FastRTC hotel receptionist.
- STT: Groq Whisper API via `STT_MODEL=whisper-groq`.
- TTS: ElevenLabs API via `TTS_MODEL=elevenlabs`.
- Retrieval: external Qdrant plus the bundled hotel KB.
- Observability: Opik prompt loading and tracing when configured.

Twilio should point inbound calls to:

```text
/voice/telephone/incoming
```

That route plays a short greeting and then connects the caller directly to the single Twilio media stream handler.

## Audio Routing

The voice stack supports these providers:

- STT: `moonshine`, `whisper-groq`, `faster-whisper`
- TTS: `elevenlabs`, `mistral-voxtral`, `kokoro`, `together`, `orpheus-runpod`

The production default is:

```env
STT_MODEL=whisper-groq
TTS_MODEL=elevenlabs
```

Lookup cues are no longer mandatory on every retrieval turn. The default behavior is direct and natural, with optional brief pauses controlled by:

```env
CALL_FLOW__TOOL_USE_PREAMBLE_MODE=auto
CALL_FLOW__LOOKUP_SOUND_MODE=auto
CALL_FLOW__LOOKUP_LATENCY_THRESHOLD_MS=1200
```

## Legacy Audio Pods

The repo still includes the older RunPod helpers for self-hosted Faster Whisper and Orpheus, but they are fallback paths only in this iteration:

- `make create-faster-whisper-pod`
- `make create-orpheus-pod`

They are no longer required for the primary deployment flow.

For the full env setup and RunPod helper commands, see [docs/GETTINGS_STARTED.md](docs/GETTINGS_STARTED.md).

## License

This project is licensed under the Apache License - see the [LICENSE](LICENSE) file for details.
