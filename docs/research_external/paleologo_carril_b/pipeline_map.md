# Mapa: pipeline Paleologo → registry y gates IS de QAF

**Fuente:** FINC-B8420 Lecture 1 (pipeline riesgo / retorno esperado / costos de transacción → construcción de cartera → atribución). Carril B conceptual.
**Propósito:** ubicar lo que QAF ya cubre y declarar los huecos. **No propone construir nada ni cambia gates ni umbrales. OOS sigue cerrado.**
**Referencias vigentes:** `qaf/validation.py::screening_gates`, `config/runner.json`, `qaf/experiment_registry.py`, `data/trials_registry.jsonl`.

```
PRE-TRADE                          DURANTE                       POST-TRADE
retorno esperado ─┐                                              
modelo de riesgo ─┼─► construcción de cartera ─► ejecución ─►   atribución
costos (TC) ──────┘                                              
      │                        │                    │                 │
      ▼                        ▼                    ▼                 ▼
edge_filter + AED        (N/A: 1 estrategia)   fill modelado      result.json +
baseline, DD, costos     PARKED                (next-bar open)    trials_registry
```

| Etapa Paleologo | Equivalente en QAF hoy | Gate / artefacto | Cobertura |
|---|---|---|---|
| **Pre-trade: retorno esperado** | Hipótesis con mecanismo declarado y patrón confirmado sobre la señal cruda | `edge_filter.md` (fase 1) → `aed_pattern_confirmed` (p<0.05), `net_positive`, `profit_factor` >1.3, `minimum_trades` ≥30, `bootstrap_lower_bound` >0 | Buena |
| **Pre-trade: modelo de riesgo** | No existe modelo factorial. Lo sustituyen controles de riesgo de una sola serie | `equity_drawdown` ≤0.20, `risk_fraction` 0.005, `beats_baseline` (comprar y mantener 1x como único control de beta), `parameter_sensitivity` (≥50% vecinos positivos) | **Parcial.** Hueco: no se mide exposición a factores; `beats_baseline` es el único filtro de "¿esto es solo beta?" |
| **Pre-trade: costos de transacción** | Contrato único de costos | `config/instruments.json`; gates `friction` ≥3.0 y `stress_net_positive` (fricción ×2) | Buena en diseño. Reserva: `costs_verified: false`, `price_basis: unknown` |
| **Durante: construcción de cartera** | No aplica: una estrategia y un instrumento | — (cartera/correlación está en PARKED IDEAS de `PROJECT_STATE.md`) | Fuera de alcance, a propósito |
| **Durante: ejecución** | Fill simulado, causal y documentado | Regla dura 21 (open de la barra siguiente); pruebas de no look-ahead; sin bróker (reglas 1-2) | Simulada solamente |
| **Post-trade: atribución** | Descomposición de costos por run y contabilidad de trials | `result.json` (bruto vs spread vs financing/swap, p. ej. 002: financing domina) y `trials_registry.jsonl` (spec_hash, cost_sha, gates, métricas); `count-trials` por hipótesis/familia | **Parcial.** Hueco: la atribución es de **costos**, no de **factores/riesgo** |
| **Integridad transversal** | Calidad de datos antes de todo | Gate 0 (`quality.status`), particiones selladas, `INVALID_POR_DATOS` | Buena |

**Decisión** (sin cambios): cualquier FAIL → `DISCARDED_IS`; con Gate 0 en RESERVE o reservas abiertas → `EXPLORATORY_CANDIDATE`; todo PASS → `READY_FOR_FROZEN_VALIDATION`, que **no** es validación ni abre OOS (`docs/VALIDATION_ROADMAP.md`).

**Huecos declarados, no accionados:**
1. No hay atribución de riesgo/factores (el curso la asume con datos CRSP/Compustat, que no aplican a MT5/CFD).
2. No hay modelo de riesgo más allá de DD y baseline.

Ambos quedan como notas. Si algún día se abordan, será después de que una estrategia pase IS, no antes.
