# Estado actual del TFG: realtime-phone-agent

## 1. Resumen ejecutivo

El repositorio implementa un agente telefónico de recepción para Blue Sardine Altea. La arquitectura verificada en código combina FastAPI, FastRTC, LangChain/LangGraph, Groq como LLM, un stack modular de STT/TTS, Superlinked sobre Qdrant para recuperación semántica y Opik para prompts/trazas cuando está configurado.

Estado: Verificado en código y configuración.

La rama `main` contiene la migración a la base de conocimiento hotelera y una arquitectura con rutas separadas para selección de idioma (`/voice`, `/voice-en`, `/voice-es`). La rama `feat/cost-reduction` añade tres commits sobre `main` y parece orientada a una demo más barata y simple: un único pod principal en RunPod CPU, STT en Groq Whisper, TTS en ElevenLabs, Mistral Voxtral como fallback, una única ruta pública de telefonía y scripts de despliegue/validación.

Rama recomendada para demo: `feat/cost-reduction`, siempre que se actualice `.env` con las variables nuevas de `.env.example` y se valide la ingesta explícita de Qdrant.

## 2. Alcance de la revisión

Revisión realizada sobre el repositorio local `lorensation/realtime-phone-agent`, con rama activa `feat/cost-reduction`.

Ramas revisadas:

- `main`: commit `c3b7542`, también `origin/main`.
- `feat/cost-reduction`: commit `f800fa3`, también `origin/feat/cost-reduction`.

Comandos ejecutados:

- `git branch -a`
- `git log --oneline --decorate -n 12 main`
- `git log --oneline --decorate -n 12 feat/cost-reduction`
- `git diff --stat main..feat/cost-reduction`
- `git diff --name-status main..feat/cost-reduction`
- `git ls-tree -r --name-only main`
- `git ls-tree -r --name-only feat/cost-reduction`
- `rg -n "STT_MODEL|TTS_MODEL|Groq|OpenAI|ElevenLabs|Mistral|Twilio|Qdrant|Superlinked|Opik|PROMPTS|KNOWLEDGE_BASE|RunPod|outbound|telephone|WebRTC|FastRTC|InMemorySaver|create_agent|search_hotel" ...`

Limitación MCP: no hay recursos ni templates MCP disponibles para Opik en esta sesión (`list_mcp_resources` y `list_mcp_resource_templates` devolvieron listas vacías). Como alternativa, se consultó Opik mediante el SDK oficial `opik==1.10.51` usando la configuración local del proyecto, sin imprimir claves ni secretos.

Estado Opik remoto: Verificado vía SDK oficial de Opik el 12 de junio de 2026.

## 3. Estado general del repositorio

El proyecto es Python 3.11, empaquetado con `uv`, FastAPI y FastRTC. Las dependencias principales aparecen en `pyproject.toml`: `fastapi[standard]`, `fastrtc`, `groq`, `langchain`, `langchain-groq`, `openai`, `qdrant-client`, `superlinked`, `twilio`, `runpod`, `opik`, `torch` y `transformers`.

Puntos de entrada verificados:

- API principal: `src/realtime_phone_agents/api/main.py`.
- Montaje de voz: `src/realtime_phone_agents/api/routes/voice.py`.
- Agente: `src/realtime_phone_agents/agent/fastrtc_agent.py`.
- Stream FastRTC/Twilio: `src/realtime_phone_agents/agent/stream.py`.
- Ingesta KB: `scripts/ingest_hotel_kb.py`.
- Gradio local: `scripts/run_gradio_application.py`.
- Despliegue RunPod principal: `scripts/runpod/create_call_center_pod.py`.
- Llamada saliente: `scripts/make_outbound_call.py`.

Servicios externos requeridos o soportados:

- Groq para LLM y STT Whisper. Estado: Verificado en código.
- ElevenLabs para TTS principal en `feat/cost-reduction`. Estado: Verificado en código/configuración.
- Mistral Voxtral TTS como fallback. Estado: Verificado en código/configuración.
- Qdrant para persistencia vectorial. Estado: Verificado en código/configuración.
- Superlinked como capa de indexación/consulta. Estado: Verificado en código.
- Twilio para telefonía. Estado: Verificado en código.
- RunPod para despliegue. Estado: Verificado en scripts/documentación.
- Opik para prompts y trazas. Estado: Verificado en código y verificado remotamente vía SDK oficial de Opik; MCP Opik no disponible en esta sesión.

El worktree local tenía `TASK.md` sin seguimiento. No se ha modificado.

## 4. Estado de la rama main

### 4.1 Últimos cambios relevantes

Últimos commits relevantes de `main`:

- `c3b7542`: migración a KB hotelera y arquitectura de prompts gestionados por Opik.
- `9d47e5f`: integración TTS es-ES con ElevenLabs y robustecimiento del agente telefónico.
- `a4f94e3`: mejoras de enrutado de voz y soporte TTS español.
- `1af89d1`: implementación de Faster-Whisper en RunPod y opciones Groq.
- `89811c1`: incorporación de Superlinked y parámetros de búsqueda vectorial.
- `13368cc`: base del agente FastRTC con LangChain, FastAPI, Twilio, STT/TTS, Docker y `uv.lock`.

Estado: Verificado en historial Git.

### 4.2 Estructura actual

`main` contiene:

- `data/blue_sardine_kb/2026-03-24` y `data/blue_sardine_kb/2026-04-11`.
- `src/realtime_phone_agents/agent/` con agente, prompts, retrieval y tools.
- `src/realtime_phone_agents/api/` con rutas `health`, `knowledge`, `superlinked`, `voice`.
- `src/realtime_phone_agents/infrastructure/superlinked/` con schema, query, index y service.
- `src/realtime_phone_agents/stt/` con `moonshine`, `whisper-groq` y `faster-whisper`.
- `src/realtime_phone_agents/tts/` con `kokoro`, `together`, `orpheus-runpod` y ElevenLabs español.
- `scripts/ingest_hotel_kb.py`, `scripts/run_gradio_application.py` y scripts legacy de RunPod para audio.

Estado: Verificado mediante `git ls-tree -r --name-only main`.

### 4.3 Funcionalidades presentes

`main` implementa:

- FastAPI con rutas HTTP de salud, ingesta y búsqueda.
- Agente FastRTC con `ReplyOnPause`.
- LangChain `create_agent` con `ChatGroq`.
- Memoria por hilo con `InMemorySaver`.
- Tool-calling mediante `search_hotel_kb_tool`.
- Prompts remotos desde Opik con fallback local.
- KB hotelera versionada de Blue Sardine.
- Superlinked + Qdrant.
- Telefonía Twilio con selección de idioma por `Gather`.
- Streams separados: `/voice`, `/voice-en`, `/voice-es`.

Estado: Verificado en código.

### 4.4 Riesgos o puntos pendientes

- La demo en `main` usa una arquitectura de teléfono más compleja, con selección de idioma inicial y rutas separadas.
- `.env.example` de `main` conserva defaults primarios `STT_MODEL=faster-whisper` y `TTS_MODEL=orpheus-runpod`, lo que requiere pods de audio o endpoints legacy.
- ElevenLabs aparece como ruta española, pero no como TTS principal general.
- Opik remoto se ha verificado vía SDK oficial, pero no mediante MCP. Las trazas remotas consultadas no se atribuyen de forma concluyente a una rama Git concreta.

Estado: Inferido a partir de código/configuración; Opik remoto verificado vía SDK, MCP No disponible.

## 5. Estado de la rama feat/cost-reduction

### 5.1 Últimos cambios relevantes

Commits propios de `feat/cost-reduction` sobre `main`:

- `e354731`: mejora STT/TTS con Mistral y scripts de despliegue.
- `b338e10`: mejora integración ElevenLabs con soporte multilingüe y configuración por voice ID.
- `f800fa3`: mejora troceado de texto y normalización de identificadores de hotel para búsqueda.

La comparación `main..feat/cost-reduction` muestra `37 files changed, 2128 insertions(+), 1640 deletions(-)`.

Estado: Verificado en Git.

### 5.2 Estructura actual

La rama conserva la estructura principal de `main`, pero añade:

- `src/realtime_phone_agents/agent/stream.py`.
- `src/realtime_phone_agents/tts/mistral/__init__.py`.
- `src/realtime_phone_agents/tts/mistral/model.py`.
- `src/realtime_phone_agents/tts/mistral/options.py`.
- `scripts/make_outbound_call.py`.
- `scripts/runpod/create_call_center_pod.py`.
- `scripts/sync_opik_prompts.py`.
- `scripts/validate_deployment_env.py`.
- `docs/RUNPOD_DEPLOYMENT.md`.
- `tests/test_deployment.py`.

También elimina `docs/NEXT_STEPS.md` y `docs/NEXT_STEPS_v2.md`.

Estado: Verificado mediante `git diff --name-status main..feat/cost-reduction`.

### 5.3 Funcionalidades presentes

Funcionalidades verificadas:

- Ruta pública única `/voice/telephone/incoming`.
- TwiML directo con `<Say>` y `<Connect><Stream>` hacia `/voice/telephone/handler`.
- Eliminación de rutas internas `/voice-en` y `/voice-es` en el montaje principal.
- `STT_MODEL=whisper-groq` y `TTS_MODEL=elevenlabs` como defaults de `.env.example`.
- ElevenLabs multilingüe con `ELEVENLABS__VOICE_ID`, `ELEVENLABS__VOICE_ID_EN` y `ELEVENLABS__VOICE_ID_ES`.
- Mistral Voxtral TTS como fallback seleccionable mediante `TTS_MODEL=mistral-voxtral`.
- Validación explícita de entorno para despliegue.
- Script de creación de pod principal en RunPod.
- Script local para llamada saliente con Twilio.
- Normalización de texto hablado para eliminar markdown antes de TTS.
- Carga de metadata de KB aunque la ingesta vectorial sea explícita.

Estado: Verificado en código.

### 5.4 Cambios orientados a reducción de costes

Cambios visibles orientados a coste:

- Sustitución del stack primario legacy `faster-whisper` + `orpheus-runpod` por `whisper-groq` + `elevenlabs`. Estado: Verificado en `.env.example` y `README.md`.
- Despliegue principal en un único pod CPU de RunPod para la app, en vez de depender de pods GPU separados para STT/TTS. Estado: Verificado en `docs/RUNPOD_DEPLOYMENT.md` y `scripts/runpod/create_call_center_pod.py`.
- Pods legacy de Faster Whisper y Orpheus quedan como fallback. Estado: Verificado en `README.md`, `Makefile` y `docs/GETTINGS_STARTED.md`.
- Twilio pasa a flujo directo con un solo stream público, reduciendo complejidad operativa. Estado: Verificado en `src/realtime_phone_agents/api/routes/voice.py`.
- `KNOWLEDGE_BASE__AUTO_INGEST_DEFAULT_BUNDLE=false` en `.env.example`, orientado a ingesta explícita de producción. Estado: Verificado en configuración.

Impacto económico exacto: No verificado. El repo no incluye mediciones de coste, facturación ni benchmarks económicos.

### 5.5 Riesgos o puntos pendientes

- `.env` local contiene nombres de variables del flujo anterior y no todas las nuevas variables de `feat/cost-reduction` observadas en `.env.example` (`RUNPOD__CALL_CENTER_IMAGE_NAME`, variables Twilio y `ELEVENLABS__VOICE_ID` general, entre otras). Estado: Verificado por nombres de variables, sin inspeccionar valores.
- `config.py` tiene `auto_ingest_default_bundle=True` como default interno, pero `.env.example` recomienda `KNOWLEDGE_BASE__AUTO_INGEST_DEFAULT_BUNDLE=false` para producción. Estado: Verificado; contradicción controlada por `.env`.
- El validador exige `OPENAI__API_KEY`, aunque el uso exacto de OpenAI en el flujo de consulta Superlinked no aparece de forma directa en `service.py` revisado. Estado: Verificado en script; uso operacional Inferido/Pendiente de confirmar.
- Opik remoto no fue accesible desde MCP, pero sí mediante SDK oficial. Estado: MCP No disponible; prompts/trazas remotas verificadas vía SDK.
- No se ejecutó una llamada real ni una sesión WebRTC real durante esta revisión. Estado: No verificado.

## 6. Comparativa entre main y feat/cost-reduction

### 6.1 Diferencias funcionales

- `main`: flujo telefónico con selección inicial de idioma usando Twilio `Gather`, luego conexión a `/voice-en` o `/voice-es`. Estado: Verificado en código.
- `feat/cost-reduction`: flujo telefónico directo con una sola ruta pública `/voice/telephone/incoming` y un único stream `/voice/telephone/handler`. Estado: Verificado en código.
- `feat/cost-reduction`: añade llamada saliente mediante `scripts/make_outbound_call.py`. Estado: Verificado en código.
- `feat/cost-reduction`: añade validación de entorno de despliegue. Estado: Verificado en código.

### 6.2 Diferencias técnicas

- `main` usa directamente `fastrtc.Stream` en `FastRTCAgent`.
- `feat/cost-reduction` introduce `VoiceAgentStream` en `src/realtime_phone_agents/agent/stream.py`, encapsulando lógica de URL pública/TwiML.
- `feat/cost-reduction` refresca prompts para nuevas llamadas según `PROMPTS__REFRESH_INTERVAL_SECONDS` con default 300 segundos.
- `feat/cost-reduction` normaliza texto antes de TTS para evitar markdown y caracteres raros en audio.
- `feat/cost-reduction` añade normalización de identificadores de hotel/secciones en `KnowledgeSearchService`.

Estado: Verificado en código.

### 6.3 Diferencias de configuración

- `main`: `.env.example` usa `STT_MODEL=faster-whisper` y `TTS_MODEL=orpheus-runpod`.
- `feat/cost-reduction`: `.env.example` usa `STT_MODEL=whisper-groq` y `TTS_MODEL=elevenlabs`.
- `feat/cost-reduction` añade `SERVER__PUBLIC_BASE_URL`, `RUNPOD__CALL_CENTER_IMAGE_NAME`, `RUNPOD__CALL_CENTER_INSTANCE_ID`, volumen del pod principal, Twilio outbound y Mistral.
- `feat/cost-reduction` cambia `GROQ__STT_MODEL` de `whisper-large-v3` a `whisper-large-v3-turbo`.
- `feat/cost-reduction` recomienda `KNOWLEDGE_BASE__AUTO_INGEST_DEFAULT_BUNDLE=false`.

Estado: Verificado en configuración.

### 6.4 Diferencias en providers

- LLM: ambas ramas usan `ChatGroq` con `settings.groq.model`. Estado: Verificado en código.
- STT principal:
  - `main`: `faster-whisper` por default de `.env.example`.
  - `feat/cost-reduction`: `whisper-groq` por default de `.env.example`.
- TTS principal:
  - `main`: `orpheus-runpod` por default, con ElevenLabs español en ruta de idioma.
  - `feat/cost-reduction`: `elevenlabs` por default, con Mistral Voxtral, Together, Kokoro y Orpheus como opciones/fallbacks.

Estado: Verificado en código/configuración.

### 6.5 Diferencias en RAG/Superlinked

Ambas ramas comparten la base de arquitectura RAG:

- KB versionada en `data/blue_sardine_kb/2026-04-11`.
- Normalización a `KnowledgeEntry`.
- Schema Superlinked con espacios de texto (`title`, `body`) y espacios numéricos (`area_sqm`, `base_price_eur`).
- Qdrant como vector DB cuando está disponible.
- Fallback a `InMemoryExecutor`.

Diferencias de `feat/cost-reduction`:

- Normaliza `hotel_id` y `section` para evitar fallos por near-match.
- Puede cargar solo metadata del bundle si el índice ya fue ingerido en Qdrant.
- Ajusta `context_builder.py` para más alias de sección y tipos documentales.

Estado: Verificado en código.

### 6.6 Diferencias en despliegue

- `main`: mantiene scripts legacy de RunPod para Faster Whisper y Orpheus.
- `feat/cost-reduction`: añade pod principal CPU para la app, build/push de imagen en `Makefile`, validación de entorno, documentación `docs/RUNPOD_DEPLOYMENT.md` y llamada saliente local.
- `feat/cost-reduction`: `Dockerfile` instala `libgl1` además de `ffmpeg`.
- `feat/cost-reduction`: `docker-compose.yml` cambia el healthcheck de `curl` a Python `urllib`, compatible con la imagen slim si `curl` no está instalado.

Estado: Verificado en diff y archivos.

### 6.7 Rama recomendada para demo

Recomendación: `feat/cost-reduction`.

Motivos:

- Tiene defaults de audio más adecuados para demo con menos infraestructura propia: `whisper-groq` + `elevenlabs`.
- Reduce el flujo Twilio a una ruta pública directa.
- Incluye scripts de validación, despliegue y llamada saliente.
- Documenta una topología primaria de RunPod CPU + Qdrant externo + Twilio.
- Añade tests para validación de despliegue, healthcheck y ruta Twilio directa.

Condición: antes de la demo hay que alinear `.env` con `.env.example` de la rama, validar `make validate-deploy-env`, ingerir KB y probar una llamada real.

## 7. Arquitectura actual del agente

### 7.1 Flujo general

Flujo verificado:

1. FastAPI arranca en `src/realtime_phone_agents/api/main.py`.
2. `lifespan` configura Opik si hay `OPIK__API_KEY`.
3. Se inicializa `KnowledgeSearchService`.
4. `mount_voice_stream(app)` crea un `FastRTCAgent`.
5. FastRTC monta `/voice`.
6. Twilio llama a `/voice/telephone/incoming`.
7. La app devuelve TwiML que conecta audio a `/voice/telephone/handler`.
8. `ReplyOnPause` entrega chunks de audio al agente.
9. STT transcribe.
10. Se construye contexto de retrieval.
11. LangChain ejecuta `ChatGroq` con tool `search_hotel_kb_tool` si necesita datos.
12. Superlinked/Qdrant recupera conocimiento.
13. El texto final se normaliza.
14. TTS sintetiza audio y FastRTC lo devuelve al canal.

Estado: Verificado en código.

### 7.2 Canal de entrada

Canales:

- WebRTC/FastRTC bajo `/voice`. Estado: Verificado en código.
- Twilio Media Streams mediante `/voice/telephone/incoming` y `/voice/telephone/handler`. Estado: Verificado en código.
- Gradio local mediante `scripts/run_gradio_application.py`. Estado: Verificado en código.

### 7.3 STT

Factory: `src/realtime_phone_agents/stt/utils.py`.

Providers soportados:

- `whisper-groq`: `src/realtime_phone_agents/stt/groq/whisper.py`.
- `faster-whisper`: `src/realtime_phone_agents/stt/runpod/faster_whisper/model.py`.
- `moonshine`: `src/realtime_phone_agents/stt/local/moonshine.py`.

Default en `feat/cost-reduction`: `STT_MODEL=whisper-groq`.

Estado: Verificado en código/configuración.

### 7.4 LLM/provider

El agente usa:

- `langchain_groq.ChatGroq`.
- Modelo desde `GROQ__MODEL`, default `openai/gpt-oss-20b`.
- `create_agent` de LangChain con `InMemorySaver`.

No se ha encontrado uso directo de OpenAI como LLM conversacional en el agente. `OPENAI__API_KEY` aparece en configuración y validación de despliegue.

Estado: Verificado en código; uso exacto de OpenAI Pendiente de confirmar.

### 7.5 TTS

Factory: `src/realtime_phone_agents/tts/utils.py`.

Providers soportados en `feat/cost-reduction`:

- `elevenlabs`, `elevenlabs-multilingual`, `elevenlabs-es`, `elevenlabs-flash`, `elevenlabs-flash-es`.
- `mistral-voxtral`, `mistral`, `voxtral`.
- `kokoro`.
- `together`.
- `orpheus-runpod`.

Default en `feat/cost-reduction`: `TTS_MODEL=elevenlabs`.

Estado: Verificado en código/configuración.

### 7.6 Memoria y sesiones

Memoria:

- LangGraph `InMemorySaver` en `create_agent`.
- `CallSessionState` por `call_id`.
- `thread_id` por sesión para memoria y trazabilidad.

No se ha encontrado persistencia de memoria a base de datos.

Estado: Verificado en código.

### 7.7 Tool-calling

Tool principal:

- `search_hotel_kb_tool` en `src/realtime_phone_agents/agent/tools/property_search.py`.

Alias legacy:

- `search_property_tool`.
- `search_property_mock_tool` como placeholder.

La tool llama a `KnowledgeSearchService.search_knowledge`. En caso de fallo devuelve un payload JSON con `knowledge_search_failed`, filtros usados y contacto fallback si el bundle está cargado.

Estado: Verificado en código.

### 7.8 Observabilidad

Opik:

- `configure()` en `src/realtime_phone_agents/observability/opik_utils.py`.
- Decoradores `track` en arranque/parada.
- `OpikTracer` para LangChain si está configurado.
- Metadata incluye `call_id`, `thread_id`, idioma, intent, filtros de retrieval y telemetry de prompt.

Se verificó remotamente el proyecto Opik `blue-sardine-hotel` mediante SDK oficial. El proyecto contiene trazas `LangGraph` etiquetadas como `voice-agent`, con metadata de prompts, retrieval, providers, `call_id` y `thread_id`. Las trazas más recientes consultadas datan del 25 de abril de 2026.

No se pudo acceder vía MCP porque no hay servidor/recurso MCP Opik registrado en esta sesión.

Estado: Verificado en código y verificado remotamente vía SDK Opik; MCP Opik No disponible.

## 8. Base de conocimiento

### 8.1 Ubicación

Ubicación principal:

- `data/blue_sardine_kb/2026-04-11`.

Versiones disponibles:

- `data/blue_sardine_kb/2026-03-24`.
- `data/blue_sardine_kb/2026-04-11`.

La versión default configurada es `data/blue_sardine_kb/2026-04-11`.

Estado: Verificado en repo/configuración.

### 8.2 Formato

La versión `2026-04-11` contiene:

- `manifest.json`
- `hotel.json`
- `room_types.json`
- `pricing_inventory_internal.json`
- `faq.json`
- `documents.json`
- `dialogues.json`
- `operational_notes.json`

Conteos verificados:

- `documents`: 6.
- `faq`: 8.
- `room_types`: 6.
- `room_type_extensions`: 1.
- `dialogues`: 8.
- `operational_notes`: 6.

El manifest indica `kb_version=2026-04-11`, `property_name=Blue Sardine Altea` y `confidence=official_plus_internal_unvalidated_pricing`.

Estado: Verificado en datos.

### 8.3 Proceso de ingesta

Proceso:

1. `scripts/ingest_hotel_kb.py` parsea `--bundle-path`.
2. `load_knowledge_bundle` valida existencia, manifest, modelos Pydantic y checksums.
3. `normalize_knowledge_bundle` genera `KnowledgeEntry`.
4. `KnowledgeSearchService.ingest_knowledge_bundle` convierte a DataFrame.
5. `self.source.put([dataframe])` envía datos a Superlinked.
6. Superlinked escribe en Qdrant si está configurado; si falla, usa memoria.

Comando:

```bash
uv run python scripts/ingest_hotel_kb.py
```

Alternativa in-memory:

```bash
uv run python scripts/ingest_hotel_kb.py --in-memory
```

Estado: Verificado en código.

### 8.4 Estado actual

La KB actual está preparada para hotel Blue Sardine Altea, con datos oficiales, pricing interno orientativo, notas operativas, FAQ y diálogos de estilo. Hay guardrails para pricing sin fechas, datos third-party, datos internos no validados y handoff humano.

Estado: Verificado en código/datos.

### 8.5 Pendientes

- Confirmar con datos reales del hotel los elementos marcados como internos no validados.
- Ejecutar ingesta contra el Qdrant que se usará en demo.
- Verificar que la colección `hotel-knowledge` contiene los vectores esperados antes de llamar.
- Decidir si la demo usará autoingesta local o ingesta explícita de producción.

Estado: Pendiente de confirmar.

## 9. Capa RAG + Qdrant + Superlinked

### 9.1 Componentes principales

Componentes:

- Schema/index: `src/realtime_phone_agents/infrastructure/superlinked/index.py`.
- Query: `src/realtime_phone_agents/infrastructure/superlinked/query.py`.
- Servicio: `src/realtime_phone_agents/infrastructure/superlinked/service.py`.
- Contexto de retrieval: `src/realtime_phone_agents/agent/retrieval/context_builder.py`.
- Tool: `src/realtime_phone_agents/agent/tools/property_search.py`.

Estado: Verificado en código.

### 9.2 Flujo de indexación

Superlinked indexa:

- `title_space`: similitud textual sobre título.
- `body_space`: similitud textual sobre cuerpo.
- `area_space`: espacio numérico para área, modo máximo.
- `price_space`: espacio numérico para precio base, modo mínimo.

Modelo de embeddings default:

- `sentence-transformers/all-MiniLM-L6-v2`.

Qdrant:

- Host default: `qdrant`.
- Puerto default: `6333`.
- Colección/app id: `hotel-knowledge`.

Estado: Verificado en código/configuración.

### 9.3 Flujo de recuperación

La consulta Superlinked filtra por:

- `hotel_id`
- `entity_type`
- `section`
- `doc_type`
- `policy_type`
- `amenity_type`
- `room_type_id`
- `language`
- `verification_state`
- `source_priority`
- `area_min`
- `price_max`

El servicio prueba búsquedas por tipos documentales y aplica fallback sin `room_type_id`, sin `section` y sin `entity_type` si no hay resultados.

Estado: Verificado en código.

### 9.4 Integración con el agente

El agente crea un `RetrievalContext` antes de invocar el modelo y lo usa en metadata y políticas de pausas. Cuando el LLM decide usar herramienta, llama a `search_hotel_kb_tool`, que devuelve JSON con resultados, filtros, guardrails y contacto fallback.

Estado: Verificado en código.

### 9.5 Riesgos técnicos

- Si `KNOWLEDGE_BASE__AUTO_INGEST_DEFAULT_BUNDLE=false`, hay que ejecutar ingesta explícita antes de la demo.
- Si Qdrant falla, el código cae a memoria, lo que puede ocultar problemas de infraestructura si no se revisan logs.
- `OPENAI__API_KEY` se valida como obligatorio para despliegue, pero su uso exacto no quedó verificado en el código RAG revisado.
- No se validó con una consulta real contra Qdrant externo.

Estado: Inferido/Pendiente de confirmar.

## 10. Prompts y Opik

### 10.1 Prompts locales

Prompts locales en:

- `src/realtime_phone_agents/agent/prompts/defaults.py`.

Componentes:

- `core`: rol y comportamiento de recepcionista telefónico.
- `retrieval`: reglas de grounding y respuestas factualizadas.
- `escalation`: gestión de incertidumbre y handoff.
- `style`: estilo oral, breve, sin markdown.

Políticas de idioma:

- Default: español por defecto, inglés si el llamante habla o pide inglés.
- Locked: español o inglés durante toda la llamada.

Estado: Verificado en código.

### 10.2 Prompts en Opik

El código carga prompts de Opik por nombre si:

- `PROMPTS__REMOTE_ENABLED=true`.
- `OPIK__API_KEY` está configurado.
- El SDK de Opik está instalado.

Nombres configurados:

- `blue_sardine.receptionist.core`
- `blue_sardine.receptionist.retrieval`
- `blue_sardine.receptionist.escalation`
- `blue_sardine.receptionist.style`

Estado remoto verificado vía SDK Opik:

- Proyecto: `blue-sardine-hotel`.
- URL de proyecto devuelta por SDK: `https://www.comet.com/opik/lorensation/redirect/projects?name=blue-sardine-hotel`.
- Los 4 prompts configurados existen en la librería remota de Opik.
- Cada prompt tiene 6 versiones remotas.
- Ningún componente tiene commit fijado en `.env`/configuración local; el código selecciona la versión más reciente por `created_at` e `id`.
- Las versiones más recientes no tienen variables Mustache detectadas (`{{variable}}`), por lo que los prompts remotos actuales son texto plano.
- Las versiones más recientes de los 4 componentes coinciden exactamente con los fallbacks locales actuales según comparación de contenido (`matches_local_fallback=true`).

Últimas versiones remotas verificadas:

| Componente | Prompt Opik | Commit latest | Creado en UTC | Longitud | Hash SHA-256 corto | Coincide con fallback local |
| --- | --- | --- | --- | ---: | --- | --- |
| `core` | `blue_sardine.receptionist.core` | `f5c47c6f` | `2026-06-12 12:19:49.728711+00:00` | 1247 | `72d218435c60` | Sí |
| `retrieval` | `blue_sardine.receptionist.retrieval` | `162d2755` | `2026-06-12 12:19:50.279422+00:00` | 953 | `6b46100e9914` | Sí |
| `escalation` | `blue_sardine.receptionist.escalation` | `f23923a5` | `2026-06-12 12:19:50.818822+00:00` | 734 | `2f4a2ee08b1b` | Sí |
| `style` | `blue_sardine.receptionist.style` | `887e569f` | `2026-06-12 12:19:51.388952+00:00` | 1010 | `34aab3847889` | Sí |

Metadata de las versiones latest:

- `hotel=blue-sardine`
- `channel=voice`
- `component=core|retrieval|escalation|style`

Trazas remotas verificadas en el proyecto `blue-sardine-hotel`:

- La consulta `search_traces(max_results=10)` devolvió 10 trazas.
- La traza más reciente de la muestra es `app.shutdown_services`, iniciada el `2026-04-25 11:37:23.817844+00:00`.
- Las trazas conversacionales recientes aparecen como `LangGraph`.
- Tags observados: `voice-agent`, `language:auto`, `intent:location_and_parking`, `intent:room_selection`.
- Metadata observada en trazas `LangGraph`: `call_id`, `thread_id`, `language`, `providers`, `retrieval.intent`, `retrieval.search_mode`, filtros de retrieval y campos `prompt.*` con nombre, source, commit y version_id.
- Threads remotos: `search_threads(max_results=10)` devolvió 10 threads.
- Thread más reciente: `7ed46b88-79fd-4899-bef4-2a42171e3977`, del `2026-04-25 11:14:24.762927+00:00` al `2026-04-25 11:16:06.954367+00:00`, con 16 mensajes.

No se han volcado inputs/outputs de conversaciones en este documento; solo metadatos operativos.

Estado: Verificado en código/configuración y verificado remotamente vía SDK Opik. MCP Opik No disponible.

### 10.3 Versionado

Cada componente acepta `commit` opcional:

- `PROMPTS__CORE__COMMIT`
- `PROMPTS__RETRIEVAL__COMMIT`
- `PROMPTS__ESCALATION__COMMIT`
- `PROMPTS__STYLE__COMMIT`

Si el commit está vacío, el provider selecciona la versión más reciente según `created_at` e `id`.

`scripts/sync_opik_prompts.py` publica prompts locales a Opik y muestra el commit creado.

Versionado remoto observado:

- `core`: 6 versiones. Latest `f5c47c6f`. Versiones anteriores relevantes: `a5452a29`, `b025d693`, `9cdd8fcf`, `3c58e813`, `33a22442`.
- `retrieval`: 6 versiones. Latest `162d2755`. Versiones anteriores relevantes: `c44b6075`, `ae7759b3`, `366950c3`, `98bfe437`, `0cadbc28`.
- `escalation`: 6 versiones. Latest `f23923a5`. Versiones anteriores relevantes: `7dbd59e8`, `5fe2cf57`, `77006d97`, `2b504ca6`, `ca4bbcec`.
- `style`: 6 versiones. Latest `887e569f`. Versiones anteriores relevantes: `3e85c5b3`, `206a5a77`, `69d82c48`, `c9fde13c`, `e513f007`.

Implicación: con commits vacíos en configuración, una nueva llamada debería usar las versiones latest anteriores, salvo que falle Opik y se active fallback local. Dado que los latest coinciden con los fallbacks locales, el riesgo de divergencia actual entre remoto y local es bajo.

Estado: Verificado en código y verificado remotamente vía SDK Opik.

### 10.4 Variables usadas

Variables principales:

- `OPIK__API_KEY`
- `OPIK__PROJECT_NAME`
- `PROMPTS__REMOTE_ENABLED`
- `PROMPTS__REFRESH_INTERVAL_SECONDS`
- `PROMPTS__CORE__NAME`
- `PROMPTS__CORE__COMMIT`
- `PROMPTS__RETRIEVAL__NAME`
- `PROMPTS__RETRIEVAL__COMMIT`
- `PROMPTS__ESCALATION__NAME`
- `PROMPTS__ESCALATION__COMMIT`
- `PROMPTS__STYLE__NAME`
- `PROMPTS__STYLE__COMMIT`

Estado: Verificado en código/configuración.

### 10.5 Pendientes de validación

Ya verificado:

- Los prompts remotos existen en Opik.
- Hay 6 versiones por componente.
- Los commits latest activos por selección automática están identificados.
- Existen trazas reales en el proyecto `blue-sardine-hotel`.
- `scripts/sync_opik_prompts.py` parece haber sido ejecutado al menos el 12 de junio de 2026, porque los latest remotos tienen metadata `hotel=blue-sardine`, `channel=voice` y coinciden con los fallbacks locales publicados por ese script.

Pendiente:

- Decidir si la demo debe fijar commits concretos o usar latest.
- Confirmar si los commits latest del 12 de junio de 2026 son los aprobados formalmente para demo.
- Revisar contenido completo de trazas si se necesita auditoría conversacional; en este informe solo se documentan metadatos para no volcar conversaciones.
- Verificar experimentos/evaluaciones Opik: no se encontró una API directa de listado general de experimentos en el cliente usado; solo se inspeccionaron prompts, trazas y threads.

Estado: Parcialmente verificado vía SDK Opik; pendientes explícitos arriba.

## 11. Guía de despliegue para la demo

### 11.1 Requisitos previos

Requisitos:

- Python 3.11.
- `uv`.
- Docker y Docker Compose si se ejecuta localmente con contenedores.
- Cuenta/API key de Groq.
- Cuenta/API key de ElevenLabs.
- Qdrant local o externo.
- Cuenta/API key de RunPod si se despliega en RunPod.
- Cuenta Twilio y número de teléfono si se prueba telefonía real.
- Opik opcional para prompts remotos/trazas.

Estado: Verificado en documentación/configuración.

### 11.2 Variables de entorno

Crear `.env` desde ejemplo:

```bash
cp .env.example .env
```

Variables críticas para la ruta recomendada:

```env
STT_MODEL=whisper-groq
TTS_MODEL=elevenlabs
GROQ__API_KEY=...
GROQ__MODEL=openai/gpt-oss-20b
GROQ__STT_MODEL=whisper-large-v3-turbo
ELEVENLABS__API_KEY=...
ELEVENLABS__VOICE_ID=...
QDRANT__HOST=...
QDRANT__PORT=6333
QDRANT__USE_HTTPS=true|false
KNOWLEDGE_BASE__DEFAULT_BUNDLE_PATH=data/blue_sardine_kb/2026-04-11
KNOWLEDGE_BASE__AUTO_INGEST_DEFAULT_BUNDLE=false
KNOWLEDGE_BASE__COLLECTION_NAME=hotel-knowledge
KNOWLEDGE_BASE__DEFAULT_HOTEL_ID=blue_sardine_altea
CALL_FLOW__LANGUAGE_SELECTION_ENABLED=false
```

Para despliegue RunPod:

```env
RUNPOD__API_KEY=...
RUNPOD__CALL_CENTER_IMAGE_NAME=...
RUNPOD__CALL_CENTER_INSTANCE_ID=cpu5c-2-4
```

Para llamada saliente:

```env
TWILIO__ACCOUNT_SID=...
TWILIO__AUTH_TOKEN=...
TWILIO__FROM_NUMBER=...
```

No incluir secretos en documentación ni commits.

### 11.3 Servicios externos necesarios

Ruta principal recomendada:

- Groq: LLM y STT.
- ElevenLabs: TTS.
- Qdrant: vector database.
- Twilio: telefonía.
- RunPod: hosting app si no se ejecuta local/ngrok.
- Opik: prompts/trazas si se activa.

Estado: Verificado en código/configuración.

### 11.4 Instalación

Instalar dependencias:

```bash
uv venv .venv
uv pip install -e .
```

Validar Python:

```bash
uv run python --version
```

Validar entorno de demo:

```bash
make validate-deploy-env
```

Si se va a usar llamada saliente:

```bash
uv run python scripts/validate_deployment_env.py --include-outbound
```

Estado: Comandos basados en archivos verificados.

### 11.5 Preparación de la base de conocimiento

Con Qdrant levantado/configurado:

```bash
uv run python scripts/ingest_hotel_kb.py
```

Con Makefile:

```bash
make ingest-hotel-kb
```

Prueba de búsqueda:

```bash
curl -X POST http://localhost:8000/knowledge/search ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"Hay parking cerca?\",\"limit\":3}"
```

En PowerShell también puede usarse:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/knowledge/search -ContentType "application/json" -Body '{"query":"Hay parking cerca?","limit":3}'
```

Estado: Comandos basados en endpoints verificados.

### 11.6 Ejecución local

Arrancar API sin Docker:

```bash
uv run python -m realtime_phone_agents.api.main
```

Healthcheck:

```bash
curl http://localhost:8000/health
```

Exponer para Twilio con ngrok:

```bash
make start-ngrok-tunnel
```

Configurar Twilio con:

```text
https://<ngrok-url>/voice/telephone/incoming
```

Estado: Verificado en documentación/código.

### 11.7 Ejecución con Docker

Arrancar app + Qdrant:

```bash
docker compose up --build -d
```

O mediante Make:

```bash
make start-call-center
```

Parar:

```bash
make stop-call-center
```

Borrar volúmenes:

```bash
make delete-call-center
```

Estado: Verificado en `docker-compose.yml` y `Makefile`.

### 11.8 Configuración de llamada/WebRTC/Twilio

Entrada Twilio inbound:

```text
/voice/telephone/incoming
```

La app genera un WebSocket hacia:

```text
/voice/telephone/handler
```

Para llamada saliente desde máquina local:

```bash
make outbound-call
```

O explícito:

```bash
uv run python scripts/make_outbound_call.py --to-number +34XXXXXXXXX --public-base-url https://<public-url>
```

Estado: Verificado en código.

### 11.9 Prueba de funcionamiento

Checklist mínimo:

1. `make validate-deploy-env` sin errores.
2. API responde `/health` con `status=healthy`.
3. KB ingerida en Qdrant.
4. `/knowledge/search` devuelve resultados para consultas de parking, habitaciones o políticas.
5. Twilio webhook apunta a `/voice/telephone/incoming`.
6. La llamada reproduce "Connecting you to the hotel assistant.".
7. El agente transcribe, consulta KB si hace falta y responde por voz.
8. Si Opik está activo, aparecen trazas con tags `voice-agent`.

Estado: Pasos basados en código; llamada real No verificada en esta revisión.

### 11.10 Logs y trazas

Revisar:

- Logs de FastAPI/uvicorn.
- Logs de `KnowledgeSearchService` para conexión Qdrant e ingesta.
- Logs de `Voice stream was not mounted` si falla audio provider.
- `/health` para `voice_stream_error`.
- Opik project `blue-sardine-hotel` si está configurado.
- Twilio debugger/call logs.

Estado: Verificado en código/documentación.

### 11.11 Problemas comunes

- `voice_stream_available=false`: revisar `GROQ__API_KEY`, `ELEVENLABS__API_KEY`, voice ID y providers.
- Healthcheck 503: voz o servicio de conocimiento no inicializados.
- Sin resultados RAG: ejecutar `scripts/ingest_hotel_kb.py` y revisar Qdrant.
- URL WebSocket incorrecta en RunPod/ngrok: dejar `SERVER__PUBLIC_BASE_URL` vacío en RunPod proxy o usar un valor HTTPS real.
- `SERVER__PUBLIC_BASE_URL` placeholder: el validador lo rechaza.
- `KNOWLEDGE_BASE__AUTO_INGEST_DEFAULT_BUNDLE=true` en producción: el validador lo rechaza para flujo explícito.
- `.env` local desalineado con `.env.example`: actualizar variables antes de demo.

Estado: Verificado/Inferido desde scripts y tests.

## 12. Checklist final antes de la demo

- Cambiar a rama `feat/cost-reduction`.
- Actualizar `.env` desde `.env.example` de la rama actual.
- Confirmar `STT_MODEL=whisper-groq`.
- Confirmar `TTS_MODEL=elevenlabs`.
- Confirmar `ELEVENLABS__VOICE_ID` o overrides por idioma.
- Confirmar `GROQ__API_KEY`.
- Confirmar `QDRANT__HOST`, `QDRANT__PORT`, `QDRANT__USE_HTTPS` y `QDRANT__API_KEY` si aplica.
- Ejecutar `make validate-deploy-env`.
- Levantar API local o desplegar pod RunPod.
- Ejecutar `make ingest-hotel-kb`.
- Probar `/health`.
- Probar `/knowledge/search`.
- Configurar Twilio inbound hacia `/voice/telephone/incoming`.
- Hacer una llamada de prueba.
- Revisar logs y Opik si está activo.
- Preparar fallback: demo local por Gradio o WebRTC si Twilio falla.

## 13. Conclusiones

El proyecto tiene una arquitectura suficientemente completa para una demo de agente telefónico hotelero: voz en tiempo real, tool-calling, RAG sobre KB versionada, Qdrant/Superlinked, prompts locales/remotos y trazabilidad con Opik.

La rama `feat/cost-reduction` es la mejor candidata para demo porque reduce infraestructura, formaliza despliegue y simplifica telefonía. El mayor riesgo no está en el código revisado sino en la configuración operacional: `.env`, claves externas, ingesta Qdrant, Twilio y validación de prompts remotos.

## 14. Anexos

### 14.1 Comandos Git utilizados

```bash
git status --short
git branch --show-current
git branch -a
git log --oneline --decorate -n 12 main
git log --oneline --decorate -n 12 feat/cost-reduction
git log --left-right --cherry-pick --oneline main...feat/cost-reduction
git diff --stat main..feat/cost-reduction
git diff --shortstat main..feat/cost-reduction
git diff --name-status main..feat/cost-reduction
git diff --name-only main..feat/cost-reduction -- docs scripts src tests .env.example README.md Makefile Dockerfile docker-compose.yml
git ls-tree -r --name-only main
git ls-tree -r --name-only feat/cost-reduction
git show main:.env.example
git show main:src/realtime_phone_agents/config.py
git show main:src/realtime_phone_agents/api/routes/voice.py
git show main:src/realtime_phone_agents/tts/utils.py
git show main:README.md
git show main:docker-compose.yml
git show main:Makefile
```

Comprobaciones Opik realizadas:

```bash
uv run python - <<'PY'
from realtime_phone_agents.config import settings
print(bool(settings.opik.api_key))
print(settings.opik.project_name)
PY
```

```bash
uv run python - <<'PY'
from opik.api_objects import opik_client
client = opik_client.get_client_cached()
print(client.get_project_url("blue-sardine-hotel"))
print(client.search_traces(project_name="blue-sardine-hotel", max_results=10))
print(client.search_threads(project_name="blue-sardine-hotel", max_results=10))
PY
```

```bash
uv run python - <<'PY'
from opik.api_objects import opik_client
from opik.api_objects.prompt.client import PromptClient
client = opik_client.get_client_cached()
prompt_client = PromptClient(client.rest_client)
for name in [
    "blue_sardine.receptionist.core",
    "blue_sardine.receptionist.retrieval",
    "blue_sardine.receptionist.escalation",
    "blue_sardine.receptionist.style",
]:
    print(name, prompt_client.get_all_prompt_versions(name=name, project_name=None))
PY
```

### 14.2 Archivos revisados

Archivos principales:

- `README.md`
- `.env.example`
- `.env` solo nombres de variables, sin valores.
- `pyproject.toml`
- `Dockerfile`
- `docker-compose.yml`
- `Makefile`
- `docs/GETTINGS_STARTED.md`
- `docs/RUNPOD_DEPLOYMENT.md`
- `scripts/ingest_hotel_kb.py`
- `scripts/make_outbound_call.py`
- `scripts/runpod/create_call_center_pod.py`
- `scripts/sync_opik_prompts.py`
- `scripts/validate_deployment_env.py`
- `src/realtime_phone_agents/config.py`
- `src/realtime_phone_agents/api/main.py`
- `src/realtime_phone_agents/api/models.py`
- `src/realtime_phone_agents/api/routes/health.py`
- `src/realtime_phone_agents/api/routes/knowledge.py`
- `src/realtime_phone_agents/api/routes/voice.py`
- `src/realtime_phone_agents/agent/fastrtc_agent.py`
- `src/realtime_phone_agents/agent/stream.py`
- `src/realtime_phone_agents/agent/prompts/builder.py`
- `src/realtime_phone_agents/agent/prompts/defaults.py`
- `src/realtime_phone_agents/agent/prompts/provider.py`
- `src/realtime_phone_agents/agent/retrieval/context_builder.py`
- `src/realtime_phone_agents/agent/tools/property_search.py`
- `src/realtime_phone_agents/infrastructure/superlinked/index.py`
- `src/realtime_phone_agents/infrastructure/superlinked/query.py`
- `src/realtime_phone_agents/infrastructure/superlinked/service.py`
- `src/realtime_phone_agents/knowledge/loader.py`
- `src/realtime_phone_agents/knowledge/normalization.py`
- `src/realtime_phone_agents/observability/opik_utils.py`
- `src/realtime_phone_agents/observability/prompt_versioning.py`
- `src/realtime_phone_agents/stt/utils.py`
- `src/realtime_phone_agents/tts/utils.py`
- `tests/test_audio_stack.py`
- `tests/test_deployment.py`
- `data/blue_sardine_kb/2026-04-11/manifest.json`

### 14.3 Información no verificada

- Acceso a Opik mediante MCP: no hay servidor/recurso MCP Opik disponible en esta sesión.
- Experimentos/evaluaciones Opik: no se verificó un listado general de experimentos porque el cliente SDK disponible no expuso una llamada directa equivalente durante la revisión.
- Coste real comparado entre providers.
- Funcionamiento de llamada real Twilio en esta máquina.
- Estado real de Qdrant externo usado para la demo.
- Que las claves de `.env` local sean válidas.
- Uso operacional exacto de `OPENAI__API_KEY` en el flujo actual de Superlinked.
- Calidad final de audio de ElevenLabs/Mistral en llamada telefónica real.
