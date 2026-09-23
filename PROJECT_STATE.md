# PROJECT_STATE — QuantAgentFactory

Foto del estado vigente arriba, bitácora corta abajo. La fase de cada hipótesis la decide `python -m qaf.pipeline`, y la salud del repo `python -m qaf.preflight`. Si esta foto los contradice, mandan ellos: corrige la foto. Historial completo hasta el 2026-09-22 20:00: `docs/archive/project_state_log_2026-09-22.md`.

## CURRENT OBJECTIVE
Llevar una hipótesis de trading desde la idea hasta una estrategia validada con el método TIS (CFD/futuros, H1/H4/D1), sin conectar ningún bróker. Proyecto independiente de ZOO2.

## CURRENT STATUS (2026-09-23 00:30)
- **Hipótesis:** 9 registradas; la 009 ya tiene contrato ejecutable y espera registro/Gate 0.
  - Descartadas en IS: 001 (XAUUSD D1), 003 (SP500 D1), 004 (US30 D1) y 006 (DAX H4).
  - Rechazada por Alexander: 005 (US30 H1).
  - Bloqueadas por arquitectura: 002 (calendario), 007 (KAMA) y 008 (media con banda porcentual; reglas incompletas).
  - Pendiente de engine: 009 (EURUSD H1, reversión intradía con SMA(5), banda 0.1% y sesión NY); familia implementada y adaptación de riesgo congelada antes del IS.
  - Cero estrategias aprobadas y cero aperturas de OOS.
- **Motor `qaf` 2.0.0:** filtro IS que falla cerrado, con estas puertas: AED por rotación (p<0.05), baseline del mismo capital 1x, sensibilidad ±10/20% con 200 vecinos, fricción ≥3.0, estrés ×2 y bootstrap. Las 28 particiones IS/OOS están selladas.
- **OOS:** cerrado a propósito (`qaf/holdout.py`). Faltan los costos históricos (C4), el calendario, `price_basis`, el walk-forward real y el contrato congelado; ver `docs/VALIDATION_ROADMAP.md`.
- **Catálogo** (`catalog/candidates/`, versionado):
  - 18 candidatos: 3 promovidos (007, 008 y 009) y 15 rechazados tras triaje/revisión.
  - La primera extracción real agregó 15 candidatos; `source-sync` conserva el recorrido seguro y manual por lotes.
- **Datos:** el contrato habilita 10 símbolos en H1/H4/D1, pero el manifest sellado carece de EURUSD/H1 y USDJPY/H1. El lote EURUSD/H1 disponible empieza en 2010-08-18, después del corte EURUSD ya sellado (2010-02-17); `qaf.ingest` falla cerrado y no sobrescribe particiones. `costs_verified: false` y `price_basis: unknown` en todos.
- **Coordinación:** `AGENTS.md` + reservas SQLite + preflight. El workflow de CI existe, pero el repo no tiene remoto git, así que no corre.
- **Pruebas:** suite completa verde (173).

## NEXT ACTION
Resolver la incompatibilidad de corte EURUSD (reimportación controlada de todas sus temporalidades con un corte común posterior a 2010-08-18, o decisión explícita de no usar 009); después importar/sellar H1 y ejecutar Gate 0 + IS. La corrida no puede abrir OOS ni aprobar una estrategia.

## DECISIONS
- Independiente de ZOO2: sin cuenta, capital ni bróker compartidos. (2026-09-21)
- Alcance: CFDs y futuros, H1/H4/D1. Excluidos M15/M30, scalping, alta frecuencia y rebalanceo de cartera. (2026-09-22)
- Kaufman y Raschke son ejemplos del método, no el catálogo de ideas. (2026-09-21)
- Comprar y mantener durante años queda descartado en CFD índice/metal: el swap domina. Las hipótesis deben mantener posiciones días o pocas semanas. (2026-09-22)
- El baseline es comprar y mantener del mismo símbolo y timeframe, con los mismos costos y el mismo capital 1x. Es un costo de oportunidad absoluto: la estrategia debe ser positiva y superarlo. (2026-09-22)
- La sensibilidad es diagnóstica y su política vive en `config/runner.json`. Solo cambia antes de una campaña nueva, nunca para rescatar un resultado. (2026-09-22)
- Cambiar una regla o un parámetro después de ver resultados crea una hipótesis nueva, con otro ID. (2026-09-22)
- No se agregan agentes de optimización, sizing o deploy hasta tener walk-forward y OOS. Tampoco agentes de investigación en paralelo. (2026-09-22)
- **Operación continua/orquestación entre agentes: en espera.** Alexander pidió no construirla sin acuerdo previo de Claude y Codex (recordó que GPT ya lo había pedido antes). Señal de arranque acordada por las dos IA: una hipótesis completa las 5 fases y llega a `READY_FOR_FROZEN_VALIDATION`. Detalle en `docs/OPERATIONS.md`. (2026-09-22)
- **Modelos por tarea: nivel barato por defecto.** Alto (Opus/Codex razonamiento alto) solo para método, auditoría o cambios al motor/costos/puertas/datos/OOS. Tabla en `docs/OPERATIONS.md`. (2026-09-22)
- El catálogo se versiona en `catalog/`. `source-sync` es una cosecha manual por lotes, sin promoción ni backtest automáticos. (2026-09-22)
- Toda fuente autoritativa tiene una sola copia; los espejos se generan o se verifican (`qaf.consistency`). (2026-09-22)

## OPEN QUESTIONS (decide Alexander)
1. **009:** importar EURUSD/H1 y, tras el contrato de `protocol`, decidir si se implementa su familia SMA+banda+sesión.
2. **007:** conseguir la evidencia de Kaufman para ER_Length, FastMA_Length y la salida (`docs/research_queue.md`) y decidir si se implementa la familia KAMA. Decidir también el riesgo de la spec: 1% frente al 0.5% de la política.
3. **002:** implementar una familia de calendario o archivar la hipótesis.
4. **USDJPY H1:** reimportar los 3 timeframes con un corte compatible con 2010+, o dejarlo en D1/H4.
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

### 2026-09-22 20:14 — Auditoría post-limpieza y cursor `source-sync` (Codex)
- `d6d7096` conserva el lote de catálogo/source-sync; los retiros no tienen usuarios activos y el tag `archive/pre-factory-v2` existe.
- `catalog-list` y el Centro de Control pasaron con los 3 candidatos; suite completa: 146 pasados.
- `docs/cost_model.md` y `docs/DATA_PIPELINE.md` coinciden con los comandos y salidas vigentes de MT5.
- Las preguntas VWAP siguen aparcadas: Codex no las estaba investigando.
- El diseño inicial del cursor fue auditado y reemplazado por el contrato implementado de `docs/CATALOG_AUTOMATION.md`.

### 2026-09-22 20:40 — Auditoría del diseño del cursor de source-sync (Claude-app)
- Veredicto: REQUIERE CAMBIOS; el contrato corregido quedó implementado en la entrada siguiente.
- Cambios pedidos: arXiv por recorrido completo, Crossref como muestreo por relevancia, reserva global y escrituras exclusivas.
- Solo consultas reales de lectura; sin cambios de código ni commit.

### 2026-09-22 20:53 — `source-sync` seguro implementado (Codex)
- Reemplazado el cursor universal: arXiv escanea 330/330; Crossref declara muestreo; GitHub exige árbol completo.
- Reserva global con heartbeat, escrituras exclusivas y snapshots solo para acciones reales.
- Refrescos idempotentes y reconocidos en el candidato; borrar SQLite no reabre trabajo atendido.
- Cubiertos límites, concurrencia, pérdida de lease, corrupción, recuperación y `dry-run` sin estado.
- Consulta real de solo lectura: arXiv 330, Crossref 1 y LEAN 10; no se crearon candidatos.
- Suite completa: 158 pasados / 0 fallidos. Primera extracción real sigue pendiente de Alexander.

### 2026-09-22 21:08 — Robustecimiento final de `source-sync` (Codex)
- Reconciliación independiente del fetch, JSON exclusivo por enlace atómico, arXiv reciente primero y fallos aislados por proveedor.
- Suite completa: 164 pasados / 0 fallidos; sin commit.

### 2026-09-22 21:06 — Revisión de las correcciones de Codex y recomendaciones (Claude-app)
- Correcciones de Codex verificadas: reconciliación sin depender del fetch, escritura atómica exclusiva, arXiv lo reciente primero y fallos aislados por proveedor. Suite: 164/164.
- `docs/CATALOG_AUTOMATION.md`: recomendación de Crossref (solo la muestra inicial) y procedimiento de triaje barato. `AGENTS.md`: 5 recomendaciones para ahorrar tokens, incluida la de compactar. `.gitignore`: `*.tmp`.

### 2026-09-22 21:15 — Primera extracción real de source-sync (Claude-app, autorizada por Alexander)
- `source-sync --limit 5`: 15 candidatos nuevos (5 de arXiv, 5 de Crossref, 5 de LEAN). Quedan en espera 325 de arXiv y 5 de LEAN para las próximas corridas.
- arXiv falló una vez por timeout pasajero: el transporte solo reintentaba HTTP 429/503. Ahora también reintenta timeouts y errores de conexión (1 prueba). Suite: 165/165.

### 2026-09-22 21:20 — Triaje de la primera extracción (Claude-investigator, subagente Sonnet)
- De 16 en cola: 12 rechazadas por metadatos (fuera de alcance, sin dato disponible, o no es una regla de trading), 4 sobreviven `captured` para revisión completa: `IDEA-PILOT-MABAND-EUR-H4`, `IDEA-SRC-051A7EA057B3` (reversión intradía FX), `IDEA-SRC-CB192E3BD042` (reversión por IBS) e `IDEA-SRC-E1BFCE63DDA4` (reversión de gaps).
- Suite: 165/165. Sin commit ni promoción.

### 2026-09-22 21:35 — Punto objetivo con Codex: esperar antes de construir orquestación (Claude-app)
- Alexander pidió consultar con Codex antes de seguir con la política de modelos/automatización, y verificar "OmniRoot".
- Acuerdo: se espera a que una hipótesis llegue a `READY_FOR_FROZEN_VALIDATION` de punta a punta antes de construir el ciclo/interruptor.
- "OmniRoot" no existe con ese nombre según Codex (documentación oficial de OpenAI); no se inventa una definición.
- Niveles de modelo bajados: alto solo para auditoría o cambios de motor/costos/puertas/datos/OOS; investigator/protocol en nivel medio; mecánico en nivel barato.
- `docs/OPERATIONS.md` actualizado con el punto objetivo y la tabla ajustada. Sin cambios de código.
## 2026-09-22 — Protocol de hipótesis 008

- La hipótesis EURUSD H4 de media móvil con banda porcentual quedó `blocked_architecture`.
- La fuente disponible no fija periodo/tipo de media, ancho de banda, salida ni sizing, y `qaf` no implementa esa familia.
- Se creó una spec humana bloqueada y una pregunta de investigación; no se generó JSON, no hubo backtest y OOS permaneció cerrado.
- Verificación: 165 pruebas pasadas; consistencia, universo, pipeline y coordinación sin fallos. Preflight conserva solo la advertencia por cambios todavía no consolidados.

### 2026-09-22 22:00 — Revisión completa de evidencia, hipótesis 008 (Claude-investigator, subagente Sonnet)
- `IDEA-SRC-CB192E3BD042` (IBS): rechazada, es rebalanceo de cartera multi-activo, no una regla de un instrumento.
- `IDEA-SRC-E1BFCE63DDA4` (gaps): rechazada, resolución de minutos y cartera dinámica — doble fuera de alcance.
- `IDEA-SRC-051A7EA057B3` (reversión intradía FX): evidencia buena y dentro de alcance (paper real verificado), pero quedó `needs_data`/bloqueada por un bug de `qaf/catalog.py` — ver "Hallazgos cruzados" en AGENTS.md.
- `IDEA-PILOT-MABAND-EUR-H4`: promovida. **Hipótesis 008** (`eurusd-h4-media-m-vil-con-banda-porcentual`), `blocked_architecture` — falta familia de señal (precio vs una MA ± banda %) en `qaf/signals.py`, y los valores numéricos exactos quedan como ambigüedad declarada.
- Suite: 165/165. Sin commit.

### 2026-09-22 23:55 — Catálogo reparado e hipótesis 009 promovida (Codex)
- La revisión `needs_data` ahora puede corregirse sin borrar evidencia: la versión anterior queda en `review_history`.
- El objetivo declarado se persiste y `research_lane` se recalcula; las revisiones finales continúan inmutables.
- `IDEA-SRC-051A7EA057B3` quedó `promoted` como 009, EURUSD/H1, pendiente de `protocol`.
- El manifest sellado aún no contiene EURUSD/H1; debe importarse antes de `engine`. OOS sigue cerrado.
- Verificación: 167 pruebas, preflight/pipeline/consistencia sin fallos. Sin commit.

### 2026-09-23 00:10 — Protocol de hipótesis 009 (Codex)
- La regla LEAN quedó congelada: SMA(5), banda 0.1%, cambio de dirección y sesión 10:00–15:00 NY con salida 15:01.
- No se generó JSON: `qaf` no tiene una familia precio/SMA+banda+sesión y no se forzó dentro de `trend_cross`.
- 009 pasó a `blocked_architecture`; la especificación bloqueada y la pregunta de diseño quedaron documentadas.
- OOS no se abrió y no se ejecutó engine.

### 2026-09-23 00:30 — Familia `sma_band_session` y contrato 009 (Codex, autorizado por Alexander)
- Implementados contrato, señales causales con IANA/DST y salida temporal en el motor; 5 pruebas nuevas cubren expiración y no-look-ahead.
- La adaptación previa al IS congela ATR14, SL 1.5×, TP 3×, riesgo 0.5% y max_holding 6; no se eligió mirando resultados.
- 009 salió de `blocked_architecture`; JSON y narrativa están listos para `engine`.
- Suite de regresión: 172 pruebas pasadas. OOS continúa cerrado.

### 2026-09-23 00:45 — Auditoría de datos EURUSD/H1 (Codex)
- El lote raw existe, pero comienza 2010-08-18 y no alcanza el corte EURUSD ya sellado de 2010-02-17.
- `qaf.ingest` devolvió `INSUFFICIENT_BEFORE_FIXED_CUTOFF` y preservó intactas las particiones existentes.
- No se abrió OOS ni se ejecutó backtest; la reimportación de D1/H4/H1 requiere una decisión explícita por su efecto sobre sellos históricos.

### 2026-09-23 00:55 — Auditoría de sensibilidad (Codex)
- La nueva familia añade horarios y zona IANA, que no son parámetros numéricos libres.
- `qaf.validation.parameter_sensitivity` ahora perturba solo campos numéricos y reporta los estructurales sin modificarlos.
- Suite completa: 173 pruebas pasadas; consistencia y pipeline sin violaciones.
