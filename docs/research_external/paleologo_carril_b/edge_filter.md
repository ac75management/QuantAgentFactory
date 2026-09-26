# Filtro de edge (Carril B — Paleologo)

**Fuente:** G. Paleologo, FINC-B8420 (Columbia), Lecture 1 "Quant Business Models and Roles"; *The Elements of Quantitative Investing*. Auditado por Grok.
**Carril:** B conceptual. No se mezcla con el triaje `method_only` Paleologo anterior.
**Alcance:** solo candidatos nuevos (012+). No se aplica retroactivamente a 001-011, no reabre ni rescata ninguno.
**Estado:** borrador de Claude. Antes del merge hay que cotejar las 6 etiquetas contra la slide de la Lecture 1 (ver nota al final).

---

## 1. Investing vs trading

Primero se clasifica la hipótesis y después se evalúa su edge. Una misma regla puede ser sólida en un eje y fallar en el otro.

| Eje | Investing | Trading |
|---|---|---|
| De dónde sale el P&L | Pronóstico de retorno esperado (el precio converge a un valor) | Flujo, liquidez o microestructura (cobrar por inmediatez o anticipar flujos) |
| Horizonte | Días a meses | Intradía a pocos días |
| Capacidad | Alta, escala con capital | Baja, se satura rápido |
| Sensibilidad a costos | Moderada | Dominante: el costo es parte del edge |
| Riesgo que se controla | Exposición a factores / beta | Inventario y ejecución |

**Lectura para QAF:** QAF opera un solo instrumento CFD, en H1/H4/D1, con posiciones de días a pocas semanas. Casi todas las hipótesis son timing direccional de serie temporal. No es investing cross-seccional con modelo de riesgo, ni trading de microestructura. Por eso cada hipótesis declara en qué lado cae y **por qué los costos del bróker no se comen el edge** (regla dura 11/17).

---

## 2. Checklist: los 6 mecanismos de edge persistente

> ⚠ Las etiquetas son paráfrasis de Claude y quedan **pendientes de cotejo literal** con la slide. No hubo acceso al PDF desde el entorno (Dropbox bloqueado). Si alguna no coincide, se sustituye la etiqueta y se mantiene la estructura.

Una hipótesis marca **exactamente un mecanismo primario** y contesta las tres columnas. Si no puede contestarlas, no pasa.

| # | Mecanismo (⚠ VERIFICAR) | ¿Quién paga el edge y por qué no deja de pagarlo? | ¿Es compatible con QAF (MT5/CFD, OHLC, ≥H1)? |
|---|---|---|---|
| 1 | Prima de riesgo: cobrar por asumir un riesgo que otros no quieren | Contrapartes que pagan por cubrirse | Sí. Hay que distinguirla de beta pura (ver `beats_baseline`) |
| 2 | Sesgos conductuales de otros participantes | Participantes que repiten errores sistemáticos | Sí. Es el mecanismo típico de las hipótesis QAF |
| 3 | Restricciones estructurales/institucionales (mandatos, benchmarks, flujos forzados, calendario) | Actores obligados a operar sin mirar el precio | Sí, siempre que el flujo sea observable con OHLC y calendario |
| 4 | Ventaja informacional (datos que otros no tienen o reciben tarde) | Quien opera con menos información | **No.** QAF solo tiene OHLC/spread de MT5. Se rechaza como `OUT_OF_SCOPE` |
| 5 | Ventaja analítica: procesar mejor datos públicos | Quien procesa peor el mismo dato | Con reservas: con OHLC público la carga de prueba es máxima (AED p<0.05) |
| 6 | Provisión de liquidez / ventaja de ejecución y costos | Quien paga por inmediatez | **No.** No hay market making ni barras por debajo de H1, y el costo CFD es del bróker. `OUT_OF_SCOPE` |

**Preguntas obligatorias** (van en la ficha `docs/hypotheses/<slug>.md`, sección "Mecanismo de edge"):

- [ ] Lado: investing o trading, justificado con los ejes de la §1.
- [ ] Mecanismo primario (1 solo, de la tabla).
- [ ] Quién está al otro lado y por qué seguirá ahí después de la publicación de la fuente.
- [ ] Qué puerta IS existente lo falsaría primero (ver `pipeline_map.md`).
- [ ] Si el mecanismo es 1: por qué no es solo exposición direccional al activo (debe superar `beats_baseline`).

---

## 3. Uso como filtro dentro de QAF

1. **Dónde:** FASE 1 de `docs/CHECKLIST_HIPOTESIS.md`, durante la revisión de evidencia de `investigator`, antes de `protocol`. No es una puerta nueva del motor y no cambia `qaf/validation.py`, `config/runner.json` ni ningún umbral.
2. **Qué rechaza (antes de gastar un trial IS):**
   - No hay mecanismo declarable → `rejected`, motivo "sin mecanismo de edge".
   - Mecanismo 4 o 6 → `rejected` / `OUT_OF_SCOPE`.
   - Más de un mecanismo "primario", o una explicación circular ("funciona porque el backtest gana") → se devuelve a `investigator`.
3. **Qué NO hace:**
   - No aprueba nada. Pasar el filtro solo da derecho a entrar a protocol. Las puertas IS siguen decidiendo.
   - No inventa edges: solo clasifica el mecanismo que la **fuente primaria** ya declara. Si la fuente no lo explica, el filtro no lo rellena.
   - No reinterpreta resultados. Un `DISCARDED_IS` no se rescata cambiando de mecanismo. Un mecanismo distinto sobre la misma regla es una hipótesis nueva con otro ID y cuenta como trial en el registry.
   - No abre OOS.
4. **Coste:** un párrafo por hipótesis. Su valor está en quemar menos trials del presupuesto de campaña (`campaign_max_trials`) en ideas sin mecanismo, lo que reduce el problema de múltiples pruebas que ya cuenta `count-trials`.

---

**Nota de verificación:** Alexander o Grok cotejan las etiquetas 1-6 con la slide correspondiente de `FINC_B8420_1_simple.pdf` y dejan aquí el número de slide. Hasta entonces, este documento no se cita como transcripción del curso.
