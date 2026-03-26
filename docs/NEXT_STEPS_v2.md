# Integración de TTS es-ES y hardening de un phone agent realtime con Twilio, FastRTC y Opik

## Resumen ejecutivo

Tu repo ya tiene un “skeleton” funcional de voice agent con FastRTC + Twilio: montas un `Stream` en FastAPI y reemplazas el endpoint de inbound de teléfono para devolver TwiML con `<Connect><Stream>` hacia `/voice/telephone/handler`. En paralelo, el agente encapsula STT → LangChain agent (tools/RAG) → TTS y soporta un flujo de selección de idioma (inglés/español) al inicio de la llamada, pero está deshabilitado por defecto y depende de `startup_fn` + detección por STT/LLM. 

Los dos problemas que describes (“intro/idioma no se reproduce bien” y “las respuestas se cortan cuando son largas”) encajan con **tres causas dominantes**:

1) **El flujo actual de Twilio no fuerza un paso de selección de idioma antes de conectar el stream**, porque el TwiML actual solo conecta con `<Connect><Stream>` sin `<Gather>`; por tanto dependes de un `startup_fn` que puede **no ejecutarse como esperas** o ser interrumpido si `can_interrupt=True`.

2) **Barge-in / interrupciones**: `ReplyOnPause` permite interrupción (`can_interrupt=True` por defecto). Si Twilio introduce audio temprano (ruido de línea, DTMF, speech, “hello?”), el sistema puede cortar el greeting/idioma o cortar TTS a mitad. 

3) **Mismatch de formato/ritmo de audio y buffers en telefonía**: Twilio Media Streams es **audio/x-mulaw, 8kHz, mono**; al enviar audio de vuelta debes mandar **mulaw/8000 en base64 y sin headers de archivo**, y Twilio “bufferiza” los `media` en orden. Si tu pipeline genera 16k/24k y no controlas suficientemente el troceado, la latencia/cola y el “clear/mark” pueden provocar sensación de corte (o el usuario interrumpe sin querer). 

Recomendación central: **hacer la selección de idioma determinista con TwiML `<Gather>` antes de `<Connect><Stream>`** y montar **dos streams** (ES/EN) en dos paths distintos, evitando depender del `startup_fn` para el idioma. Esto además simplifica elegir TTS por idioma y reduce edge-cases de interrupción. Para español, integrar **ElevenLabs Flash v2.5** con la voz “Beatriz” (voice id proporcionado) usando endpoint **streaming** y `output_format=ulaw_8000` (o PCM + resample) para telefonía. ElevenLabs recomienda Flash para latencia (~75ms de inferencia) y streaming para reducir TTFB.  Mantener Orpheus para inglés como ya tienes (RunPod o Together).

Finalmente, **no automatizar ingestión de conversación→KB**: es arriesgado para un hotel (alucinaciones, PII, drift y “ensuciar” la base de conocimiento). En su lugar, usar Opik para **versionado y observabilidad de prompts** (como en el repo del curso) y dejar KB updates a un pipeline curado/humano. El curso trae utilidades concretas de Opik (`configure()` y `Prompt`) pensadas para fallback seguro si faltan credenciales.

## Necesidades de información

Para responder y diseñar la integración “de verdad” (robusta y coste-efectiva) hacen falta estas 6 piezas de información:

1) **Tráfico esperado**: llamadas simultáneas pico (p99) y duración media → dimensiona TTS/LLM, concurrencia y coste (API vs self-host).  
2) **Topología de despliegue**: dónde corre FastAPI (región), si hay GPU, si hay límites de egress y latencia a APIs (ElevenLabs).  
3) **Requisitos de privacidad**: ¿se puede almacenar transcripción? ¿se puede enviar a Opik / terceros? (impacta logging, retención). ElevenLabs “zero retention” está ligado a enterprise según su propia documentación.   
4) **Formato de audio real del tramo Twilio↔servidor** en tu implementación (FastRTC suele abstraer, pero Twilio exige mulaw/8k).   
5) **Conjunto de intents del hotel** (reservas, check-in/out, late checkout, política, upsell) y boundaries (qué no hace) → afecta prompt y truncation.  
6) **Coste objetivo** (€/mes) o al menos preferencia API vs self-host (RunPod/Together) → define cuál TTS conviene en ES/EN.

## Estado actual del repositorio y puntos exactos de cambio

### Dónde se rompe hoy el “idioma al inicio” (Twilio)

En tu endpoint de inbound telefónico, el TwiML que devuelves es esencialmente:

- `<Response><Connect><Stream url="wss://.../voice/telephone/handler"/></Connect></Response>` (sin `<Gather>` ni `<Say>`).
- Eso hace que la selección de idioma dependa de tu agente y de que `startup_fn` esté configurado. En tu agente, ese comportamiento está condicionado por `call_flow.language_selection_enabled`.
- `ReplyOnPause` soporta `startup_fn`, pero por defecto permite interrupción (`can_interrupt=True`) y puede parar el generador si entra audio durante la reproducción.

**Por qué esto se traduce en “no se genera bien la introducción”**: en telefonía real es común que el caller hable inmediatamente (“hola?”) o haya audio residual; si el handler permite interrupción, el greeting se corta. Además, si `language_selection_enabled` no está activo en `.env`, no hay greeting en absoluto.

### Dónde se rompe hoy el “se corta la respuesta” (TTS / buffering)

Tienes varios puntos donde esto puede pasar:

- **Interrupción por VAD** en medio de la reproducción (mismo `can_interrupt`).
- **Límites/segmentación del modelo TTS**: Orpheus en tu config tiene `max_tokens` y `sample_rate=24000`; si el texto es largo o el backend corta por límites, notarás truncation.
- **Telefonía exige mulaw/8k**: Twilio indica explícitamente `audio/x-mulaw` a 8000Hz y advierte no incluir headers de audio al mandar `media.payload`. Si no controlas el formato o envías chunks demasiado grandes, la reproducción puede degradarse.
- **Tu route de app y montaje**: montas el voice stream en `api/main.py` vía `mount_voice_stream(app)`. Esto es el sitio correcto para añadir inicialización de Opik en lifespan.

### Dónde insertar Opik “como en el curso”

El repositorio del curso implementa:

- `observability/opik_utils.py` con `configure()` que lee settings, setea `OPIK_PROJECT_NAME` y llama a `opik.configure(...)`.  
- `observability/prompt_versioning.py` con clase `Prompt` que intenta crear `opik.Prompt` y hace fallback a string si falla.
- Un ejemplo de integración en el agente usando `OpikTracer` (callbacks de LangChain) y decoradores `@opik.track`.

La parte útil para tu objetivo (versionado de prompt, SIN “memoria conversacional”) es **Prompt + configure**; el tracer es opcional y debe configurarse para **no capturar PII** si así lo quieres (ver sección de honestidad sobre almacenamiento).

image_group{"layout":"carousel","aspect_ratio":"16:9","query":["Twilio Media Streams websocket audio mulaw 8000 architecture diagram","FastRTC ReplyOnPause startup_fn can_interrupt diagram","ElevenLabs Flash v2.5 streaming text to speech diagram"],"num_per_query":1}

## Arquitectura objetivo y call flow recomendado

### Call flow recomendado

- **Inbound Twilio → Webhook**: tu FastAPI recibe la llamada.
- **TwiML `<Gather>`** (DTMF + opcional speech) para elegir idioma.
- Según idioma, TwiML **conecta a un stream distinto**:
  - Español → `/voice-es/telephone/handler`
  - Inglés → `/voice-en/telephone/handler`
- Dentro de cada stream:
  - STT → LLM agent con KB → chunking de texto → TTS (ElevenLabs Flash 2.5 ES / Orpheus EN) → audio hacia Twilio.

Esto evita depender de customParameters del WebSocket y evita el problema de que el atributo `url` de `<Stream>` no soporta query string; Twilio dice que para pasar pares clave/valor uses “Custom Parameters” (nouns anidados) en vez de query params. 

### Mermaid del flujo

```mermaid
flowchart LR
  A[Caller] --> B[Twilio Voice]
  B --> C[Webhook /voice/telephone/incoming]
  C --> D{TwiML Gather\nIdioma: 1=ES, 2=EN\n(o speech)}
  D -->|ES| E[<Connect><Stream>\nwss://.../voice-es/telephone/handler]
  D -->|EN| F[<Connect><Stream>\nwss://.../voice-en/telephone/handler]
  E --> G[FastRTC WebSocket handler]
  F --> G
  G --> H[STT]
  H --> I[LLM Agent + KB tool]
  I --> J[Chunking & turn-taking rules]
  J --> K{TTS Provider}
  K -->|ES| L[ElevenLabs Flash v2.5\nVoice: Beatriz]
  K -->|EN| M[Orpheus (RunPod/TogetherAI)]
  L --> N[Audio normalize\n(8kHz μ-law for Twilio)]
  M --> N
  N --> B
```

Twilio Media Streams confirma que el audio en los mensajes `start.mediaFormat` es siempre `audio/x-mulaw` a 8000Hz y que el audio que envías de vuelta debe ser mulaw/8000 base64 sin headers. 

### Opción recomendada “cost-effective + low latency” para español

**ElevenLabs Flash v2.5** está documentado como modelo “rápido y asequible”, con latencia de inferencia ~75ms y pensado para escenarios en tiempo real; además recomiendan usar **streaming** para reducir time-to-first-byte. En su “cookbook” de Twilio muestran explícitamente `outputFormat = 'ulaw_8000'`, lo cual reduce fricción con Twilio (mulaw/8k). 

**Coste**: ElevenLabs ha migrado nomenclatura de “characters” a “credits”; para Flash/Turbo indican 1 carácter = 0.5 créditos en planes self-serve (y puede variar en enterprise).  Esto es relevante porque tu caso (recepción 24/7) es de texto corto–medio pero continuo, y Flash v2.5 está justamente optimizado para ese patrón (agents).

### Nota importante sobre números y hotelería

ElevenLabs documenta que en Flash v2.5 la normalización de números puede no ser la esperada (teléfonos, fechas, divisas), y recomiendan que el LLM normalice antes o usar `apply_text_normalization` (enterprise).   
Esto impacta directamente al caso “recepcionista”: horarios, noches, tarifas, números de habitación. La solución práctica: **reformar el system prompt** para que el LLM convierta números a forma hablada en el idioma seleccionado (ver fixes).

## Fixes concretos y diseño honesto sobre “memoria → KB”

### Fix A: El greeting/idioma en Twilio no se reproduce

**Solución robusta (recomendada): TwiML `<Gather>` antes de `<Connect><Stream>`**

- `<Gather>` está diseñado para recoger dígitos o speech (o ambos) durante la llamada.   
- Tras el gather, devuelves TwiML que conecta con el stream correcto.  
- Esto evita el edge-case de `startup_fn` interrumpido (porque el greeting lo hace Twilio con `<Say>` dentro del Gather, no tu TTS). 

**Solución alternativa (si quieres greeting con tu propia voz): `startup_fn` + `can_interrupt=False`**

FastRTC permite `startup_fn` en `ReplyOnPause` y el flag `can_interrupt` para evitar que audio entrante pare el generador.   
Esta opción mantiene la voz “Beatriz/Orpheus” desde el primer segundo, pero sacrifica “barge-in” (que en atención telefónica muchas veces es aceptable).

### Fix B: El TTS corta respuestas largas

Necesitas atacar esto desde 3 capas:

1) **Turn-taking**: desactivar interrupción durante TTS largo (o al menos durante ciertos estados). `ReplyOnPause` lo soporta globalmente.   
2) **Chunking**: dividir texto en trozos pequeños (por frases) y emitir audio en stream por segmento. Esto reduce buffers, baja TTFB y limita el daño si algún segmento falla. ElevenLabs además ofrece parámetros como `previous_text`, `next_text` para continuidad al concatenar; su endpoint de streaming lo menciona como mecanismo para continuidad.   
3) **Prompting**: forzar respuestas “phone-first” (estructuradas, concisas, con offer de continuar si quieres más detalle). Esto reduce el riesgo de producir textos de 800–1500 palabras que nadie escucha en una llamada.

Además, en telefonía la codificación correcta importa: Twilio exige mulaw/8k, base64, sin headers.  Si dependes de conversión implícita, al menos debes testear que toda la cadena preserve el sample rate y que no introduces WAV headers.

### Fix C: “No session memory → KB ingestion” (honestidad)

**No recomiendo** un sistema automático que “al final de la sesión” meta conversaciones a la base de conocimiento del hotel, salvo que:

- tengas **extracción estructurada** (slots verificados),
- **filtros de privacidad/PII**, y
- **revisión humana** antes de publicar.

Por qué: un recepcionista automático gestiona información muy susceptible de error (tarifas, disponibilidad, políticas) y la conversación puede contener “suposiciones” del usuario; si lo metes a KB, conviertes ruido en verdad. Además, legal/privacidad. Twilio + STT + LLM ya son una cadena sensible.

Lo que sí es útil (y más seguro) es:
- registrar **telemetría y versiones de prompt** para iterar, sin convertir conversaciones en “hechos”. Ahí encaja Opik. El curso implementa `Prompt` para versionado (fallback local) y `configure()` para activar Opik con variables de entorno. 

Ojo: si habilitas tracing completo tipo `OpikTracer` y `@opik.track`, estás (potencialmente) guardando transcripciones outputs. El curso muestra esa integración. Si tu requerimiento real es *“no guardar conversaciones”*, debes configurar Opik para no capturar input/output (o capturar solo métricas agregadas), y/o no instrumentar transcripciones.

## Objetivo de implementación

- Añadir un proveedor TTS español basado en ElevenLabs Flash v2.5 con voz Beatriz (`voice_id = gJlzF5JxsCvM5hQAoRyD`) usando streaming.
- Mantener Orpheus para inglés (RunPod o Together) como está hoy.
- Hacer selección de idioma al inicio de la llamada vía TwiML `<Gather>` (robusta).
- Mitigar truncation vía chunking + ajustes `can_interrupt`.
- Integrar Opik para versionado de prompts copiando la implementación del curso (`opik_utils.py`, `prompt_versioning.py`).

### Variables de entorno a añadir

Añadir a `.env` (nombres estilo pydantic `env_nested_delimiter="__"` como ya usas en settings del repo)

- `ELEVENLABS__API_KEY=...`
- `ELEVENLABS__MODEL_ID=eleven_flash_v2_5`  (modelo recomendado para realtime)
- `ELEVENLABS__VOICE_ID_ES=gJlzF5JxsCvM5hQAoRyD`
- `ELEVENLABS__OUTPUT_FORMAT=ulaw_8000` (ideal Twilio) 
- `OPIK__API_KEY=...`
- `OPIK__PROJECT_NAME=blue-sardine-hotel` (o el nombre que definas)

Opcional (si mantienes `startup_fn`):
- `CALL_FLOW__LANGUAGE_SELECTION_ENABLED=false` (lo apagamos porque gather decide)

### Patch 1: Añadir módulo de observabilidad (Opik) y activarlo en `lifespan`

**Crear archivos nuevos (copiados del curso, con mínimos ajustes de imports si hace falta):**

- `src/realtime_phone_agents/observability/opik_utils.py` (basado en curso) 
- `src/realtime_phone_agents/observability/prompt_versioning.py` (basado en curso) 
- `src/realtime_phone_agents/observability/__init__.py` (puede estar vacío)

**Modificar `src/realtime_phone_agents/api/main.py` para configurar Opik en startup**

```diff
diff --git a/src/realtime_phone_agents/api/main.py b/src/realtime_phone_agents/api/main.py
index 9c81fa1..XXXXXXX 100644
--- a/src/realtime_phone_agents/api/main.py
+++ b/src/realtime_phone_agents/api/main.py
@@ -1,6 +1,7 @@
 from contextlib import asynccontextmanager
 
 from fastapi import FastAPI
 from fastapi.middleware.cors import CORSMiddleware
 
+from realtime_phone_agents.observability.opik_utils import configure as configure_opik
 from realtime_phone_agents.infrastructure.superlinked.service import (
     get_knowledge_search_service,
 )
@@ -10,10 +11,14 @@ from realtime_phone_agents.api.routes.voice import mount_voice_stream
 
 
 @asynccontextmanager
 async def lifespan(app: FastAPI):
     """Manage application lifespan - startup and shutdown events."""
+    # Observability: prompt versioning + (optional) tracing
+    configure_opik()
+
     app.state.knowledge_service = get_knowledge_search_service()
     yield
     # Shutdown: Cleanup if needed
```

### Patch 2: Añadir settings ElevenLabs + Opik en `config.py`

Modificar `src/realtime_phone_agents/config.py` para añadir `ElevenLabsSettings` y `OpikSettings` (patrón del curso). 

```diff
diff --git a/src/realtime_phone_agents/config.py b/src/realtime_phone_agents/config.py
index XXXXXXX..YYYYYYY 100644
--- a/src/realtime_phone_agents/config.py
+++ b/src/realtime_phone_agents/config.py
@@ -1,6 +1,7 @@
 from typing import ClassVar
 
 from pydantic import BaseModel, Field
 from pydantic_settings import BaseSettings, SettingsConfigDict
 
@@
 class TogetherTTSSettings(BaseModel):
@@
     sample_rate: int = Field(default=24000, description="Audio sample rate (Hz)")
 
+class ElevenLabsSettings(BaseModel):
+    api_key: str = Field(default="", description="ElevenLabs API Key")
+    model_id: str = Field(default="eleven_flash_v2_5", description="ElevenLabs TTS model id")
+    voice_id_es: str = Field(default="", description="ElevenLabs voice id for Spanish (es-ES)")
+    output_format: str = Field(default="ulaw_8000", description="ElevenLabs output format (Twilio-friendly)")
+
+class OpikSettings(BaseModel):
+    api_key: str = Field(default="", description="Opik API Key")
+    project_name: str = Field(default="", description="Opik Project Name")
+
 class Settings(BaseSettings):
@@
     together: TogetherTTSSettings = Field(default_factory=TogetherTTSSettings)
+    elevenlabs: ElevenLabsSettings = Field(default_factory=ElevenLabsSettings)
+    opik: OpikSettings = Field(default_factory=OpikSettings)
```

### Patch 3: Implementar TTS ElevenLabs (streaming) como provider

Crear archivo nuevo: `src/realtime_phone_agents/tts/elevenlabs/model.py`

Requisitos funcionales basados en docs oficiales:

- Endpoint streaming: `POST https://api.elevenlabs.io/v1/text-to-speech/:voice_id/stream`   
- Recomendación de Flash + streaming para latencia   
- Cookbook Twilio con `outputFormat='ulaw_8000'`   

**Implementación sugerida (httpx async streaming):**

```python
# src/realtime_phone_agents/tts/elevenlabs/model.py
from __future__ import annotations

import asyncio
import base64
from typing import AsyncIterator, Optional

import httpx
import numpy as np

from realtime_phone_agents.config import settings
from realtime_phone_agents.tts.base import TTSModel, AudioChunk

ELEVEN_TTS_STREAM_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"

class ElevenLabsTTSModel(TTSModel):
    """
    ElevenLabs streaming TTS wrapper.
    - Designed for telephony: request output_format=ulaw_8000 when possible.
    - If ulaw_8000 is returned, we decode to int16 PCM for the rest of the pipeline
      (or you can refactor pipeline to send ulaw bytes directly to Twilio).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_id: Optional[str] = None,
        voice_id: Optional[str] = None,
        output_format: Optional[str] = None,
        language_code: str = "es",
    ):
        self.api_key = api_key or settings.elevenlabs.api_key
        self.model_id = model_id or settings.elevenlabs.model_id
        self.voice_id = voice_id or settings.elevenlabs.voice_id_es
        self.output_format = output_format or settings.elevenlabs.output_format
        self.language_code = language_code

        if not self.api_key:
            raise ValueError("Missing ELEVENLABS__API_KEY")
        if not self.voice_id:
            raise ValueError("Missing ELEVENLABS__VOICE_ID_ES")

    async def stream_tts(self, text: str, **kwargs) -> AsyncIterator[AudioChunk]:
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",  # server will return audio bytes regardless; keep permissive
        }

        params = {
            "output_format": self.output_format,
            # optimize_streaming_latency is documented but deprecated; still widely used.
            # Keep it optional to avoid surprises.
        }

        payload = {
            "text": text,
            "model_id": self.model_id,
            "language_code": self.language_code,
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=30.0)) as client:
            async with client.stream(
                "POST",
                ELEVEN_TTS_STREAM_URL.format(voice_id=self.voice_id),
                headers=headers,
                params=params,
                json=payload,
            ) as resp:
                resp.raise_for_status()

                # If output_format is ulaw_8000: you receive raw μ-law bytes.
                # Convert to int16 PCM so the rest of the app (FastRTC) can resample/encode as needed.
                async for chunk in resp.aiter_bytes():
                    if not chunk:
                        continue

                    # Decode μ-law (u-law) 8k to 16-bit PCM using audioop if you want.
                    # Here we assume ulaw_8000 and yield as 8k int16 frames.
                    pcm = ulaw_bytes_to_int16(chunk)
                    yield (8000, pcm)

                    await asyncio.sleep(0)

    def tts(self, text: str, **kwargs) -> AudioChunk:
        # For this project we prefer streaming always. Implement non-streaming if needed.
        raise NotImplementedError("Use stream_tts() for ElevenLabs to minimize latency.")
```

Y añade helpers (en un nuevo archivo o dentro del mismo módulo):

```python
import audioop
import numpy as np

def ulaw_bytes_to_int16(ulaw_bytes: bytes) -> np.ndarray:
    # audioop.ulaw2lin returns bytes of linear PCM
    lin = audioop.ulaw2lin(ulaw_bytes, 2)  # 2 bytes width => int16
    return np.frombuffer(lin, dtype=np.int16)
```

### Patch 4: Enganchar ElevenLabs en el factory `get_tts_model`

Modificar `src/realtime_phone_agents/tts/utils.py` para incluir un `model_name` nuevo, p.ej. `"elevenlabs-flash-es"`.

```diff
diff --git a/src/realtime_phone_agents/tts/utils.py b/src/realtime_phone_agents/tts/utils.py
index XXXXXXX..YYYYYYY 100644
--- a/src/realtime_phone_agents/tts/utils.py
+++ b/src/realtime_phone_agents/tts/utils.py
@@
 from realtime_phone_agents.tts.local.kokoro import KokoroTTSModel
 from realtime_phone_agents.tts.runpod.orpheus.model import OrpheusTTSModel
 from realtime_phone_agents.tts.togetherai.model import TogetherTTSModel
+from realtime_phone_agents.tts.elevenlabs.model import ElevenLabsTTSModel
 
 def get_tts_model(model_name: str | None = None):
@@
     if model_name in ("kokoro", "local-kokoro"):
         return KokoroTTSModel()
     if model_name in ("orpheus-runpod", "runpod-orpheus"):
         return OrpheusTTSModel()
     if model_name in ("together", "togetherai"):
         return TogetherTTSModel()
+    if model_name in ("elevenlabs-flash-es", "elevenlabs-es"):
+        return ElevenLabsTTSModel()
 
     raise ValueError(f"Unsupported TTS model: {model_name}")
```

### Patch 5: Selección de idioma en Twilio vía `<Gather>` y streams separados

Modificar `src/realtime_phone_agents/api/routes/voice.py` (donde hoy reemplazas el endpoint inbound) para:

- Montar **dos agentes/streams** (`/voice-en`, `/voice-es`)  
- Cambiar `/voice/telephone/incoming` para devolver TwiML con `<Gather>` y un `action=/voice/telephone/language`  
- Crear un nuevo endpoint `/voice/telephone/language` que devuelve TwiML conectando al handler correcto

**Contexto actual**: hoy solo conectas el stream directamente. 

```diff
diff --git a/src/realtime_phone_agents/api/routes/voice.py b/src/realtime_phone_agents/api/routes/voice.py
index XXXXXXX..YYYYYYY 100644
--- a/src/realtime_phone_agents/api/routes/voice.py
+++ b/src/realtime_phone_agents/api/routes/voice.py
@@
-from realtime_phone_agents.agent.fastrtc_agent import FastRTCAgent
+from realtime_phone_agents.agent.fastrtc_agent import FastRTCAgent
+from realtime_phone_agents.tts import get_tts_model
+from realtime_phone_agents.config import settings
 
 def mount_voice_stream(app: FastAPI):
-    agent = FastRTCAgent(...)
-    stream = agent.stream
-    stream.mount(app, path="/voice", tags=["voice"])
+    # Mount EN stream
+    agent_en = FastRTCAgent(
+        # Keep your existing defaults for EN
+        tts_model=get_tts_model(settings.tts_model),
+        system_prompt=DEFAULT_SYSTEM_PROMPT_EN,  # define prompts
+    )
+    agent_en.stream.mount(app, path="/voice-en", tags=["voice"])
+
+    # Mount ES stream (ElevenLabs)
+    agent_es = FastRTCAgent(
+        tts_model=get_tts_model("elevenlabs-flash-es"),
+        system_prompt=DEFAULT_SYSTEM_PROMPT_ES,
+    )
+    agent_es.stream.mount(app, path="/voice-es", tags=["voice"])
 
     _replace_telephone_incoming_route(app)
 
@@
 @router.api_route("/voice/telephone/incoming", methods=["GET", "POST"])
 async def incoming_telephone_call(request: Request):
-    # old: immediate connect
-    return Response(content=_build_telephone_twiml(request), media_type="text/xml")
+    # new: ask language first (DTMF 1/2; speech optional)
+    return Response(content=_build_language_gather_twiml(request), media_type="text/xml")
+
+@router.post("/voice/telephone/language")
+async def select_language(request: Request):
+    form = await request.form()
+    digits = (form.get("Digits") or "").strip()
+    speech = (form.get("SpeechResult") or "").strip().lower()
+
+    # Decide language
+    lang = "es" if digits == "1" or "españ" in speech or "spanish" in speech else "en"
+    return Response(content=_build_connect_twiml(request, lang=lang), media_type="text/xml")
 
 def _build_language_gather_twiml(request: Request) -> str:
+    # Twilio <Gather> supports speech/digits. Use digits for robustness. 
+    action_url = _abs_url(request, "/voice/telephone/language")
+    return f"""<?xml version="1.0" encoding="UTF-8"?>
+<Response>
+  <Gather input="dtmf speech" numDigits="1" timeout="6" action="{action_url}" method="POST" language="es-ES">
+    <Say language="es-ES">Bienvenido. Para español, pulse 1. Para inglés, pulse 2.</Say>
+    <Say language="en-US">Welcome. For Spanish press 1. For English press 2.</Say>
+  </Gather>
+  <Say language="es-ES">No he recibido respuesta. Reintentando.</Say>
+  <Redirect>{_abs_url(request, "/voice/telephone/incoming")}</Redirect>
+</Response>"""
+
+def _build_connect_twiml(request: Request, lang: str) -> str:
+    # Twilio <Stream> url cannot have query strings; use different paths. 
+    stream_path = "/voice-es/telephone/handler" if lang == "es" else "/voice-en/telephone/handler"
+    stream_url = _wss_url(request, stream_path)
+    return f"""<?xml version="1.0" encoding="UTF-8"?>
+<Response>
+  <Connect>
+    <Stream url="{stream_url}" />
+  </Connect>
+</Response>"""
```

**Notas**:
- La doc de Twilio indica que el payload de vuelta debe ser mulaw/8000 y sin headers.   
- Este diseño evita depender de `customParameters` de `<Stream>`, aunque Twilio soporta custom parameters anidados si los necesitas. 

### Patch 6: Chunking + can_interrupt + prompt “phone-first” para evitar truncation

Modificar `src/realtime_phone_agents/agent/fastrtc_agent.py`:

- Construir el stream con `ReplyOnPause(... can_interrupt=False)` cuando estás en modo “telefonía” (o siempre, si tu producto es exclusivamente phone).   
- Implementar `chunk_text()` y hacer que `_synthesize_text_with_model` sintetice por chunks.
- Ajustar prompts para:
  - respuestas por frases cortas,
  - enumeraciones,
  - “si quieres más detalle, dímelo”.

Ejemplo de chunking:

```python
import re
from typing import Iterable

_SENT_SPLIT = re.compile(r"(?<=[\.\!\?])\s+")

def chunk_text(text: str, max_chars: int = 240) -> Iterable[str]:
    text = (text or "").strip()
    if len(text) <= max_chars:
        if text:
            yield text
        return

    parts = _SENT_SPLIT.split(text)
    buf = ""
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if len(buf) + len(p) + 1 <= max_chars:
            buf = (buf + " " + p).strip()
        else:
            if buf:
                yield buf
            buf = p
    if buf:
        yield buf
```

Luego en tu síntesis:

```python
async def _synthesize_text_with_model(self, text: str, model):
    for segment in chunk_text(text, max_chars=240):
        async for audio_chunk in model.stream_tts(segment):
            yield audio_chunk
```

**Prompting recomendado (resumen, incrustar en tu `DEFAULT_SYSTEM_PROMPT_ES/EN`)**:

- “Habla como recepcionista: frases cortas, 1 idea por frase.”  
- “Si la respuesta supera ~20 segundos, da un resumen y pregunta si el cliente quiere detalles.”  
- “Normaliza números: di ‘veinticuatro horas’ en vez de ‘24h’; di el teléfono separando dígitos.” (especialmente importante con Flash v2.5).   

### Snippets requeridos (según tu checklist)

#### TwiML pre-gather (mínimo viable)

```xml
<Response>
  <Gather input="dtmf" numDigits="1" timeout="6" action="/voice/telephone/language" method="POST">
    <Say language="es-ES">Para español, pulse 1. Para inglés, pulse 2.</Say>
  </Gather>
  <Redirect>/voice/telephone/incoming</Redirect>
</Response>
```

#### `startup_fn` con `can_interrupt=False` (alternativa)

FastRTC documenta explícitamente `startup_fn` y `can_interrupt`. 

```python
from fastrtc import ReplyOnPause

handler = ReplyOnPause(
    fn=handler_wrapper,
    startup_fn=startup_prompt_fn,
    can_interrupt=False,
)
```

#### Llamada ElevenLabs (HTTP streaming) con voice id

El endpoint de streaming está documentado como `/v1/text-to-speech/:voice_id/stream`. 

```python
import httpx

async with httpx.AsyncClient() as client:
    async with client.stream(
        "POST",
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        params={"output_format": "ulaw_8000"},
        json={"text": text, "model_id": "eleven_flash_v2_5", "language_code": "es"},
    ) as resp:
        resp.raise_for_status()
        async for b in resp.aiter_bytes():
            ...
```

ElevenLabs muestra `ulaw_8000` como formato práctico para Twilio en su cookbook. 

#### Resampling a 8k μ-law (si lo necesitas explícito)

Twilio exige `mulaw/8000` para `media.payload`. 

```python
import audioop
import numpy as np

def pcm16_to_ulaw8k(pcm: np.ndarray, src_rate: int) -> bytes:
    # pcm: int16 mono
    pcm_bytes = pcm.astype(np.int16, copy=False).tobytes()
    if src_rate != 8000:
        pcm_bytes, _ = audioop.ratecv(pcm_bytes, 2, 1, src_rate, 8000, None)
    ulaw = audioop.lin2ulaw(pcm_bytes, 2)
    return ulaw
```

#### Factory `get_tts_model` (ya incluido en Patch 4)

(Ver Patch 4.)

### Tests mínimos (pytest)

1) `test_chunk_text_max_chars`: asegura que ningún chunk exceda `max_chars`.  
2) `test_twiml_language_gather_contains_gather`: el endpoint `/voice/telephone/incoming` devuelve `<Gather>` y `action` correcto.  
3) `test_twiml_routes_choose_voice_es_en`: `/voice/telephone/language` con `Digits=1` conecta a `/voice-es/telephone/handler`, con `Digits=2` a `/voice-en/telephone/handler`.

### Criterios de aceptación (verificables)

- Al llamar al número de Twilio, el caller escucha el prompt de idioma y puede seleccionar 1/2; Twilio ejecuta `<Gather>` (sin conectar stream todavía).   
- Si elige 1, el stream se conecta a `/voice-es/telephone/handler` y el TTS sale con ElevenLabs Flash v2.5 (Beatriz). ElevenLabs Flash v2.5 está recomendado para realtime y streaming.   
- Si elige 2, se conecta a `/voice-en/telephone/handler` y se mantiene Orpheus tal como hoy. 
- Para una respuesta “larga” (p.ej. 60–90 segundos de locución), el agente **no corta**: se emiten múltiples chunks TTS y el audio llega completo (sin interrupción involuntaria). `ReplyOnPause.can_interrupt` está documentado para controlar esto.   
- Opik queda configurado en startup y el prompt queda envuelto en `Prompt(name=..., prompt=...)` con fallback local si no hay credenciales.

### Nota final sobre costes (para tu argumentario comercial)

- ElevenLabs Flash v2.5: optimizado para latencia (~75ms) y “más barato por carácter”; su help indica que Flash/Turbo suelen costar 0.5 créditos por carácter en planes self-serve.  
- Orpheus self-host: RunPod publica precios indicativos por hora (4090/5090). Útil si quieres coste fijo por hora vs coste por carácter.   
- Orpheus en TogetherAI: pricing directo $15 por 1M caracteres (y documentación de modelos y streaming).   

Esto te permite presentar al hotel (y a ti mismo) dos estrategias:
- **API-first** (ElevenLabs ES + Together/Orpheus EN): coste variable por uso, menos ops.
- **Self-host EN** (RunPod): coste por hora, control, pero requiere disciplina de autoapagado/autoescalado.

