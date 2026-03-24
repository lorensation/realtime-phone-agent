# Base de conocimiento para Hotel Blue Sardine Altea

## Contexto y objetivos de migración

El objetivo es convertir el contenido público del sitio oficial del alojamiento en una base de conocimiento útil para un agente conversacional (RAG/LLM), de forma que el POC actual (orientado a “real estate agent”) pueda responder con precisión a preguntas típicas de huéspedes: tipos de habitaciones, equipamiento, políticas, ubicación, parking, check-in, cancelaciones y servicios.

En la web oficial se describe el alojamiento como “alojamiento boutique” en un antiguo barrio de pescadores, a pocos metros del mar y al inicio del casco histórico de Altea.

## Evidencia extraída del sitio oficial

El sitio oficial presenta una taxonomía clara de productos de alojamiento: habitaciones (estándar, superior, con terraza/premium, estudio con terraza) y apartamentos (Blue y Sardine).

En el propio “home” también se publican servicios y facilities en categorías (experiencias, limpieza, equipamiento y parking), con elementos operativos relevantes para un agente: atención personalizada, tecnología para aperturas y registros, servicio de limpieza, amenities, toallas, wifi gratuito, climatización frío/calor, caja fuerte, nevera, Smart TV, taquillas/almacenamiento de equipaje y parking público gratuito a 200 metros.

El sitio ofrece datos de contacto (teléfono y email) y una dirección asociada al alojamiento (“Calle Pescadores 1, 03590, Altea, Alicante”). 

## Inventario de alojamiento y mapeo con tus categorías

### Tipos canónicos de la web (recomendación “source of truth”)

A nivel de “producto” (lo que un huésped puede reservar y entender), la web describe estas unidades, todas para 2 adultos y cama doble (según páginas de cada tipo): 

**Habitación Standard (Habitación Doble Estándar)**: 15 m²; incluye A/C frío-calor, TV, minibar, taquilla/locker, zona de estar; baño con ducha, amenities/toiletries, secador y WiFi. 

**Habitación Superior (Habitación Doble Superior)**: 18 m²; amenities muy similares a Standard (A/C, TV, minibar, locker, zona de estar; ducha, toiletries, secador, WiFi). 

**Habitación Premium (Habitación Doble con terraza)**: se presenta como habitación con terraza independiente y vistas al mar y al casco antiguo; incluye A/C, TV, minibar, locker, zona de estar, WiFi; baño con ducha, toiletries, secador; además kettle y cafetera. 

**Studio Room with terrace (Estudio con terraza)**: 30 m²; se describe como una opción para estancias largas, con sala de estar, habitación y baño en suite; menciona balcón y terraza principal. Incluye A/C, TV, minibar, locker, escritorio, zona de estar, ducha, toiletries, secador, kettle, microondas, plancha y WiFi. 

**Apartamento Blue (Apartamento Blue)**: se presenta como el “Blue 04”, un apartamento de 50 m² con dormitorio, cocina, salón-comedor y baño; lista equipamiento tipo apartamento (kitchenette, menaje, microondas, lavadora, plancha), además de A/C, TV, minibar, locker, escritorio, zona de estar, ducha, toiletries, secador, kettle y WiFi. 

**Apartamento Sardine (Apartamento Sardine)**: se presenta como el “Sardine 05”, apartamento de 50 m² con dormitorio, cocina, salón-comedor, baño y balcón; equipamiento similar al Blue (kitchenette, menaje, microondas, lavadora, plancha), más A/C, TV, minibar, locker, escritorio, zona de estar, ducha, toiletries, secador, kettle y WiFi. 

### Total de habitaciones (21) y categoría “Doble Económica”

En la web oficial revisada no aparece explícitamente un contador de “número total de habitaciones/unidades”. 

Sin embargo, varias fuentes de distribución turística publican que el alojamiento tendría **21 habitaciones** (p. ej., reseñas/portales tipo “boutique hotels” o agregadores). Esto es útil como pista, pero conviene tratarlo como dato **secundario** frente al PMS/channel manager propio. 

Sobre **“Habitación Doble Económica”**, sí aparece como tipo de habitación en listados de metabuscadores (ejemplo: Google Hoteles) aunque no se muestre en el “menú de tipos” del sitio oficial. Esto sugiere que la categoría existe en canal/OTA o motor externo, y debe modelarse en la base de conocimiento aunque la web principal no la describa con detalle. 

## Servicios, amenities y localización operativa

### Servicios y equipamiento publicados

El sitio oficial enumera explícitamente (entre otros): atención personalizada, tecnología para aperturas y registros, información turística, y celebraciones (cumpleaños/aniversarios). 

En limpieza y confort, menciona servicio de limpieza, amenities, toallas, sábanas y almohadas confortables. 

En facilities/equipamiento general, incluye wifi gratuito, climatizador frío/calor, caja fuerte, nevera, Smart TV en todas las habitaciones, y taquillas/almacenamiento de equipaje. 

**Nota sobre “2 botellas de agua”**: no aparece en la lista pública de servicios/facilities del sitio; si queréis que el agente lo trate como “promesa de estancia”, debe introducirse como dato de negocio (fuente interna) y versionarse. 

### Parking y distancias

El sitio oficial indica **parking público gratuito a 200 metros** (2 minutos caminando) del hostal. 

En “condiciones generales” se añade el detalle operativo del parking: **parking público gratuito en Calle La Mar 98, detrás de la estación de tren** (sin coste, sin responsabilidad por robo/daños). 

Sobre cercanía a playa: la web oficial habla de “a pocos metros del mar”.   
En fuentes externas (p. ej., metabuscadores/OTAs) aparecen distancias como ~100 m a playa (ejemplo: Amimir menciona 100 m de la playa de La Roda). Útil para FAQs, pero idealmente el agente debería responder con formulaciones prudentes (“a pocos minutos andando”) salvo que tengáis la métrica exacta validada internamente. 

## Políticas operativas y condiciones de reserva

Las “General conditions” del sitio (en inglés) aportan reglas que conviene convertir en conocimiento estructurado y en FAQ:

El **check-in** está disponible a partir de las 15:00 y el **check-out** debe completarse antes de las 12:00; además, se menciona consigna/taquillas gratuitas para equipaje y un buzón para dejar llaves a la salida. 

Política de adultos: el alojamiento es para **adultos y niños mayores de 10 años**. 

Espacio libre de humo: el establecimiento es **smoke-free** y el incumplimiento puede conllevar cargos. 

Daños y pérdidas: se listan cargos por toallas (10€ pequeña, 15€ grande) y por elementos decorativos según su valor. 

Bicicletas y patinetes eléctricos: no están permitidos dentro del alojamiento ni en las habitaciones. 

Mascotas: no se permiten. 

Horario del departamento de reservas: atención telefónica de lunes a domingo 10:00–17:00; reservas web 24/7. 

Pago y cancelación: se requiere tarjeta válida; el pago debe hacerse antes del periodo no reembolsable (no más tarde de 5 días antes de llegada); cancelación gratuita hasta 5 días antes; sin cambios de fecha dentro de los 5 días previos; en tarifa no reembolsable no se permiten cancelaciones/modificaciones; fuerza mayor queda a revisión del equipo de reservas. 

## Datos estructurados para la nueva base de conocimiento

A continuación incluyo un diseño de datos pensado para: (a) servir como “single source of truth” del agente, (b) permitir RAG híbrido (filtros + embeddings), y (c) soportar discrepancias entre web/OTAs/datos internos.

### Esquema JSON recomendado

**Hotel (perfil y políticas)** (derivado del sitio oficial). 

```json
{
  "kb_version": "2026-03-24",
  "source": {
    "primary_domain": "bluesardinealtea.com",
    "retrieved_local_date": "2026-03-24",
    "notes": "Datos extraídos del sitio oficial y condiciones generales. Algunos datos (inventario/precio) vienen de input interno."
  },
  "property": {
    "name": "Blue Sardine Altea",
    "category": "hostal_boutique",
    "city": "Altea",
    "region": "Alicante",
    "country": "ES",
    "address_public": "Calle Pescadores 1, 03590, Altea, Alicante",
    "contact": {
      "phone": "+34 629 610 233",
      "email": "info@bluesardinealtea.com"
    },
    "positioning": {
      "summary": "Alojamiento boutique en un antiguo barrio de pescadores, cerca del mar y del casco histórico.",
      "themes": ["innovacion", "diseno", "sostenibilidad", "limpieza", "hospitalidad", "localizacion"]
    }
  },
  "policies": {
    "check_in": "15:00",
    "check_out": "12:00",
    "luggage_storage": {
      "lockers_free": true,
      "key_drop_mailbox": true
    },
    "adults_and_children": {
      "adults_only": true,
      "children_allowed_from_age": 10
    },
    "smoke_free": true,
    "pets_allowed": false,
    "bicycles_and_scooters_allowed_inside": false,
    "damages_fees_eur": {
      "towel_small": 10,
      "towel_large": 15,
      "decor_items": "according_to_value"
    },
    "reservation_hours": {
      "phone_support": "Mon-Sun 10:00-17:00",
      "website_booking": "24/7"
    },
    "payment_and_cancellation": {
      "card_required": true,
      "payment_deadline_days_before_arrival": 5,
      "free_cancellation_until_days_before_arrival": 5,
      "date_changes_allowed_within_days_before_arrival": false,
      "non_refundable": {
        "cancellation_allowed": false,
        "date_modification_allowed": false
      },
      "force_majeure": "case_by_case_review"
    }
  },
  "parking": {
    "available_on_site": false,
    "public_free_parking": {
      "available": true,
      "walking_distance_m": 200,
      "location_note": "Calle La Mar 98 (detras de la estacion de tren)",
      "liability_note": "No responsable de robos/danos en parking"
    }
  },
  "services_and_facilities": {
    "experience": [
      "atencion_personalizada",
      "tecnologia_para_aperturas_y_registros",
      "informacion_turistica",
      "celebracion_cumpleanos_aniversarios"
    ],
    "housekeeping": [
      "servicio_de_limpieza",
      "amenities",
      "toallas",
      "sabanas_y_almohadas_confortables"
    ],
    "in_room_and_property": [
      "wifi_gratuito",
      "climatizacion_frio_calor",
      "caja_fuerte",
      "nevera_o_minibar",
      "smart_tv_en_todas_las_habitaciones",
      "taquillas_y_almacenamiento_equipaje"
    ]
  }
}
```

### Tipos de habitación/unidad (canónico web + extensiones)

**Inventario canónico descrito en la web** (sin contar “económica”, que no está descrita en la web principal). 

```json
{
  "room_types": [
    {
      "id": "standard_room",
      "display_name_es": "Habitación Doble Estándar",
      "occupancy": { "adults_max": 2 },
      "bed": "doble",
      "area_sqm": 15,
      "features": ["climatizacion_frio_calor", "tv", "minibar", "locker", "zona_de_estar", "ducha", "amenities_bano", "secador", "wifi"]
    },
    {
      "id": "superior_room",
      "display_name_es": "Habitación Doble Superior",
      "occupancy": { "adults_max": 2 },
      "bed": "doble",
      "area_sqm": 18,
      "features": ["climatizacion_frio_calor", "tv", "minibar", "locker", "zona_de_estar", "ducha", "amenities_bano", "secador", "wifi"]
    },
    {
      "id": "premium_room",
      "display_name_es": "Habitación Doble con Terraza",
      "occupancy": { "adults_max": 2 },
      "bed": "doble",
      "area_sqm": null,
      "highlights": ["terraza_independiente", "vistas_mar_y_casco_antiguo"],
      "features": ["climatizacion_frio_calor", "tv", "minibar", "locker", "zona_de_estar", "wifi", "ducha", "amenities_bano", "secador", "hervidor", "cafetera"]
    },
    {
      "id": "studio_with_terrace",
      "display_name_es": "Estudio con Terraza",
      "occupancy": { "adults_max": 2 },
      "bed": "doble",
      "area_sqm": 30,
      "highlights": ["balcon", "terraza_principal", "estancias_largas"],
      "features": ["climatizacion_frio_calor", "tv", "minibar", "locker", "escritorio", "zona_de_estar", "ducha", "amenities_bano", "secador", "hervidor", "microondas", "plancha", "wifi"]
    },
    {
      "id": "blue_apartment",
      "display_name_es": "Apartamento Blue",
      "occupancy": { "adults_max": 2 },
      "bed": "doble",
      "area_sqm": 50,
      "layout": ["dormitorio", "cocina", "salon_comedor", "bano"],
      "features": ["climatizacion_frio_calor", "tv", "minibar", "locker", "escritorio", "zona_de_estar", "ducha", "amenities_bano", "secador", "hervidor", "kitchenette", "menaje", "microondas", "lavadora", "plancha", "wifi"]
    },
    {
      "id": "sardine_apartment",
      "display_name_es": "Apartamento Sardine",
      "occupancy": { "adults_max": 2 },
      "bed": "doble",
      "area_sqm": 50,
      "layout": ["dormitorio", "cocina", "salon_comedor", "bano", "balcon"],
      "features": ["climatizacion_frio_calor", "tv", "minibar", "locker", "escritorio", "zona_de_estar", "ducha", "amenities_bano", "secador", "hervidor", "kitchenette", "menaje", "microondas", "lavadora", "plancha", "wifi"]
    }
  ],
  "room_type_extensions": [
    {
      "id": "double_economic",
      "display_name_es": "Habitación Doble Económica",
      "source": "metabuscadores_otAs",
      "notes": "Aparece como tipología en canales externos, pero no está descrita en la web principal. Requiere ficha interna (m2, amenities, fotos, reglas).",
      "needs_internal_validation": true
    }
  ]
}
```

### Matriz de precios y recuento de unidades (input tuyo / “config de negocio”)

El sitio oficial revisado no publica esta matriz de precios “por temporada” en abierto; por tanto, lo siguiente se modela como **dato interno** (debe tratarse como configuración versionada, con fecha de vigencia y responsable). 

Además, hay una discrepancia aritmética: tus unidades por tipo suman 20, mientras que en fuentes externas se menciona 21 habitaciones. Recomiendo incluir un campo “inventory_gap” para forzar revisión. 

```json
{
  "pricing_and_inventory_internal": {
    "currency": "EUR",
    "pricing_model": "seasonal",
    "status": "client_provided_requires_validation",
    "inventory_breakdown": [
      { "room_type_id": "double_economic", "units": 2, "base_price_eur": 70 },
      { "room_type_id": "standard_room", "units": 11, "base_price_eur": 80 },
      { "room_type_id": "superior_room", "units": 3, "base_price_eur": 100 },
      { "room_type_id": "premium_room", "units": 1, "base_price_eur": 150 },
      { "room_type_id": "studio_with_terrace", "units": 1, "base_price_eur": 160 },
      { "room_type_id": "blue_apartment", "units": 1, "base_price_eur": 175 },
      { "room_type_id": "sardine_apartment", "units": 1, "base_price_eur": 190 }
    ],
    "inventory_sum_units": 20,
    "inventory_expected_units_external_hint": 21,
    "inventory_gap_units": 1,
    "season_definitions_placeholder": [
      {
        "season_id": "low",
        "date_ranges": [],
        "price_multiplier": 1.0
      },
      {
        "season_id": "high",
        "date_ranges": [],
        "price_multiplier": 1.0
      }
    ]
  }
}
```

### CSV mínimo (para BI, tarifas y pruebas rápidas)

```csv
room_type_id,display_name_es,units,base_price_eur
double_economic,Habitación Doble Económica,2,70
standard_room,Habitación Doble Estándar,11,80
superior_room,Habitación Doble Superior,3,100
premium_room,Habitación Doble con Terraza,1,150
studio_with_terrace,Estudio con Terraza,1,160
blue_apartment,Apartamento Blue,1,175
sardine_apartment,Apartamento Sardine,1,190
```

## Datos no estructurados para RAG

Para un agente hotelero suele funcionar bien un **corpus mixto**:
- “Documentos de referencia” (descripciones y políticas resumidas con neutralidad).
- “FAQ canónica” (preguntas frecuentes con respuestas cortas y citables).
- “Snippets por tipo de habitación” (amenities y puntos diferenciales).
- “Reglas de cumplimiento” (lo que el agente debe decir siempre y lo que nunca debe prometer).

A continuación, propongo un paquete de documentos **no verbatim** (parafraseados), cada uno con metadatos de trazabilidad al origen.

### Documentos (formato recomendado)

```json
{
  "documents": [
    {
      "doc_id": "bs_overview_es",
      "language": "es-ES",
      "title": "Resumen del alojamiento y propuesta de valor",
      "body": "Alojamiento boutique restaurado en un antiguo barrio de pescadores, cerca del mar y al inicio del casco histórico. Ofrece habitaciones y apartamentos con enfoque en confort moderno, detalle en diseño y apoyo tecnológico para la estancia.",
      "metadata": {
        "source_priority": "official",
        "source_urls": ["https://bluesardinealtea.com/"],
        "tags": ["overview", "location", "boutique"]
      }
    },
    {
      "doc_id": "bs_services_es",
      "language": "es-ES",
      "title": "Servicios, limpieza y equipamiento",
      "body": "Servicios destacados: atención personalizada, apoyo tecnológico para aperturas y registros, información turística y opciones para celebraciones. Limpieza: servicio de limpieza, amenities, toallas, sábanas y almohadas confortables. Equipamiento: wifi gratuito, climatización frío/calor, caja fuerte, nevera/minibar, Smart TV, taquillas y almacenamiento de equipaje.",
      "metadata": {
        "source_priority": "official",
        "source_urls": ["https://bluesardinealtea.com/"],
        "tags": ["services", "housekeeping", "amenities", "facilities"]
      }
    },
    {
      "doc_id": "bs_parking_es",
      "language": "es-ES",
      "title": "Parking",
      "body": "Hay parking público gratuito aproximadamente a 200 metros andando. En condiciones generales se indica como referencia Calle La Mar 98 (detrás de la estación de tren) y que no hay responsabilidad por robos o daños en el parking.",
      "metadata": {
        "source_priority": "official",
        "source_urls": ["https://bluesardinealtea.com/", "https://bluesardinealtea.com/en/general-conditions/"],
        "tags": ["parking", "location"]
      }
    },
    {
      "doc_id": "bs_policies_es",
      "language": "es-ES",
      "title": "Condiciones generales: horarios y normas",
      "body": "Check-in a partir de las 15:00 y check-out antes de las 12:00. Hay taquillas gratuitas para equipaje y un sistema para dejar llaves. Alojamiento orientado a adultos (y niños mayores de 10). Espacio sin humo. No se permiten mascotas. No se permiten bicicletas ni patinetes eléctricos dentro. Se aplican cargos por daños o pérdida (p. ej., toallas).",
      "metadata": {
        "source_priority": "official",
        "source_urls": ["https://bluesardinealtea.com/en/general-conditions/"],
        "tags": ["policies", "checkin", "checkout", "rules"]
      }
    }
  ]
}
```

Estos documentos se fundamentan en el sitio oficial (home + páginas de cada tipología + condiciones generales). 

### FAQ canónica sugerida (para “handoff” directo al agente)

```json
{
  "faq": [
    {
      "q": "¿A qué hora es el check-in y el check-out?",
      "a": "El check-in es a partir de las 15:00 y el check-out debe hacerse antes de las 12:00.",
      "sources": ["https://bluesardinealtea.com/en/general-conditions/"]
    },
    {
      "q": "¿Hay parking?",
      "a": "No hay parking dentro del alojamiento, pero hay parking público gratuito a unos 200 metros andando. En condiciones generales se menciona Calle La Mar 98 (detrás de la estación de tren).",
      "sources": ["https://bluesardinealtea.com/", "https://bluesardinealtea.com/en/general-conditions/"]
    },
    {
      "q": "¿Se admiten mascotas?",
      "a": "No, no se permiten mascotas.",
      "sources": ["https://bluesardinealtea.com/en/general-conditions/"]
    },
    {
      "q": "¿Es un alojamiento solo para adultos?",
      "a": "Según las condiciones generales, está orientado a adultos y se admiten niños a partir de 10 años.",
      "sources": ["https://bluesardinealtea.com/en/general-conditions/"]
    },
    {
      "q": "¿Qué incluye el equipamiento básico en habitaciones?",
      "a": "De forma general se publica wifi gratuito, climatización frío/calor, caja fuerte, nevera/minibar y Smart TV. En cada tipología se listan también TV, minibar y amenities de baño.",
      "sources": ["https://bluesardinealtea.com/", "https://bluesardinealtea.com/en/standard-room/"]
    }
  ]
}
```

Las respuestas anteriores están alineadas con “General conditions” y el “home” del sitio (más páginas de habitación para equipamiento). 

## Instrucciones para Claude Haiku 4.5 para integrar la nueva base en el POC

Estas instrucciones están pensadas para que Claude revise **vuestro codebase real** (arquitectura actual, rutas, módulos, prompts, vector store) y lo adapte a un dominio “hotelero”. Como aquí no tengo acceso al repositorio, el guion se centra en qué inspeccionar, qué decisiones tomar, y cómo integrar los datos anteriores sin romper el POC.

### Objetivo técnico

Convertir el POC de “real estate agent” en un “hotel guest assistant” manteniendo la arquitectura (RAG, herramientas, UI) pero sustituyendo:
- **Fuentes de conocimiento**: inmuebles → hotel (habitaciones, políticas, servicios, ubicaciones, precios).
- **Ontología/esquemas**: property listing fields → room_type + policies + inventory/pricing.
- **Prompts**: intención de compra/venta → intención de reserva/estancia/soporte.

### Pasos de análisis del codebase (debe ejecutar Claude)

1) **Mapa rápido de arquitectura**
- Identifica lenguaje y framework (Node/Python, Next.js/FastAPI, etc.).
- Localiza: `prompts/`, `rag/`, `retriever/`, `embeddings/`, `vectorstore/`, `tools/`, `schemas/`, `config/`, `data/`.
- Encuentra “entrypoints” del agente (por ejemplo: `agent.ts`, `agent.py`, `chat_controller`, `orchestrator`).

2) **Inventario de la base de conocimiento actual**
- Localiza el origen actual: JSON/CSV/Markdown, o scraping de portales inmobiliarios.
- Identifica el pipeline de ingestión: chunking, embeddings, upsert al vector DB (Pinecone/Qdrant/Chroma/etc.).
- Localiza evaluaciones (golden tests / conversation tests). Si no existen, crea mínimos.

3) **Puntos de cambio mínimo**
- Determina si el POC usa:
  - RAG “simple” (solo vector search), o
  - RAG “híbrido” (filtros + vector + reranking), o
  - tool-calling (p. ej., “buscar inmuebles”, “calcular hipoteca”).
- Señala qué herramientas deben retirarse o renombrarse (p. ej., mortgage calculator → “cotizar estancia”, “explicar políticas”).

### Integración de datos (lo que Claude debe implementar)

4) **Añadir un nuevo paquete de datos versionado**
- Crear carpeta (ejemplo): `data/blue_sardine_kb/2026-03-24/`
  - `hotel.json`
  - `room_types.json`
  - `pricing_inventory_internal.json`
  - `faq.json`
  - `documents.json`
- Añadir `manifest.json` con checksums y metadatos:
  - fecha, fuentes, responsable, y “confidence”.

5) **Actualizar el esquema de dominio**
- Si existe `schemas/propertyListing.json`, crear `schemas/hotelKnowledge.json`:
  - `property`, `room_types`, `policies`, `services_and_facilities`, `parking`, `pricing_and_inventory_internal`.
- Implementar validación en runtime (zod/pydantic/ajv) y fallar temprano.

6) **Reindexar el vector store**
- Convertir `documents.json` + `faq.json` en “chunks”:
  - target 400–800 tokens, solape 80–120 tokens.
  - `metadata`: `doc_id`, `tags`, `source_priority`, `version`, `language`.
- Ejecutar reindex (script `ingest_kb.*`) y confirmar:
  - número de chunks,
  - cobertura por tags (policies, parking, room_types),
  - latencia y coste.

7) **Actualizar el prompt del agente**
- Sustituir objetivos (inmuebles) por objetivos de huéspedes:
  - responder preguntas de estancia,
  - ser estricto con políticas (check-in/out, pets, smoke),
  - evitar prometer datos no confirmados (p. ej., “2 botellas de agua” si está marcado como interno/no verificado).
- Añadir “policy precedence”:
  1) `official` > 2) `internal_validated` > 3) `internal_unvalidated` > 4) `third_party`.
- Añadir instrucciones de estilo: respuestas cortas, con posibilidad de ampliar; pedir fechas solo si es imprescindible; proponer alternativas cuando una restricción bloquea.

8) **Implementar “routing” por intención**
- Si existe clasificador de intención (buy/sell/rent), reemplazar por:
  - `availability_pricing` (si hay motor),
  - `room_selection`,
  - `policies`,
  - `location_and_parking`,
  - `special_requests` (celebraciones).
- Implementar fallback: si falta dato, el agente debe decir “no lo tengo confirmado” y ofrecer contacto telefónico/email (del perfil). 

9) **Tratamiento de precios y temporadas**
- Integrar `pricing_inventory_internal.json` como **config**, no como verdad externa.
- Añadir un “guardrail”:
  - Si el usuario pide precio para fechas concretas, el agente debe:
    - pedir fechas exactas,
    - advertir que puede variar por temporada/ocupación,
    - si no hay motor de reservas integrado, devolver “precio orientativo desde X€” y recomendar confirmar en web o por contacto.
- Registrar en logs cuándo se usa “unvalidated pricing”.

10) **Tests y verificación**
- Crear pruebas tipo:
  - “¿Se admiten mascotas?” → “No”.
  - “¿Horario check-in/out?” → 15:00/12:00.
  - “¿Hay parking?” → público gratuito ~200 m + nota Calle La Mar 98.
  - “Describe Habitación Doble Estándar” → 15 m² + amenities.
- Añadir tests de “no hallucination”:
  - si preguntan “¿Incluye 2 botellas de agua?” y eso está `unverified`, respuesta debe ser prudente.

### Checklist de entrega

- El agente responde políticas y servicios citando consistentemente el dataset oficial.   
- Los tipos de habitación del agente están alineados con la web (Standard/Superior/Premium/Studio/Apartamentos).   
- La discrepancia 20 vs 21 unidades queda registrada como “inventory_gap” hasta validación interna. 