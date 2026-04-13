# RunPod Deployment

## Primary topology

- One RunPod CPU pod for the main FastAPI/FastRTC app.
- Groq Whisper for STT.
- Mistral Voxtral for TTS.
- External Qdrant for retrieval.
- Twilio inbound webhook pointed to `/voice/telephone/incoming`.

## 1. Validate env

```bash
make validate-deploy-env
```

Optional outbound-call validation:

```bash
uv run python scripts/validate_deployment_env.py --include-outbound
```

## 2. Build and push the app image

```bash
make build-call-center-image
make push-call-center-image
```

`RUNPOD__CALL_CENTER_IMAGE_NAME` must match the image you push.

## 3. Create the RunPod CPU pod

```bash
make create-call-center-pod
```

The helper prints the expected public URL and reminds you to set:

```env
SERVER__PUBLIC_BASE_URL=https://<pod-id>-8000.proxy.runpod.net
```

## 4. Ingest hotel knowledge into Qdrant

Production should use explicit ingestion:

```bash
make ingest-hotel-kb
```

Keep:

```env
KNOWLEDGE_BASE__AUTO_INGEST_DEFAULT_BUNDLE=false
```

## 5. Configure Twilio

Set the Twilio inbound webhook to:

```text
https://<runpod-url>/voice/telephone/incoming
```

The app will:

1. Return a language-selection TwiML `<Gather>`.
2. Post the result to `/voice/telephone/language`.
3. Connect Twilio to `/voice-es/telephone/handler` or `/voice-en/telephone/handler`.

## 6. Trigger outbound calls locally

Outbound calling is intentionally a local CLI flow, not a public server endpoint:

```bash
make outbound-call
```

It uses local Twilio credentials and points Twilio back to the same deployed inbound route.

## Legacy fallbacks

These are not required for the primary deployment flow:

- `make create-faster-whisper-pod`
- `make create-orpheus-pod`
