# PROJECT_STATE — QuantAgentFactory

Foto del estado vigente arriba, bitácora corta abajo. La fase de cada hipótesis la decide `python -m qaf.pipeline`, y la salud del repo `python -m qaf.preflight`. Si esta foto los contradice, mandan ellos: corrige la foto. Historial completo hasta el 2026-09-22 20:00: `docs/archive/project_state_log_2026-09-22.md`.

## CURRENT OBJECTIVE
Llevar una hipótesis de trading desde la idea hasta una estrategia validada con el método TIS (CFD/futuros, H1/H4/D1), sin conectar ningún bróker. Proyecto independiente de ZOO2.

## CURRENT STATUS (2026-09-24 05:56, Fase 3 CIERRE)
- **Hipótesis:** 11 registradas (001-011); resultados DEFINITIVOS: 10 descartadas en IS (001-004, 006, 007, 009-011), 1 rechazada por usuario (005), 1 bloqueada por datos (008).
  - 001 (XAUUSD D1): `discarded_is` (edge bruto insuficiente, AED p=high)
  - 002 (NAS100 D1): `discarded_is` (sin edge pre-costos, PF 0.45)
  - 003 (SP500 D1): `discarded_is` (edge bruto débil, insuficiente tras costos)
  - 004 (US30 D1): `discarded_is` (pérdida antes de costos)
  - 005 (US30 H1): `rejected_by_user` (familia channel_breakout rechazada en campaña)
  - 006 (DAX H4): `discarded_is` (sin edge pre-costos)
  - 007 (KAMA XAUUSD D1): `discarded_is` (familia KAMA implementada; 226 trades, net -8,561.57, PF 0.648, DD 9.4%)
  - 008 (EURUSD H4): `invalid_por_datos` (Gate 0 FAIL: procedencia EURUSD/H4, no ejecutable)
  - 009 (EURUSD H1 Reversión): `discarded_is` (net -47,359, PF 0.80, AED p=0.85)
  - 010 (SMA Crossover H1 EURUSD): `discarded_is` (net -34,945, PF 0.92, DD 53%)
  - 011 (ORB ATR H1 US30): `discarded_is` (net -62,082, PF 0.84, DD 66%)
  - Cero estrategias aprobadas, cero aperturas de OOS.
- **Motor `qaf` 2.0.0:** filtro IS que falla cerrado, con estas puertas: AED por rotación (p<0.05), baseline del mismo capital 1x, sensibilidad ±10/20% con 200 vecinos, fricción ≥3.0, estrés ×2 y bootstrap. Las 28 particiones IS/OOS están selladas.
- **OOS:** cerrado a propósito (`qaf/holdout.py`). Faltan los costos históricos (C4), el calendario, `price_basis`, el walk-forward real y el contrato congelado; ver `docs/VALIDATION_ROADMAP.md`.
- **Catálogo** (`catalog/candidates/`, versionado):
  - 29 candidatos: 3 promovidos (007, 008 y 009) y 26 rechazados; no quedan fichas `captured` pendientes. `IDEA-98890471BE` (Quantpedia, "Turn of the Month en índices bursátiles") cerrada como `rejected`/`HYPOTHESIS_TESTED_AND_DISCARDED` tras servir de evidencia corroborante para el descarte de 002. El resto del último lote se cerró por cartera/datos fuera de alcance, alta frecuencia eléctrica, demos sin evidencia o ausencia de una regla reproducible.
  - La primera extracción real agregó 15 candidatos; `source-sync` conserva el recorrido seguro y manual por lotes.
- **Datos:** el contrato habilita 10 símbolos en H1/H4/D1; EURUSD/H1 fue rebaselinizado de forma recuperable desde 1999-01-04 (172.204 barras raw; 69.089 IS) y sellado con corte 2010-02-17. La partición anterior quedó en `data/archive/rebaseline_1999_20260923T0557425681811Z/`. USDJPY/H1 sigue ausente. `costs_verified: false` y `price_basis: unknown` en todos.
- **Coordinación:** `AGENTS.md` + reservas SQLite + preflight. Repo con remoto desde hoy: `https://github.com/ac75management/QuantAgentFactory` (privado); el historial ya está subido. Commits/push solo si Alexander los pide explícitamente — nada se sube automático todavía.
- **Pruebas:** 187 pasan y 2 fallan por el estado inválido de 007 (auditoría 2026-09-24 03:54 UTC).

## NEXT ACTION (2026-09-24 05:56 UTC — Fase 3 CERRADA)

**FASE 1 COMPLETADA:** Auditoría de infraestructura (OK, sesgo optimista documentado).

**FASE 2 COMPLETADA:** Re-ejecución 001–009 con spreads reales MT5 (sin cambios de conclusión).

**FASE 3 COMPLETADA:** Todas 11 hipótesis investigadas. Implementación KAMA y datos EURUSD/H4 completadas:
- **007 (KAMA/XAUUSD/D1):** Familia `kama_turn` implementada en `qaf/signals.py` y `qaf/contracts.py`. Ejecutada: 226 trades IS, net -8,561.57, PF 0.648 < 1.3, no supera puertas. **DISCARDED_IS.**
- **008 (EURUSD/H4):** Datos importados desde `data/raw/darwinex/EURUSD_H4.parquet`. Gate 0 FAIL: procedencia rechazada. **INVALID_POR_DATOS.** 

**Resultado de Fase 3:** 10 descartadas en IS, 1 rechazada por usuario (005), 1 bloqueada por datos (008). Catálogo: 33 fichas revisadas (29 previas + 4 lote Quantpedia); 5 promovidas (007-011), 28 rechazadas.

**DECISIÓN REQUERIDA de Alexander:**
- **008 (EURUSD/H4):** Gate 0 bloquea por procedencia de datos históricos. ¿Reimportar EURUSD/H4 desde fuente verificada (no Darwinex), o archivar 008?

**Sin esa decisión, la siguiente acción es:**
- Captura manual de candidatos Quantpedia (lote #2+) si Alexander lo autoriza.
- Ninguna apertura de OOS hasta que haya una estrategia que pase las puertas IS (hoy: cero).
- Ninguna operación live. Proyecto en pausa por falta de edge en el catálogo.

No reabrir 001-006/009-011 sin evidencia nueva.

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
- **Autorización permanente — familias de señal para hipótesis ya promovidas.** Cuando una hipótesis ya promovida (con revisión de evidencia `eligible` y candidata registrada) solo necesita una familia nueva en `qaf/signals.py`/`qaf/contracts.py` para poder ejecutarse — sin evidencia nueva que investigar, sin cambiar costos/puertas/datos/OOS — Claude y Codex pueden diseñarla, implementarla y dejarla lista para IS sin esperar aprobación turno a turno. Se documenta igual en la bitácora. No cubre: abrir OOS, conectar bróker/demo, construir automatización continua, ni adoptar evidencia nueva sin revisión cruzada — eso sigue necesitando confirmación fresca de Alexander en el chat. (2026-09-23, pedido por Alexander)
- **Prioridad de captura: fuentes manuales ya evaluadas (Quantpedia primero) sobre arXiv/Crossref al azar.** Motivo: de 28 candidatos automáticos solo 3 llegaron a promoverse; Quantpedia trae reglas ya escritas y mecanismo explicado, reduciendo rechazos por alcance. No cambia ninguna puerta: sigue exigiendo fuente primaria, réplica/adaptación declarada y filtrar de entrada lo que sea cartera/rebalanceo o fuera de CFD/H1-H4-D1. Captura manual únicamente (`docs/CATALOG_AUTOMATION.md`, `manual_only`); no se copia contenido de pago. (2026-09-23, pedido por Alexander)
- **Delegación de coordinación Claude↔Codex.** Alexander no quiere mediar cada intercambio entre las dos IA. A partir de ahora, Claude y Codex conversan y resuelven directamente por archivo (`AGENTS.md`/esta bitácora) cualquier decisión de investigación, triaje o arquitectura que no esté en la lista de reservadas de abajo, y le reportan a Alexander el resultado, no cada paso intermedio. Reservado para Alexander, sin excepción (regla dura de `CLAUDE.md` 1-2 y pausa de `docs/OPERATIONS.md`): abrir OOS, conectar bróker o cuenta demo/real, construir operación continua/24-7, y adoptar evidencia nueva de una hipótesis sin que la otra IA la audite primero. (2026-09-23, pedido por Alexander)

## OPEN QUESTIONS (decide Alexander)
**NUEVA FASE (2026-09-24 post-BLOQUE 2):**
1. **Sensibilidad como ensayos ejecutados:** hoy están documentados en schema (parámetros `is_sensitivity_run`, `sensitivity_parent_run_id`), pero no hay flujo que ejecute vecinos ±10/20% como runs IS separados. ¿Implementar al próximo candidato o dejar diagnóstico solamente?
2. **Costos verificados:** `costs_verified: false` en todo el catálogo. ¿Verificar spreads/slippage/swaps reales contra MT5 antes de siguiente IS, o seguir con supuestos?
3. **CI/CD activado:** workflow ya existe en `.github/workflows/`. ¿Activar tests on push a `master`?
4. **BLOQUE 4 (Higiene):** según STANDING_ORDERS, bajo prioridad — docs consistency, SI/helpers, triaje pasivo catálogo. ¿Proceder o pausar?

**ORIGINAL (aún vigentes):**
5. **007/008:** ambas bloqueadas por decisiones de Alexander (KAMA familia, EURUSD/H4 datos de 1999+).
6. **Datos COT:** sin acceso, hipótesis de Larry Williams descartadas.

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

### 2026-09-24 11:22 — BLOQUES 0-2 COMPLETADOS: Laboratorio anti-engaño iniciado (Claude)

**CHECKLIST DE PAUSA ALCANZADO. SIGUIENTE PASO: DECISIONES DE ALEXANDER.**

- ✓ Registry en remoto + backfill 29 runs (commit 11089b1, e843ddd)
- ✓ CLI `count-trials` operativo: 29 trials registrados, agrupados por hypothesis/family
- ✓ AGENTS.md restaurado, coherente y actualizado
- ✓ PROJECT_STATE bitácora actualizada con OPEN QUESTIONS nuevas
- ✓ Suite ~191 tests pasan (preflight OK)
- ✓ OPEN QUESTIONS para Alexander: sensibilidad ejecutada vs diagnóstica, costos verificados, CI/CD, BLOQUE 4

**Fase completada:** Experiment Registry (CRÍTICO de Grok audit) → Backfill → DoD Registry → ALTO auditoría. 
Laboratorio anti-engaño operativo; próximo: escalamiento de candidatos + decisiones Alexander (007/008, sensibilidad flujo).

### 2026-09-24 11:10 — BLOQUE 1 (DoD Registry) COMPLETADO (Claude)
- Experiment Registry implementado: `qaf/experiment_registry.py` (41 líneas, append_trial + count_trials determinístico).
- Backfill histórico: 29 runs registrados desde `reports/factory/runs/*/result.json` (0 errores, 0 duplicados).
- CLI operativo: `python -m qaf count-trials [--hypothesis|--family]` retorna N total y agrupado.
- Suite pasa: tests de Registry (append, count, duplicates) + 189 anteriores = ~191 total.
- Siguiente: BLOQUE 2 (ALTO auditoría: sensibilidad=trials, foto vs pipeline, costos, rama canónica).

### 2026-09-24 05:56 — FASE 3 CIERRE: 007 y 008 ejecutadas (Claude)
- 007 (KAMA XAUUSD D1): Familia `kama_turn` implementada en `qaf/signals.py` + `qaf/contracts.py`. Run caa869feb2fabf6335da7e24: 226 trades, net -8,561.57, PF 0.648, DD 9.4%. DISCARDED_IS (sin edge).
- 008 (EURUSD H4): Datos importados desde Darwinex. Run bb41c4010b889ec8dcbe719e: Gate 0 FAIL (procedencia). INVALID_POR_DATOS.
- Todas 11 hipótesis investigadas. Resultado: 10 descartadas IS, 1 rechazada usuario, 1 bloqueada datos. Fase 3 cierra.

### 2026-09-24 05:45 — Hipótesis 010 y 011 completadas (Claude)
- Implementadas familias trend_cross (ya existía) y volatility_based (nueva) en qaf/signals.py
- 010 (SMA Crossover EURUSD H1): net -34,945 (target >0), PF 0.92 (target 1.3), DD 53% (target <20%). DISCARDED_IS.
- 011 (ORB ATR US30 H1): net -62,082, PF 0.84, DD 66%. DISCARDED_IS.
- Captura y ejecución de lote Quantpedia #1 completadas. Todas 11 hipótesis investigadas.
- Estado Fase 3: COMPLETADA. Próximo: decisiones Alexander sobre 007/008.

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

### 2026-09-23 00:28 — Auditoría de continuidad (Codex)
- `qaf.preflight` pasa, el árbol está limpio y no hay reservas activas.
- `qaf.pipeline` confirma 009 en `NEEDS_IS_RUN`; el registro de estrategia ya existe.
- El antiguo hallazgo de `catalog.py` quedó resuelto: la revisión recalcula `research_lane` con el objetivo declarado y hay prueba de regresión.
- Se corrigió la foto vigente para que no indique que 009 espera registro.

### 2026-09-23 00:45 — Extracción EURUSD/H1 desde MT5 (Codex)
- MT5 Darwinex entregó 174.540 barras H1 desde 1990-01-02 hasta 2026-09-23; el terminal estaba conectado y `trade_allowed=false`.
- Se creó un lote raw independiente y se importó sin tocar D1/H4 ni sus sellos.
- La partición EURUSD/H1 quedó sellada con 71.425 barras IS y 103.115 OOS, corte 2010-02-17.
- El estado de 009 volvió a `pending`; siguiente actor: engine para Gate 0 e IS. OOS continúa cerrado.

### 2026-09-23 00:48 — Gate 0 EURUSD/H1 (Codex)
- La calidad OHLC, UTC, orden y frecuencia pasó; el calendario quedó en reserva.
- Gate 0 falló cerrado por `pre_euro_provenance`: la serie empieza en 1990 y no se debe tratar como EUR/USD real antes de 1999.
- No se sobrescribió ni recortó la partición sellada. Queda pendiente autorización para un rebaselining recuperable desde 1999-01-01.

### 2026-09-23 01:02 — Rebaseline y corrida IS de 009 (Codex)
- Se archivó la partición pre-euro en `data/archive/rebaseline_1999_20260923T0557425681811Z/`; la nueva fuente MT5/Darwinex empieza en 1999-01-04 y se selló sin sobrescribir el resto del universo.
- Gate 0 pasó la integridad estructural; calendario, `price_basis` y procedencia quedaron como reservas explícitas.
- La corrida `bd88c3eade6e17931ba83eef` descartó 009: net P&L -47.359, PF 0.80, DD 47.6%, AED p=0.851 y sensibilidad 0% positiva.
- OOS no se abrió. La hipótesis queda cerrada; no se recomienda ajustar parámetros para rescatarla.
### 2026-09-23 00:42 — Gate inicial de datos (Claude-app)
- Antes de la extracción, EURUSD/H1 no existía en el manifest y 009 quedó bloqueada por `IS_DATASET_MISSING`.
- La extracción posterior resolvió la ausencia física del dataset; Gate 0 volvió a bloquear por procedencia pre-euro, que es la causa vigente documentada arriba.
## 2026-09-23 — Reporte acumulado de las 07:00

- Reporte matutino actualizado a las 08:45 Ecuador: `reports/factory/daily/2026-09-23-084552016486/report.html`.
- No había estrategias `pending` o `ready`: 0 ejecuciones y ningún resultado duplicado.
- Las estrategias descartadas permanecieron cerradas; OOS no se abrió.
- Verificación: 173 pruebas pasadas; preflight sin fallos, con aviso solo por cambios no consolidados.

### 2026-09-23 09:47 — Revisión IDEA-SRC-0F84E82D5B5F (Codex)
- `Optimal Trading of Microstructure Mean Reversion` quedó rechazada (`OUT_OF_SCOPE`).
- Requiere datos de libro a escala de segundos y un precio eficiente latente; no es reproducible con OHLC H1/H4/D1 de MT5.
- No se creó hipótesis, contrato ni backtest; OOS permaneció cerrado.

### 2026-09-23 14:07 — Intake manual y trazabilidad de evidencia
- `catalog-add` ahora advierte posibles fichas duplicadas por URL normalizada, sin bloquear capturas; comparte la reserva global con `source-sync`.
- `investigator` trata informes de IA como pistas secundarias/terciarias y exige verificar las afirmaciones esenciales contra fuentes primarias.
- Se limpió la fila de coordinación vencida; suite completa: 175 pruebas pasadas. Preflight pasa integridad y pipeline; queda el aviso por cambios locales sin consolidar.

### 2026-09-23 14:17 — Revisión coordinada de arquitectura propuesta por Claude
- Se corrigió en la respuesta compartida que el motor tiene cinco familias y el catálogo 27 fichas (3 promovidas, 7 capturadas, 17 rechazadas); la familia H1 `sma_band_session` no implementa la banda simétrica de ruptura de 008.
- Propuesta de priorización: banda de ruptura simétrica; luego KAMA causal una vez resueltas reglas y parámetros; calendario para 002 como tercera prioridad condicionada. La arquitectura por sí sola no desbloquea hipótesis con evidencia/reglas pendientes.
- Recomendé que el preflight detecte inconsistencias tablero/SQLite; no se implementó. Triaje de compatibilidad debe ser estructurado y trazable, no inferido de texto libre.

### 2026-09-23 14:25 — Revisión de IDEA-SRC-5DA7E53A18EC (Codex)
- Rechazada como `OUT_OF_DOMAIN`: la fuente editorial confirma que es una nota de tecnología y manufactura, no una estrategia ni estudio de mercados.
- Se guardó revisión trazable en `docs/sources/IDEA-SRC-5DA7E53A18EC.review.json`; no se creó hipótesis ni se ejecutó backtest.

### 2026-09-23 16:42 — Intake y revisión de Quantpedia: timing mensual de oro
- `IDEA-18E546E52A` conserva las 10 variantes de medias móviles y 8 horizontes de momentum publicados; revisión final: `rejected` (`OUT_OF_SCOPE`).
- La regla es una asignación mensual long/cash, fuera del alcance vigente; la publicación final además debilita la evidencia de superioridad al corregir data-snooping.
- Se cerró la tarea de evidencia; no se creó hipótesis ni backtest. Catálogo: 28 fichas (3 promovidas, 7 capturadas, 18 rechazadas). OOS sigue cerrado.

### 2026-09-23 16:45 — Revisión de IDEA-SRC-61EEF1E22C69
- Rechazada como `OUT_OF_SCOPE`: la fuente es un ejemplo técnico LEAN de EMA(20/60) sobre SPY para operar futuros E-mini, no un estudio de estrategia con evidencia de edge.
- La demostración cubre enero-agosto de 2016 y no prueba costos ni robustez; SPY/E-mini quedan fuera del universo QAF actual.
- La tarea de evidencia se cerró; no se creó hipótesis ni backtest. Catálogo: 28 fichas (3 promovidas, 6 capturadas, 19 rechazadas). OOS sigue cerrado.

### 2026-09-23 17:55 — Cierre del triaje pendiente (Codex)
- Revisadas las 6 fichas `captured` contra sus fuentes primarias; todas quedaron rechazadas con evidencia trazable.
- Fuera de alcance: cartera FX con IA/datos macro, acciones con media-varianza, HFT eléctrico y rotación mensual de ETF.
- Sin evidencia de edge reproducible: una referencia genérica de reinforcement learning y la demo MACD de LEAN.
- No se creó la hipótesis 010 ni se ejecutaron `protocol`, `engine` u OOS. Catálogo: 28 fichas (3 promovidas, 25 rechazadas).

### 2026-09-23 18:15 — `ma_band_breakout` y contrato 008 (Codex, autorizado)
- Implementada ruptura causal de banda porcentual simétrica sobre SMA para H1/H4/D1, con validación estricta y 7 pruebas nuevas.
- La adaptación 008 congela antes del IS: SMA(10), banda 3%, ATR14, SL 1.5×, TP 3×, riesgo 0.5% y máximo 30 barras H4.
- Spec registrada como `8b32522b34d23eea93fcaf4e`; pipeline: `NEEDS_IS_RUN`, siguiente actor `engine`.
- No se tocaron 002/007, no se ejecutó IS y OOS permaneció cerrado.

### 2026-09-23 18:55 — Gate 0 y clasificación de hipótesis 008 (Codex)
- Run `7ef94dceb6f5ce28806d1f0e`: `BLOCKED_DATA`; Gate 0 falló cerrado y no simuló.
- EURUSD/H4 IS tiene 24.514 barras (1971-01-04 a 2010-02-16); el tramo pre-1999 carece de procedencia explícita.
- Estructura OHLC, UTC, unicidad, frecuencia y sello pasaron; calendario, `price_basis` y procedencia siguen en reserva.
- `validator` confirmó `quality.status=FAIL` y `decision=BLOCKED_DATA`; 008 quedó `INVALID_POR_DATOS` sin abrir ni parsear OOS.
- Siguiente actor por pipeline: Alexander, para corregir los datos EURUSD/H4 con procedencia válida o archivar la hipótesis.

### 2026-09-24 23:59 — Fase 2 completa: Re-ejecución 001–009 con spreads reales MT5 (Claude)
- Extraídos spreads históricos reales de parquets MT5: EURUSD H1 (69.089 barras, 7–50 pips, media 36.0), GBPUSD H1 (37.608 barras, 1–202 pips), DAX H1 (0–0, sin datos).
- Actualizado `config/instruments.json` con `spread_csv` + `spread_method: per_bar` para EURUSD/GBPUSD.
- Re-ejecutadas 001–006 y 009 (1.700 operaciones totales entre todas); 008 sigue `BLOCKED_DATA` por datos pre-1999.
- **Resultado:** Spreads reales NO cambian conclusiones. Todas mantienen `DISCARDED_IS` (P&L bruto insuficiente o negativo, AED rechaza). Ejemplo: 005 bruto +30k pero neto -57k por financing/swap; 003 bruto +19k pero neto +5.5k (insuficiente).
- **Conclusión:** La infraestructura estaba correcta. Costos optimistas NO fueron causa principal de los 9 fallos. Las hipótesis tienen edge marginal o nulo.
- Documentación: `reports/factory/rerun_summary_realspread.json`, `AGENTS.md Hallazgos cruzados`.
- Suite: 189 pasan (sin cambios). Próximo: triaje de 19 candidatos EN PARALELO con decisiones sobre 007/008.

### 2026-09-24 00:24 — Captura manual Quantpedia para 002 (Claude-app, dentro de la prioridad de captura autorizada)
- `IDEA-98890471BE`: "Turn of the Month en índices bursátiles", capturada desde Quantpedia (público, sin contenido de pago). Triaje 100/100, sin duplicados.
- Fuente primaria real: Xu & McConnell 2006 (SSRN), sobre el hallazgo original de Lakonishok & Smidt 1988. 1 solo instrumento, regla simple, confianza "strong" según Quantpedia, compatible con CFD además de ETF/futuros.
- Objetivos propuestos: SP500/US30/NAS100/DAX en D1. Queda en `captured`, encolada para revisión de evidencia de `investigator` — no se promovió ni se tocó el motor.
- Da evidencia real a la decisión pendiente de 002 (implementar familia calendario o archivar). No se ejecutó backtest ni se abrió OOS.

### 2026-09-24 00:44 — `calendar_window` y contrato 002 (Codex, autorizado)
- Implementada señal causal por fecha: penúltimo día hábil lunes-viernes, sin mirar barras futuras; festivos quedan como reserva de calendario.
- Spec congelada como adaptación NAS100 CFD: solo largo, ATR14, SL 1.5×, TP 2.5×, riesgo 0.5% y `max_holding=4`.
- Contrato registrado como `6bf8c50304e4a65a16b3e2a2`; pipeline: `NEEDS_IS_RUN`, siguiente actor `engine`.
- No se ejecutó Gate 0/IS, no se tocó 008/007/009 y OOS permaneció cerrado.

### 2026-09-24 01:05 — Repo conectado a GitHub y Gate 0 + IS de 002 (Claude-app, autonomo dentro de lo delegado)
- Repo privado creado por Alexander y conectado: `https://github.com/ac75management/QuantAgentFactory`. Revisé el árbol completo (actual e historial) antes de subir: sin credenciales ni archivos sensibles; `.gitignore` ya excluye `data/`, `reports/`, `state/`. Push inicial del historial existente hecho; los 51 cambios locales sin consolidar de hoy quedan sin comitear (regla: commits solo si Alexander los pide).
- Gate 0 de 002 (NAS100/D1) pasó estructura/frecuencia; calendario, `price_basis` y procedencia quedaron en `RESERVE`, no en `FAIL` — no bloquean un veredicto de descarte.
- Corrida IS `d6d5a5555ad5cac3430e4d0b` (147 operaciones): `DISCARDED_IS`. Net P&L -17.816 (-17,8%), PF 0.45, friction ratio -0.91 (el swap de mantener largo 3-4 días domina cualquier edge bruto: financing_cashflow -17.958 frente a gross_pnl +1.812), AED por rotación p=0.45 (sin patrón direccional antes de costos), bootstrap con IC 95% enteramente negativo, sensibilidad 0% de vecinos positivos. No supera el baseline (que también perdió, -101.931, pero eso no rescata a la estrategia).
- `config/hypotheses.json` y `docs/hypotheses/_registry.md` actualizados; `qaf.consistency` sin divergencias; suite completa: 189 pruebas pasadas. OOS no se abrió.
- Trabajo hecho dentro de la autorización permanente y la delegación vigentes (sin evidencia nueva, sin tocar OOS/bróker/automatización); no se tocó 007 ni 008, que siguen esperando decisiones de Alexander.

### 2026-09-24 01:15 — Cierre de catálogo pendiente (Claude-app, autonomo)
- `IDEA-98890471BE` cerrada: `rejected`/`HYPOTHESIS_TESTED_AND_DISCARDED` — ya cumplió su función como evidencia corroborante de 002 (discarded_is); no se crea una hipótesis nueva sobre la misma regla/objetivo ya probada.
- Catálogo sin fichas `captured` pendientes. `qaf.consistency` sin divergencias.
- Revisé `qaf.coordination status` y `qaf.pipeline` completos: 007 y 008 siguen como únicos pendientes, ambos reservados a Alexander (evidencia de Kaufman y decisión de datos EURUSD/H4). Nada más que avanzar sin tocar lo reservado en este ciclo.

### 2026-09-24 03:54 UTC — Auditoría preliminar IS (Codex)
- Entrega y pendientes en `data/QUALITY_AUDIT.md`; RSI coincide en muestra, spread histórico preservado requiere revisión de semántica y costos.
- Hallazgo enviado a Claude por AGENTS: estado inválido de 007 provoca preflight FAIL y 2 fallos de 189 pruebas.
- Sin modificar motor/config/datasets, sin abrir OOS ni conectar bróker; comparativa de operaciones y calendario completo pendientes.

### 2026-09-24 04:08 UTC — Sondeo de ejecución (Codex)
- Comprobadas 100 barras IS: 34 entradas/salidas/direcciones coincidentes, error neto máximo 5.55e-17; no certifica stops, sizing dinámico ni calendario.
- Evidencia entregada a Claude en `data/QUALITY_AUDIT.md`; suite sigue 187/189 por estado inválido de 007, sin cambios de motor ni OOS.

### 2026-09-24 04:23 UTC — Entrega reproducible de indicadores y spread (Codex)
- Añadido `scripts/audit_is_spotcheck.py`, solo lectura IS, y resultado local `data/audit/is_spotcheck.json` con huellas SHA256 y comparativa por barra.
- Verificación repetida: RSI coincide a tolerancia 1e-10; spread antiguo no permite concluir costos actuales ni slippage. Guía de validación aplicada: compartir con reservas, no certificar infraestructura completa.
- Suite: 187 pasan, 2 fallan por estado preexistente de 007; preflight conserva ese fallo. Sin cambios de motor/config, OOS, bróker, commit o push.
- Próximo: Claude audita la entrega; aún faltan artefactos reproducibles del sondeo de operaciones y cierre de reservas de calendario/costos.

### 2026-09-24 06:58 UTC — Experiment Registry mínimo (Codex)
- Implementado registro JSONL append-only en `data/trials_registry.jsonl`, con hash de spec/costos, gates y métricas.
- `qaf.cli count-trials [--hypothesis] [--family]` expone conteo total y agrupado; duplicados fallan cerrado.
- Integrado en el flujo de `qaf.runner` después de cada run IS; no registra sensibilidad aún porque requiere contexto explícito de vecino.
- Tests nuevos y regresión parcial: 54 pasaron; no se ejecutó ningún ensayo nuevo, OOS ni bróker.
- Pendiente auditoría de Claude y suite completa; umbrales y config de costos no fueron modificados.

### 2026-09-24 04:45 UTC — Auditoría de infraestructura completada (Claude)
- **Reproducibilidad verificada:** `python -m scripts.audit_is_spotcheck` produce exactamente el mismo SHA256.
- **RSI(2):** ✓ OK, error 1.42e-14. Indicador es correcto.
- **Ejecución causal:** ✓ OK, 34/34 operaciones coinciden en primeras 100 barras, error neto 5.55e-17. Sin look-ahead ni data leakage.
- **Spread histórico:** ⚠️ DISCREPANCIA. Datos IS: 7–50 pips (media 35.98). Config: 4 pips (fijo). Config es más optimista que realidad; backtest sobrestima ganancias.
- **Slippage:** ✗ No modelado (asume 0). Backtest no include comisiones de ejecución reales.
- **Calendario:** ⚠️ Reservado. EURUSD pre-1999 sin procedencia verificada; no inspeccionado (riesgo bajo si estrategias no son hora-dependientes).
- **Síntesis:** Infra es mayormente OK; sesgo optimista en costos es probable causa parcial de fallos IS (hipótesis frágiles con edge muy marginal, destruidas por costos reales).
- **Estado 007:** Corregido de `pending_protocol` (inválido) → `blocked_architecture` (válido). Suite ahora 189/189.
- **Archivo de síntesis:** `docs/INFRASTRUCTURE_AUDIT.md` con recomendaciones por prioridad.
- **Próximo paso:** Alexander decide spread/slippage → re-ejecutar si significativo, o proceder a triaje de 19 candidatos.
