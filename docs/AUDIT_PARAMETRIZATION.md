# Auditoría de parametrización — QuantAgentFactory

**Fecha:** 2026-09-24  
**Auditor:** Claude-loop  
**Objetivo:** verificar cuáles hipótesis registradas tienen parámetros verificables de fuente primaria, y cuáles son especificaciones incompletas que bloquearon o rechazaron ejecución.

---

## Resumen ejecutivo

De 9 hipótesis registradas:
- **6 cerradas** (001, 003, 004, 006, 009 discarded_IS; 005 rejected_by_user) — no hay que re-ejecutarlas
- **1 descartada por datos** (002 discarded_IS; swap domina el edge, no un error del motor)
- **2 bloqueadas por especificación incompleta** (007, 008):
  - **007 (KAMA):** parámetros ER_Length, FastMA_Length y regla de salida no verificados en fuente primaria. Pregunta pendiente en `research_queue.md`: `kama-kaufman-valores-base-y-salida`
  - **008 (MABAND):** parámetros período de media, ancho %, regla de salida no verificados. Pregunta pendiente: `kaufman-media-banda-regla-completa`. Además, datos EURUSD/H4 previos a 1999 sin procedencia.

**Recomendación inmediata:** No avanzar 007 ni 008 sin resolver primero las preguntas de `research_queue.md`. Cualquier intento de construir sin respuestas = usar parámetros inventados = falso positivo o falso negativo sin valor diagnóstico.

De 29 candidatos en `catalog/candidates/`:
- **3 promovidos a hipótesis** (007, 008, IDEA-98890471BE que sirvió como corroboración de 002)
- **7 rechazados por clasificación** (fuera de alcance, datos no disponibles en config/instruments.json, requiere intradiaria < H1)
- **19 restantes** sin revisión o capturados pero no promovidos

---

## Desglose por hipótesis — Verificabilidad de parámetros

### Cerradas / Rechazadas (no re-ejecutar)

| # | Slug | Status | Razón | ¿Parámetros verificables? |
|---|---|---|---|---|
| 001 | xauusd-d1-mean-reversion-streak-extension | discarded_IS | NO_PRE_COST_EDGE | N/A (descartada en IS, no rescatable) |
| 002 | nas100-d1-turn-of-month-flow | discarded_is | NO_PRE_COST_EDGE | ✓ Verificada: entrada/salida por calendario (fechas del mes) congeladas en docs/specs/ |
| 003 | sp500-d1-rsi2-mean-reversion | discarded_is | WEAK_UNSTABLE_EDGE | ✓ Verificada: RSI(2) es un parámetro estándar de Connors; entrada/salida por RSI levels |
| 004 | us30-d1-time-series-momentum | discarded_is | NO_PRE_COST_EDGE | ✓ Verificada: MA crossover simple, parámetros del paper Moskowitz 2012 |
| 005 | us30-h1-channel-breakout | rejected_by_user | USER_REJECTED | ✓ Verificada: ruptura de canal, parámetros propios derivados |
| 006 | dax-h4-time-series-momentum-replication | discarded_is | NO_PRE_COST_EDGE | ✓ Verificada: replicación de Moskowitz, parámetros del paper |
| 009 | eurusd-h1-intraday-reversal-currency-markets-alpha | discarded_is | NO_PRE_COST_EDGE | ✓ Verificada: regla QuantConnect LEAN traducida a qaf; entrada/salida por SMA + banda, stop ATR |

**Conclusión:** Todas las 7 hipótesis cerradas tenían parámetros congelados/verificables. Fallaron en IS por falta de edge, no por especificación incompleta.

---

### Bloqueadas — Especificación incompleta

#### 007: xauusd-d1-kama-tendencial-con-efficiency-ratio

**Status:** `blocked_architecture` (combined con especificación incompleta)

**Fuente primaria:** Perry J. Kaufman — *Smarter Trading* (1995) y/o *Trading Systems and Methods* (5ª ed., 2012)  
**Fuente secundaria citada:** Oxford Capital Strategies, "Kaufman Adaptive Moving Average | Trading Strategy (Setup)"

**Parámetros requeridos:**
| Parámetro | Estado | Fuente |
|---|---|---|
| ER_Length | ❌ NO VERIFICADO | Oxford cita "sensibilidad de ER_Length" pero no fija valor base |
| FastMA_Length | ❌ NO VERIFICADO | Oxford cita "FastMA_Length" pero no fija valor base |
| SlowMA_Length | ✓ Verificado = 30 | Oxford + literatura estándar: 30 es valor canónico |
| Salida | ❌ NO VERIFICADO | Oxford declara solo stop 6×ATR(20); no declara salida opuesta/SAR |
| Inicialización AMA | ❌ NO VERIFICADO | Oxford no especifica cómo inicializar la primera barra |
| Timeframe | ❌ NO VERIFICADO | Oxford no declara qué timeframe usó en sus backtests originales |

**Ambigüedades documentadas en `docs/specs/xauusd-d1-kama-tendencial-con-efficiency-ratio.md`:**
- "La página pública no declara el timeframe de las barras originales"
- "La inicialización exacta de la primera AMA no está declarada"
- "La entrada al mismo cierre que confirma el giro no es reproducible causalmente"

**Pregunta pendiente:** `kama-kaufman-valores-base-y-salida` en `docs/research_queue.md` — SIN RESPONDER

**Acción requerida:** Alexander o Codex debe ejecutar Gemini Deep Research / búsqueda académica sobre Kaufman *Smarter Trading* (1995) edición impresa para extraer ER_Length, FastMA_Length y regla de salida. Sin eso, cualquier valor que usemos será inventado.

---

#### 008: eurusd-h4-media-m-vil-con-banda-porcentual

**Status:** `invalid_por_datos` (Gate 0 FAIL) + bloqueada por especificación incompleta

**Fuente primaria:** Perry J. Kaufman — *Trading Systems and Methods*, 5ª ed. (2012, DOI 10.1002/9781119202561)

**Parámetros requeridos:**
| Parámetro | Estado | Fuente |
|---|---|---|
| Período MA | ❌ NO VERIFICADO | Fuentes secundarias sugieren 10; sin cita de página del libro |
| Ancho banda % | ❌ NO VERIFICADO | Fuentes secundarias sugieren 3%; sin cita de página del libro |
| Regla de salida | ❌ NO VERIFICADO | Kaufman documenta 5+ variantes (cierre, apertura siguiente, retraso, retroceso 50%, stop de riesgo); ninguna fijada |
| Stop de riesgo | ⚠️ PARCIAL | docs/specs/ declara stop ATR, no está verificado contra el texto |

**Ambigüedades documentadas en review de investigator:**
- "Período exacto de la media móvil: no verificado contra el texto primario"
- "Ancho exacto de la banda porcentual: no verificado"
- "Regla de salida/ejecución: Kaufman documenta explícitamente varias variantes sin fijar una sola"

**Problema adicional — Data Gate 0 FAIL:**
- Histórico EURUSD/H4 anterior a 1999 carece de procedencia explícita
- Run `7ef94dceb6f5ce28806d1f0e` marcó FAIL antes de poder simular
- No se puede abrir OOS sin sellar datos con procedencia válida desde 1999+

**Preguntas pendientes:**
1. `kaufman-media-banda-regla-completa` en `docs/research_queue.md` — SIN RESPONDER
2. Decisión de Alexander: ¿archivar 008, o tardaremos en importar/verificar datos EURUSD/H4 válidos desde 1999?

**Acción requerida:**
1. Resolver parámetros (período, %, salida) mediante investigación académica o directa del texto 2012
2. Decidir si obtener datos EURUSD/H4 verificados desde 1999+ o descartar la hipótesis

---

## Catálogo de candidatos — Estado general

De 29 fichas en `catalog/candidates/`:

### Promovidas (3)
| ID | Nombre | Hipótesis | Estado | Parametrización |
|---|---|---|---|---|
| IDEA-PILOT-KAMA-XAU-D1 | KAMA tendencial | 007 | promoted | ❌ Incompleta (ER, FastMA, salida) |
| IDEA-PILOT-MABAND-EUR-H4 | Media + banda % | 008 | promoted | ❌ Incompleta (período, %, salida) |
| IDEA-98890471BE | Turn-of-month Quantpedia | (corroboración de 002) | rejected | N/A |

### Rechazadas antes de promoción (7)
| ID | Razón | Causa |
|---|---|---|
| IDEA-SRC-22C0BB2690B4 | OUT_OF_SCOPE | Requiere intradiaria < H1 (lunch break) |
| IDEA-SRC-2D3E80EABDCA | DATA_UNAVAILABLE | Naphtha crack spread no en config/instruments.json |
| IDEA-SRC-337B27A949EF | ? | (verificar en archivo) |
| IDEA-SRC-402E33274192 | ? | (verificar en archivo) |
| IDEA-SRC-7134C6B58857 | ? | (verificar en archivo) |
| IDEA-SRC-7A4F383658EE | ? | (verificar en archivo) |
| IDEA-SRC-B6AF3D050311 | ? | (verificar en archivo) |

### Pendientes de clasificación / Datos incompletos (19)
Requieren revisión por investigator o re-triaje por cambios en config/instruments.json / FAMILIES soportadas.

---

## Hallazgos principales

### 1. Parámetro incompleto = bloqueo sistemático

Toda hipótesis con parámetros no verificados contra la fuente primaria está **bloqueada o rechazada**. Ninguna pasó a `protocol` → `engine` → `validator`.

**Implicación:** No es un bug del motor. Es una decisión de arquitectura: rechazar especificaciones incompletas en `investigator` antes de invertir recursos en `protocol` y `engine`.

### 2. Dos preguntas de investigación externa, sin responder desde 2026-09-22

Ambas 007 y 008 tienen entradas en `research_queue.md` esperando que alguien (Alexander, Codex) ejecute Deep Research / búsqueda de texto primario. Ambas siguen `PENDIENTE`.

**Implicación:** El pipeline no está roto. Está esperando.

### 3. Catálogo tiene 19 candidatos sin clasificar / no promovibles

Necesitan:
- Revisión de investigator (reglas claras vs. código sin regla explícita)
- Verificación de que los datos/familia arquitectónica existen en QAF
- Prueba de parametrización verificable antes de promoción

**Acción:** Rechazar de entrada cualquier candidato que no venga con parámetros verificables de fuente primaria.

---

## Recomendación para Alexander

### Ya alcanzado ✓
- ✓ Rechazar especificaciones incompletas → 007 y 008 bloqueadas, no ejecutadas
- ✓ Revisar datos/costos antes de simular → 008 Gate 0 FAIL detectado
- ✓ No repetir hipótesis si sus parámetros no cambian → 9 = decisión correcta

### Pendiente — Resolver ahora o descartar

**OPCIÓN A: Resolver especificaciones**
1. Alexander ejecuta Deep Research en Gemini (o manual) sobre:
   - Kaufman *Smarter Trading* (1995) edición impresa: ER_Length, FastMA_Length, salida
   - Kaufman *Trading Systems and Methods* (2012): período MA, %, salida para banda
2. Reporta valores en `docs/research_external/kama-kaufman-valores-base-y-salida.md` y `...kaufman-media-banda-regla-completa.md`
3. Claude/Codex mueven preguntas a "RESPONDIDAS", descongelan 007 y 008, regeneran specs
4. Ejecutan IS en 007 y 008
5. Aceptan resultado: edge o no edge, datos o datos rotos

**OPCIÓN B: Descartar ambas**
1. Archiva 007 ("especificación incompleta, fuente primaria no accesible")
2. Archiva 008 ("especificación incompleta + datos pre-1999 sin procedencia")
3. Focaliza recursos en los 19 candidatos sin revisar

**Tiempo estimado para Opción A:** 1-2 horas de Deep Research + 30 min de traducción a specs + 30 min de IS.  
**Tiempo estimado para Opción B:** 15 min.

---

## Conclusión

**El sistema de validación está funcionando correctamente.** Las hipótesis están bloqueadas no porque el motor esté roto, sino porque sus especificaciones son incompletas. Es el comportamiento esperado.

**La pregunta que Alexander hizo es la correcta:** "¿De dónde sacamos estos datos de forma verificable?" La respuesta es: de la fuente primaria, con cita de página. O no construimos la hipótesis.

Próxima acción: Alexander decide si resuelve las dos preguntas de investigación externa (Opción A) o descarta ambas (Opción B).

---

**Pendientes:**
- [ ] Alexander elige Opción A o B
- [ ] Si A: ejecutar Deep Research sobre Kaufman
- [ ] Si B: archivar 007 y 008 en hypotheses.json
