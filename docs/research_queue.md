# Cola de investigación externa — QuantAgentFactory

Preguntas que `investigator`/`protocol` no pueden resolver solos (evidencia insuficiente vía WebSearch/WebFetch, requiere síntesis amplia, o el patrón necesita una segunda opinión). Alexander las resuelve fuera de este pipeline (Gemini Deep Research u otra herramienta de su propia suscripción) y entrega el informe en `docs/research_external/<slug>.md`.

**Ningún agente se queda bloqueado esperando esto.** Mientras una pregunta sigue `PENDIENTE`, el agente que la escribió sigue trabajando en lo que sí puede resolver solo (otras hipótesis, specs ya registradas, corridas de `engine`).

## Cómo se usa
1. El agente que encuentra la pregunta la agrega abajo, en "Preguntas pendientes", con el formato de contrato.
2. Alexander la resuelve cuando tiene tiempo, en la herramienta externa que prefiera — priorizando fuentes de Mariel/Cueva Alfa/Trade Simple cuando la pregunta sea de metodología de validación, y literatura académica/industria cuando sea de una ineficiencia de mercado específica.
3. El informe se guarda en `docs/research_external/<slug>.md` con: fuente, qué demuestra, qué no demuestra, aplicabilidad al símbolo/timeframe real del proyecto, nivel de confianza.
4. El agente que la pidió (o quien retome el trabajo) mueve la entrada a "Preguntas respondidas", cita el archivo del informe, y continúa el trabajo que estaba esperando esa evidencia.

Nota: la herramienta externa no importa (Gemini, Copilot u otra) — lo único que le importa al pipeline es que el informe final llegue a `docs/research_external/<slug>.md` con los campos del contrato. Estados: `PENDIENTE` (nadie la tomó todavía) → `EN_PROGRESO (<herramienta>)` (alguien ya la está corriendo fuera) → `RESPONDIDA` (informe ya guardado).

## Formato de contrato (copiar por cada pregunta nueva)
```
### <slug> — PENDIENTE
- Pregunta: <una pregunta concreta, no un tema general>
- Origen: <agente, hipótesis/spec relacionada, fecha>
- Fuentes esperadas: <papers, foros serios, documentación de plataformas — nunca opinión sin evidencia>
- Qué debe traer el informe: fuente + cita, qué demuestra, qué no demuestra, aplicabilidad a <símbolo/timeframe>, nivel de confianza
- Criterio de rechazo: <cuándo el informe NO sirve, ej. "evidencia solo en acciones líquidas de EEUU, sin CFD/OTC">
```

## Preguntas pendientes

### kama-kaufman-valores-base-y-salida — PENDIENTE
- Pregunta: ¿Qué valores de ER_Length y FastMA_Length (con SlowMA_Length = 30) y qué regla de salida distinta del stop (señal opuesta, stop-and-reverse, take profit, salida por tiempo u otra) define Perry Kaufman para el sistema AMA/KAMA con giro y filtro en Smarter Trading (1995) y/o Trading Systems and Methods? ¿Declara también la inicialización de la AMA y el timeframe de sus ejemplos?
- Origen: protocol, hipótesis #007 / `docs/specs/xauusd-d1-kama-tendencial-con-efficiency-ratio.md` (secciones 8 y 14), 2026-09-22. `docs/research_external/` no contiene informe previo (verificado).
- Fuentes esperadas: texto original de Kaufman (edición y página); en segundo lugar, documentación que cite ese texto con página
- Qué debe traer el informe: fuente + cita textual, qué demuestra, qué no demuestra, año de publicación de los valores (deben ser anteriores al IS 1998-2018 o independientes de él), aplicabilidad a XAUUSD D1, nivel de confianza; señalar cualquier discrepancia con la regla de Oxford (filtro 0.01 x StdDev(ΔAMA, 20), stop 6 x ATR(20))
- Criterio de rechazo: valores por defecto de plataformas sin cita al texto de Kaufman; valores elegidos por optimización sobre datos que se solapen con 1998-2018 (incluidos los gráficos de sensibilidad de Oxford); blogs o cursos sin cita verificable

### vwap-tick-volume-proxy — EN_PROGRESO (Copilot/VS Code)
- Pregunta: ¿Existe evidencia (papers, estudios de microestructura, backtests serios documentados) de reversión hacia VWAP calculado con `tick_volume` (conteo de cambios de precio) en vez de volumen real ejecutado, específicamente en CFDs o futuros de índices? ¿O toda la evidencia de "VWAP reversion" que existe asume volumen centralizado real y no dice nada sobre el proxy de tick volume?
- Origen: `docs/vwap-ndx-h1-draft.md`, borrador VWAP NDX H1, 2026-09-22
- Fuentes esperadas: papers de microestructura de mercado, estudios sobre ejecución algorítmica/institucional vs VWAP, cualquier estudio que compare explícitamente tick volume vs volumen real como proxy
- Qué debe traer el informe: fuente + cita, qué demuestra, qué no demuestra, aplicabilidad a NDX/NAS100 CFD H1, nivel de confianza
- Criterio de rechazo: evidencia que solo aplica a futuros/acciones con volumen centralizado real, sin abordar el caso de proxy por tick volume

### vwap-variantes-anchored — EN_PROGRESO (Copilot/VS Code)
- Pregunta: ¿Qué variantes de VWAP (diario, semanal, anchored a evento, sesión regular vs extendida) están documentadas en la literatura o práctica profesional entre 2015-2025, y cuáles tienen evidencia de uso específico para índices vía CFD (no solo acciones individuales o futuros líquidos)?
- Origen: `docs/vwap-ndx-h1-draft.md`, sección 3 (variante propuesta), 2026-09-22
- Fuentes esperadas: documentación de plataformas profesionales, libros de trading algorítmico, papers de ejecución, comparativas publicadas de variantes VWAP
- Qué debe traer el informe: tabla de variantes con reinicio/datos necesarios/uso típico (puede ampliar la que ya está en el draft), fuente de cada una, aplicabilidad a NDX/NAS100 H1, nivel de confianza
- Criterio de rechazo: fuentes que promocionan un indicador/curso sin evidencia independiente de que la variante funcione

### vwap-sesion-cfd-vs-futuro — EN_PROGRESO (Copilot/VS Code)
- Pregunta: NAS100/NDX como CFD sigue el futuro Nasdaq casi 24h, no la sesión de acciones de contado. ¿Hay evidencia o práctica documentada de que la sesión regular NYSE (09:30–16:00 America/New_York) siga siendo el ancla relevante para el comportamiento de precio en el CFD/futuro, o el mecanismo de "convergencia a VWAP" se diluye/cambia fuera de exchange hours de acciones?
- Origen: `docs/vwap-ndx-h1-draft.md`, sección 3 y bloqueo #4, 2026-09-22
- Fuentes esperadas: estudios de microestructura sobre futuros de índices (ES, NQ) y su relación con la sesión de acciones subyacente, documentación de exchanges (CME) sobre volumen/actividad por franja horaria
- Qué debe traer el informe: fuente + cita, qué demuestra, qué no demuestra, aplicabilidad específica a NDX/NAS100 CFD H1, nivel de confianza
- Criterio de rechazo: evidencia que solo describe la sesión de acciones sin conectar con el comportamiento del futuro/CFD fuera de esa ventana

## Preguntas respondidas
(vacío todavía)
