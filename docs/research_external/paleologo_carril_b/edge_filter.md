# Filtro de edge (Carril B — Paleologo)

**Fuente:** G. Paleologo, FINC-B8420 (Columbia), Lecture 1 "Quant Business Models and Roles" (`FINC_B8420_1_simple.pdf`, 43 slides). Libro: *The Elements of Quantitative Investing* (Wiley, 2025). Auditado por Grok.
**Carril:** B conceptual. No se mezcla con el triaje `method_only` Paleologo anterior.
**Alcance:** solo candidatos nuevos (012+). No se aplica retroactivamente a 001-011, no reabre ni rescata ninguno.
**Cotejo:** etiquetas verificadas contra el PDF de la Lecture 1 (se cita la slide en cada punto).

---

## 1. Investing vs trading (slides 21-27, 30-33)

Paleologo describe el alfa como mezcla de **tres mecanismos idealizados**: información ("investing"), estructura ("trading") y riesgo ("risk premia") (slide 21). **El horizonte no es lo que los distingue:** el investing puede darse a horizontes muy largos y muy cortos (slide 24), y hay trades estructurales con cadencia mensual o trimestral (slide 29).

| | Investing (información) | Trading (estructura) | Risk premia (riesgo) |
|---|---|---|---|
| De dónde sale el P&L | Información diferencial frente al consenso que reflejan los precios (slides 22-24) | Estructura de mercado y preferencias heterogéneas de los participantes; la demanda es pública (slides 26-28) | Compensación por perder en estados malos: Cov(m, R) < 0 (slide 31) |
| Papel del costo de operar | Es costo, no fuente de ganancia: se minimiza al expresar la información (slide 24) | **Es la fuente de ganancia** (slide 27) | Exposición sistemática (β·λ), cobrada por mantenerla (slide 32) |
| Requisitos | Tesis diferenciada + horizonte (slide 24) | Ejecución, acceso a mercado, financiación y regulación son esenciales (slide 27) | Mantener la exposición; la diversificación no elimina el riesgo de factor (slide 32) |

**Advertencias de la fuente que el filtro adopta:**
- Llamar "prima de riesgo" a un retorno persistente no establece qué mecanismo lo produce: puede ser compensación por riesgo, comportamiento o restricciones institucionales (slide 33).
- "No hay alfa. Hay beta que entiendes y beta que no entiendes" (Cochrane, citado en slide 34).
- Poder predecir no garantiza ganar: el paso de pronóstico a posición puede fallar por riesgo, liquidez o financiación (slides 35-36).

**Lectura para QAF** (interpretación de Claude, no del curso): QAF opera **un solo CFD, como price taker minorista, en H1/H4/D1**. Paga spread y swap; no los cobra. No tiene acceso privilegiado, financiación barata ni capacidad de operar varias patas. Por eso la mayoría de los edges de **trading** de la slide 27 le quedan estructuralmente fuera: los que dependen de ejecución, acceso o financiación. Toda hipótesis QAF tiene que declarar en qué vértice del triángulo cae.

---

## 2. Checklist: los 6 mecanismos (slide 39, literal)

La slide 39 ("Six mechanisms explain why excess returns can persist") los nombra así. La columna "Vértice" agrupa cada uno en el triángulo de la slide 21; esa agrupación es inferencia de Claude, apoyada en las slides 27 y 29.

| # | Mecanismo (slide 39) | Vértice | ¿Compatible con QAF (1 CFD, OHLC MT5, ≥H1, price taker)? |
|---|---|---|---|
| 1 | **Pure arbitrage** — price inconsistency | Estructura | **No.** Necesita varias patas simultáneas (ley de un precio, slides 27a y 37). `OUT_OF_SCOPE` |
| 2 | **Risk preferences** — bearing uncertainty | Riesgo | Con reservas. Debe superar `beats_baseline` (si no, es beta). En CFD el swap castiga las tenencias largas (decisión de 2026-09-22 en `PROJECT_STATE.md`) |
| 3 | **Liquidity** — providing immediacy | Estructura | **Condicional.** El market making intradía queda fuera. La provisión de liquidez a horizonte de evento es admisible si el desequilibrio es observable en OHLC ≥H1 (slide 19: "from sub-second market making to multi-week event strategies") |
| 4 | **Funding** — capital scarcity | Estructura | **No.** QAF paga la financiación (swap), no la cobra; no hay trades de base ni conversión. `OUT_OF_SCOPE` |
| 5 | **Predictable flow** — institutional demand | Estructura | Sí, si el flujo tiene calendario o regla pública verificable (slides 16 y 38) y el calendario del símbolo está documentado |
| 6 | **Information** — better forecasts | Información | Con reservas. Con OHLC público la información diferencial es la más difícil de sostener (slide 34: suele ser un "epifenómeno" de las restricciones). Carga de prueba máxima en AED |

**Preguntas obligatorias** (van en la ficha `docs/hypotheses/<slug>.md`, sección "Mecanismo de edge"):

- [ ] Vértice (información / estructura / riesgo) y **un** mecanismo primario de la slide 39.
- [ ] **¿Quién está al otro lado del trade?** (slide 34) ¿Qué restricción (de liquidez, financiación, flujo o riesgo) le obliga a seguir ahí? (slides 34 y 36: "a constraint borne by one investor may be the edge earned by another").
- [ ] ¿Por qué QAF, como price taker minorista, puede cobrar este edge después de spread y swap? (slides 35-36; se falsa con `friction` y `stress_net_positive`).
- [ ] ¿Qué puerta IS existente lo falsaría primero? (ver `pipeline_map.md`).
- [ ] Si el mecanismo es 2: ¿por qué no es solo β al activo? (debe superar `beats_baseline`).

---

## 3. Uso como filtro dentro de QAF

1. **Dónde:** FASE 1 de `docs/CHECKLIST_HIPOTESIS.md`, durante la revisión de evidencia de `investigator`, antes de `protocol`. No es una puerta del motor y no cambia `qaf/validation.py`, `config/runner.json` ni ningún umbral.
2. **Qué rechaza (antes de gastar un trial IS):**
   - No se puede nombrar un mecanismo de la slide 39 ni quién está al otro lado → `rejected`, motivo "sin mecanismo de edge".
   - Mecanismo 1 o 4 → `rejected` / `OUT_OF_SCOPE`.
   - Mecanismo 3 con market making intradía → `OUT_OF_SCOPE`.
   - Explicación circular ("funciona porque el backtest gana") o varios mecanismos "primarios" → se devuelve a `investigator`.
3. **Qué NO hace:**
   - No aprueba nada: pasar el filtro solo da derecho a entrar a protocol, y las puertas IS siguen decidiendo.
   - No inventa edges: clasifica el mecanismo que **la fuente primaria ya declara**. Si la fuente no lo explica, el filtro no lo rellena.
   - No reinterpreta resultados: un `DISCARDED_IS` no se rescata cambiando de mecanismo. Cambiar de mecanismo sobre la misma regla es una hipótesis nueva con otro ID, y cuenta como trial en el registry.
   - No abre OOS.
4. **Coste:** un párrafo por hipótesis. Su valor está en gastar menos trials de `campaign_max_trials` en ideas sin mecanismo, lo que reduce el problema de múltiples pruebas que ya cuenta `count-trials`.
