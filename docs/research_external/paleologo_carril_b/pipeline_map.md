# Mapa: pipeline Paleologo → registry y gates IS de QAF

**Fuente:** FINC-B8420 Lecture 1, slides 41 (pre-trade), 42 (durante) y 43 (post-trade). Carril B conceptual.
**Propósito:** ubicar lo que QAF ya cubre y declarar los huecos. **No propone construir nada ni cambia gates ni umbrales. OOS sigue cerrado.**
**Referencias vigentes:** `qaf/validation.py::screening_gates`, `config/runner.json`, `qaf/experiment_registry.py`, `data/trials_registry.jsonl`.

```
PRE-TRADE (sl. 41)             DURANTE (sl. 42)                 POST-TRADE (sl. 43)
risk model ─────────┐          signal aggregation ─┐            positions & executions
expected-return ────┼─► PC     risk constraints ───┼─► target   → realized PnL & costs
transaction-cost ───┘          hedging ────────────┤  portfolio → performance attribution
                               execution ──────────┘            → model & process updates
        │                               │                                  │
        ▼                               ▼                                  ▼
edge_filter + AED, baseline,   1 estrategia: sin agregación,     result.json + trials_registry
DD, friction ×1/×2             sin cobertura; fill simulado      (IS simulado, sin PnL real)
```

| Etapa (slide) | Equivalente en QAF hoy | Gate / artefacto | Cobertura |
|---|---|---|---|
| **Expected-return models** — "signals across assets and horizons" (41) | Una señal, un activo, con mecanismo declarado | `edge_filter.md` (fase 1) → `aed_pattern_confirmed` (p<0.05), `net_positive`, `profit_factor` >1.3, `minimum_trades` ≥30, `bootstrap_lower_bound` >0 | Buena para una señal; sin sección cruzada entre activos, a propósito |
| **Risk model** — "portfolio volatility and systematic exposures" (41) | Sin modelo factorial; controles sobre la propia serie | `equity_drawdown` ≤0.20, `risk_fraction` 0.005, `beats_baseline` (comprar y mantener 1x), `parameter_sensitivity` (≥50% vecinos positivos) | **Parcial.** No se miden exposiciones sistemáticas; `beats_baseline` es el único filtro de "¿esto es solo β?" (Cochrane, slide 34) |
| **Transaction-cost model** — "spread, impact, fees, and capacity" (41) | Contrato único de costos | `config/instruments.json`; `friction` ≥3.0; `stress_net_positive` (fricción ×2) | Spread, comisión y swap: sí. **Impacto y capacidad: no modelados** (se suponen irrelevantes a lotaje minorista ≥H1, sin verificar). Reserva: `costs_verified: false` |
| **Signal aggregation / risk constraints / hedging** (42) | No aplica: una estrategia, un instrumento | — (cartera/correlación está en PARKED IDEAS de `PROJECT_STATE.md`) | Fuera de alcance, a propósito |
| **Execution** — "sequence orders" (42) | Fill simulado, causal y documentado | Regla dura 21 (open de la barra siguiente); pruebas de no look-ahead; sin bróker (reglas 1-2) | Solo simulada |
| **Realized PnL and costs** (43) | Solo PnL **simulado** IS, descompuesto por componente | `result.json`: bruto / spread / financing-swap | IS simulado. PnL real inexistente hasta la incubación (regla 15) |
| **Performance attribution** — "which signals worked? did sizing add value? were realized costs consistent with the model?" (43) | Contabilidad de trials y de costos | `trials_registry.jsonl` (spec_hash, cost_sha, gates, métricas) + `count-trials` por hipótesis/familia | **Parcial.** Se atribuye a costos, no a factores. "¿Los costos reales coinciden con el modelo?" no tiene respuesta hasta tener fills reales |
| **Model and process updates** (43) | Actualizar el proceso sin contaminar hipótesis | Regla: cambiar la regla después de ver resultados = hipótesis nueva con otro ID; OOS nunca retroalimenta IS | Cubierto por diseño. El bucle de feedback de la slide 43 **no** se aplica a la misma hipótesis |
| **Datos** — "point-in-time, clean, aligned" (40) | Calidad de datos antes de todo | Gate 0 (`quality.status`), particiones selladas, `INVALID_POR_DATOS` | Buena. Solo existe la familia "prices & volume" (slide 40) |

**Decisión** (sin cambios): cualquier FAIL → `DISCARDED_IS`; con Gate 0 en RESERVE o reservas abiertas → `EXPLORATORY_CANDIDATE`; todo PASS → `READY_FOR_FROZEN_VALIDATION`, que **no** es validación ni abre OOS (`docs/VALIDATION_ROADMAP.md`).

**Huecos declarados, no accionados:**
1. Sin modelo de riesgo de exposiciones sistemáticas (el curso lo construye con CRSP/Compustat, que no aplican a MT5/CFD).
2. Sin atribución por factores.
3. Impacto y capacidad del modelo de costos: supuestos, no medidos.

Los tres quedan como notas. Si algún día se abordan, será después de que una estrategia pase IS, no antes.
