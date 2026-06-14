# Casos de uso para demo del agente Blue Sardine Altea

Este documento propone tres llamadas de demo basadas en la base de conocimiento actual del hotel. Estan pensadas para demostrar que el agente responde de forma breve, natural y util durante una llamada telefonica real.

## Caso 1: Consulta rapida de precio y disponibilidad

### Objetivo

Demostrar que el agente puede responder directamente a precios base y disponibilidad sin bloquearse pidiendo fechas.

### Datos que debe usar

- Habitacion Doble Estandar: 110 EUR por noche, para una o dos personas.
- Habitacion Doble con Terraza / Premium: 185 EUR por noche.
- Disponibilidad actual: 5 estandar y 1 Premium con terraza.
- La reserva definitiva la cierra el equipo de reservas o la web.

### Guion sugerido

**Usuario:** Hola, queria saber si teneis habitacion para dos.

**Agente esperado:** Si, ahora mismo tenemos dobles estandar, superiores y una Premium con terraza disponibles.

**Usuario:** Cuanto cuesta una doble estandar?

**Agente esperado:** La doble estandar cuesta 110 euros por noche, para una o dos personas.

**Usuario:** Y hay alguna con terraza?

**Agente esperado:** Si, queda una Premium con terraza, a 185 euros por noche.

**Usuario:** Vale, quiero reservarla.

**Agente esperado:** Perfecto. Para dejar la reserva confirmada, lo gestiona el equipo de reservas o puede hacerlo desde la web.

### Criterios de exito

- No pide fechas para dar precio base.
- Da disponibilidad de forma directa.
- Menciona que queda una Premium para sonar real.
- Hace handoff solo cuando el usuario quiere confirmar la reserva.

### Variaciones utiles

- "Somos dos, cuanto sale la superior?"
- "Y tres noches en la premium?"
- "Do you have a room with terrace available?"

## Caso 2: Recomendacion de habitacion segun preferencia

### Objetivo

Demostrar que el agente no solo recupera datos, sino que recomienda una tipologia adecuada segun presupuesto, terraza, cocina o estancia larga.

### Datos que debe usar

- Opcion mas economica: Habitacion Doble Economica, 95 EUR por noche.
- Terraza y vistas: Premium con terraza, 185 EUR por noche.
- Estancias largas: Estudio con Terraza, 30 m2, microondas, 195 EUR por noche.
- Cocina y lavadora: Apartamento Blue o Apartamento Sardine, 50 m2, dormitorio, cocina, salon-comedor, bano y lavadora.
- Todas las habitaciones admiten maximo 2 adultos.

### Guion sugerido

**Usuario:** Estoy mirando para varios dias, que habitacion me recomiendas?

**Agente esperado:** Para varios dias le recomendaria el Estudio con Terraza, porque tiene 30 metros cuadrados y microondas. Cuesta 195 euros por noche.

**Usuario:** Y si queremos cocina?

**Agente esperado:** Entonces encajan mejor el Apartamento Blue o el Apartamento Sardine. Tienen dormitorio, cocina, salon-comedor, bano y lavadora.

**Usuario:** Somos tres adultos, nos vale una habitacion?

**Agente esperado:** Las habitaciones son para maximo dos adultos. Para tres adultos, lo mejor seria reservar dos habitaciones o anadir un apartamento.

### Criterios de exito

- Recomienda sin listar todo el catalogo.
- Explica diferencias clave: espacio, terraza, cocina y lavadora.
- No inventa habitaciones triples.
- Mantiene respuestas de una o dos frases.

### Variaciones utiles

- "Quiero la mas barata."
- "Quiero algo con terraza."
- "Somos dos y queremos cocina."
- "Cual es la mejor habitacion?"

## Caso 3: Informacion operativa y fallback seguro

### Objetivo

Demostrar cobertura de localizacion, horarios, servicios y escalado seguro cuando el dato requiere confirmacion humana.

### Datos que debe usar

- Direccion publica principal: Calle Pescadores 1, 03590 Altea, Alicante.
- Cerca del mar y al inicio del casco historico.
- TRAM de Altea a unos 200 metros.
- Reservas por telefono: lunes a domingo, 10:00-17:00.
- Reservas online: 24/7.
- Soporte de recepcion: 09:00-21:00.
- Urgencias de huespedes alojados: hasta las 23:00.
- Servicios: wifi, climatizacion frio-calor, Smart TV, caja fuerte, nevera o minibar, limpieza, informacion turistica, taquillas y parking publico gratuito cercano.
- No hay restaurante propio, piscina, spa ni gimnasio.
- Accesibilidad y taxi/GPS exacto requieren confirmacion.

### Guion sugerido

**Usuario:** Donde esta el hotel? Esta cerca del mar?

**Agente esperado:** Blue Sardine Altea esta en Calle Pescadores 1, en Altea. Esta cerca del mar y al inicio del casco historico.

**Usuario:** Y teneis recepcion 24 horas?

**Agente esperado:** No es recepcion 24 horas. El soporte de recepcion es de 09:00 a 21:00, y para huespedes alojados hay urgencias telefonicas hasta las 23:00.

**Usuario:** Hay piscina o restaurante?

**Agente esperado:** No hay piscina, spa, gimnasio ni restaurante propio. Si quiere, pueden recomendarle opciones cercanas para comer o desayunar.

**Usuario:** Necesito la direccion exacta para un taxi.

**Agente esperado:** La direccion publica principal es Calle Pescadores 1. Para taxi o GPS exacto, es mejor confirmarlo con recepcion porque tambien aparece una referencia de Calle La Mar.

### Criterios de exito

- Responde ubicacion y horarios sin dudar.
- No promete servicios que no existen.
- Escala de forma natural cuando hay riesgo de error operativo.
- No menciona RAG, base de conocimiento, Qdrant ni detalles internos.

### Variaciones utiles

- "Como llego desde el aeropuerto?"
- "Esta cerca del TRAM?"
- "El desayuno esta incluido?"
- "Teneis habitaciones adaptadas para silla de ruedas?"
