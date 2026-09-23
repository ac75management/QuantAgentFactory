# PROJECT_STATE — QuantAgentFactory

Foto del estado vigente arriba, bitácora corta abajo. La fase de cada hipótesis la decide `python -m qaf.pipeline`, y la salud del repo `python -m qaf.preflight`. Si esta foto los contradice, mandan ellos: corrige la foto. Historial completo hasta el 2026-09-22 20:00: `docs/archive/project_state_log_2026-09-22.md`.

## CURRENT OBJECTIVE
Llevar una hipótesis de trading desde la idea hasta una estrategia validada con el método TIS (CFD/futuros, H1/H4/D1), sin conectar ningún bróker. Proyecto independiente de ZOO2.

## CURRENT STATUS (2026-09-22 20:10)
- **Hipótesis:** 7 registradas, ninguna ejecutable en cola.
  - Descartadas en IS: 001 (XAUUSD D1), 003 (SP500 D1), 004 (US30 D1) y 006 (DAX H4).
  - Rechazada por Alexander: 005 (US30 H1).
  - Bloqueadas por arquitectura: 002 (NAS100 D1, falta la familia de calendario) y 007 (XAUUSD D1 KAMA: la fuente no fija ER_Length, FastMA_Length ni la salida, y falta la familia KAMA).
  - Cero estrategias aprobadas y cero aperturas de OOS.
- **Motor `qaf` 2.0.0:** filtro IS que falla cerrado, con estas puertas: AED por rotación (p<0.05), baseline del mismo capital 1x, sensibilidad ±10/20% con 200 vecinos, fricción ≥3.0, estrés ×2 y bootstrap. Las 28 particiones IS/OOS están selladas.
- **OOS:** cerrado a propósito (`qaf/holdout.py`). Faltan los costos históricos (C4), el calendario, `price_basis`, el walk-forward real y el contrato congelado; ver `docs/VALIDATION_ROADMAP.md`.
- **Catálogo** (`catalog/candidates/`, versionado):
  - `IDEA-PILOT-KAMA-XAU-D1` se promovió a la 007.
  - `IDEA-PILOT-DONCHIAN-ER-DAX` fue rechazada.
  - `IDEA-PILOT-MABAND-EUR-H4` está `captured`, con una revisión de evidencia en cola para `investigator`.
  - `source-sync` (arXiv, Crossref y LEAN) está listo; solo se probó en dry-run.
- **Datos:** 10 símbolos `research` con H1/H4/D1, salvo EURUSD y USDJPY, que no tienen H1. `costs_verified: false` y `price_basis: unknown` en todos.
- **Coordinación:** `AGENTS.md` + reservas SQLite + preflight. El workflow de CI existe, pero el repo no tiene remoto git, así que no corre.
- **Pruebas:** suite completa verde (146).

## NEXT ACTION
Invocar `investigator` sobre la tarea en cola `catalog:IDEA-PILOT-MABAND-EUR-H4`: revisar la fuente primaria y decidir si es elegible. Es el único trabajo desbloqueado sin una decisión de Alexander.

## DECISIONS
- Independiente de ZOO2: sin cuenta, capital ni bróker compartidos. (2026-09-21)
- Alcance: CFDs y futuros, H1/H4/D1. Excluidos M15/M30, scalping, alta frecuencia y rebalanceo de cartera. (2026-09-22)
- Kaufman y Raschke son ejemplos del método, no el catálogo de ideas. (2026-09-21)
- Comprar y mantener durante años queda descartado en CFD índice/metal: el swap domina. Las hipótesis deben mantener posiciones días o pocas semanas. (2026-09-22)
- El baseline es comprar y mantener del mismo símbolo y timeframe, con los mismos costos y el mismo capital 1x. Es un costo de oportunidad absoluto: la estrategia debe ser positiva y superarlo. (2026-09-22)
- La sensibilidad es diagnóstica y su política vive en `config/runner.json`. Solo cambia antes de una campaña nueva, nunca para rescatar un resultado. (2026-09-22)
- Cambiar una regla o un parámetro después de ver resultados crea una hipótesis nueva, con otro ID. (2026-09-22)
- No se agregan agentes de optimización, sizing o deploy hasta tener walk-forward y OOS. Tampoco agentes de investigación en paralelo. (2026-09-22)
- El catálogo se versiona en `catalog/`. `source-sync` es una cosecha manual por lotes, sin promoción ni backtest automáticos. (2026-09-22)
- Toda fuente autoritativa tiene una sola copia; los espejos se generan o se verifican (`qaf.consistency`). (2026-09-22)

## OPEN QUESTIONS (decide Alexander)
1. **007:** conseguir la evidencia de Kaufman para ER_Length, FastMA_Length y la salida (`docs/research_queue.md`) y decidir si se implementa la familia KAMA. Decidir también el riesgo de la spec: 1% frente al 0.5% de la política.
2. **002:** implementar una familia de calendario o archivar la hipótesis.
3. **EURUSD/USDJPY H1:** reimportar los 3 timeframes con un corte compatible con 2010+, o dejarlos en D1/H4.
4. **Primera extracción real** de `source-sync` (`--limit 5`, hasta 15 candidatos).
5. **Remoto git** (GitHub): sin remoto, el CI no corre.
6. **Datos COT:** sin acceso, las hipótesis de Larry Williams que los requieren quedan descartadas.

## PARKED IDEAS
- Centro de control con una "oficina de agentes" visual: `docs/proposals/CONTROL_CENTER_ROADMAP.md`.
- Biblioteca normalizada de estrategias con comparación antes y después de su publicación: `docs/proposals/HARDQUANT_ADAPTATION.md`.
- VWAP NDX H1 (requiere familia nueva y el proxy `tick_volume`): `docs/proposals/vwap-ndx-h1.md`.
- Familias DVO, ConnorsRSI completo y DVI (fuentes insuficientes por ahora).
- Futuros CME como etapa de confirmación, solo cuando alguna estrategia sobreviva IS y OOS en CFD.
- Cartera de varias estrategias, "cuentas lógicas" y correlación <0.34: solo cuando haya estrategias aprobadas.
- Exportar a MQL5/PineScript, solo tras una aprobación.

## FILES / SOURCES
- Reglas: `CLAUDE.md`. Coordinación: `AGENTS.md`. Proceso: `docs/OPERATIONS.md`. Arquitectura: `docs/architecture.md`.
- Fuentes únicas: `config/instruments.json`, `config/hypotheses.json`, `config/runner.json`, `catalog/candidates/`.
- Resultados locales: `reports/factory/runs/<run_id>/result.json`.

## BITÁCORA
Cada entrada va al final, en 10 líneas o menos. Al pasar de 250 líneas, mover las entradas antiguas a `docs/archive/project_state_log_<fecha>.md`. El detalle va en el mensaje del commit, no aquí.

### 2026-09-22 20:10 — Limpieza del proyecto (Claude-app, autorizada por Alexander)
- Quitados:
  - `docs/archive/pre_factory_v2/`, unas 2.600 líneas; recuperable con el tag git `archive/pre-factory-v2`.
  - 3 scripts retirados y `scripts/costs.py`, un segundo modelo de costos que nadie usaba.
  - 3 copias de los pilotos en `docs/sources/` y el stub `reports/_data_quality/`.
  - La lectura de `state/catalog/`; la carpeta quedó en la Papelera.
- Movidos: 8 informes a `docs/archive/reviews/`, 3 propuestas a `docs/proposals/` y la bitácora antigua a `docs/archive/`.
- Reescritos porque contradecían al código: `docs/universe.md` (ahora espejo generado y verificado), `docs/cost_model.md` (sin valores propios), `docs/DATA_PIPELINE.md`, CLAUDE.md (reglas 5 y 20, estructura), la descripción del skill Gate 0 y los agentes `protocol`, `engine` e `investigator`.
- Deduplicados: el ciclo de coordinación ahora está solo en `AGENTS.md`.
- Locales (no versionados): los resultados de los scripts retirados pasaron a `reports/_legacy_pre_factory/`. Las 3 preguntas VWAP de `docs/research_queue.md` quedaron APARCADAS: nadie las investigaba.
- Código:
  - Quitados los imports muertos.
  - El catálogo ahora falla con un error visible ante un archivo ilegible, en vez de ocultarlo.
  - La anomalía de la 001 (hipótesis cerrada) cuenta como histórica, no como advertencia.
  - `pytest` ya no crea `.pytest_cache`.
  - Suite: 146 pasados / 0 fallidos.
