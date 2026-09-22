## CURRENT OBJECTIVE
Construir una fábrica de agentes (Claude Code) que lleve hipótesis de trading desde la idea hasta una estrategia validada, siguiendo el método TIS. Proyecto nuevo e independiente de ZOO2 — no toca cuentas ni capital en vivo.

## CURRENT STATUS
Pipeline de datos real y funcionando de punta a punta contra Darwinex MT5 (2026-09-22): `docs/universe.md` es la fuente única (10 símbolos active + BTCUSD blocked), los 3 scripts (`extract_darwinex_ohlc.py`, `extract_darwinex_costs.py`, `build_clean_data.py`) leen ese archivo sin listas propias, `data/raw/darwinex/` y `data/clean/<ALIAS>/<TF>/{IS,OOS}.parquet` usan el mismo alias que la tabla. `docs/cost_model.md` sección LIVE regenerada con `tick_size` incluido (antes faltaba — bug real, ver abajo); `commission_per_side` sigue `SIN_CONFIRMAR` para todos los símbolos (MT5 no lo expone, pendiente confirmación manual de Alexander). Gate 0 (`scripts/run_gate0.py`) re-corrido sobre los alias actuales — 20/20 series `APTO_CON_RESERVAS` (ninguna RECHAZADA), caché en `reports/_data_quality/` limpio de nombres viejos (SPX500/GER40/USOIL eliminados).

Los 4 agentes ya estaban prácticamente listos para el dry-run (rondas de revisión externa de 2026-09-23: registro de hipótesis obligatorio, rechazo de specs sobre símbolos/costos no confirmados, fill model explícito, split IS/OOS físico, puerta de baseline, meta.yaml, `INVALID_POR_DATOS`). Cambios de este turno: `engine.md` permite continuar sobre `APTO_CON_RESERVAS` sin confirmación en chat cuando la spec declara `tipo: dry-run` (reserva documentada, no oculta); `protocol.md`/`validator.md` ahora fijan que la puerta de baseline es "comprar y mantener del mismo símbolo y timeframe, neto de cost_model" — nunca el índice cash de otra fuente — y que si ese BH neto ya es negativo, el piso no es cero: una estrategia no pasa por "perder menos que el baseline" si igual pierde dinero.

**Dry-run formalizado vía el flujo de `engine`** sobre `docs/specs/dryrun_bh_sp500.md`: Gate 0 real en `reports/dryrun_bh_sp500/data_quality.md` (APTO_CON_RESERVAS — cost_key sin confirmar, 80 gaps no explicados por fin de semana, precio mid sin confirmar), resumen completo en `reports/dryrun_bh_sp500/resumen.md`. **P&L neto real: -11,062.16** (bruto +26,303, swap acumulado -37,358.61) — corrigiendo un bug de unidades del cálculo rápido del turno anterior (trataba la diferencia de precio cruda como si ya estuviera en "puntos"; SP500 tiene `tick_size=0.1`, no 1.0 — el dato ya estaba en el JSON de `extract_darwinex_costs.py` pero nunca se promovió a la tabla LIVE). Mismo ejercicio corrido también en EURUSD (+431.50, casi neutro en 39 años) y XAUUSD (-213,786.95, el más caro del universo) — tabla completa en `reports/dryrun_costs_comparativa.md`. Script: `scripts/dryrun_bh.py --alias <ALIAS>` (parametrizado, lee costos de `docs/cost_model.md`/`docs/universe.md`, reemplaza al `dryrun_bh_sp500.py` de un turno atrás). No se invocó `validator` — OOS de ningún símbolo se tocó.

**Resumen de los 3 dry-run BH (`reports/dryrun_costs_comparativa.md`), IS completo D1:**

| símbolo | bruto | swap | neto | conclusión |
|---|---|---|---|---|
| SP500 | +26,303.00 | -37,358.61 | **-11,062.16** | Piso ya negativo — swap se come toda la ganancia |
| EURUSD | +83,897.00 | -83,456.50 | **+431.50** | Casi cero en 39 años — sin margen real tras comisión/slippage |
| XAUUSD | +103,902.00 | -317,632.40 | **-213,786.95** | El más caro — swap_long de oro domina incluso tendencia alcista fuerte |

**Decisión de esta sesión (2026-09-22, autorizada por Alexander):** BH de años queda descartado para CFD índice/metal de este bróker. Próximas hipótesis: holding corto (días, máx. pocas semanas). Baseline obligatorio = BH neto del mismo símbolo/timeframe con cost_model, nunca índice cash externo. No se instalan herramientas nuevas (Gemini, MCP) este turno. OOS sigue sin tocar.

Repo git local, todo staged, sin commit.

## DECISIONS
- Proyecto independiente de ZOO2. (2026-09-21)
- Ubicación: `OneDrive\Escritorio\QuantAgentFactory\`. (2026-09-21)
- Alcance: CFDs (índices, forex, materias primas) + futuros; diario/4H mínimo; excluido scalping, alta frecuencia y rebalanceo de cartera. (2026-09-21)
- Kaufman/Raschke quedan como ejemplos ilustrativos del video fuente, no como catálogo cerrado — `investigator` busca por su cuenta dentro del alcance. (2026-09-21)
- Calidad de datos es Gate 0, obligatorio antes de AED — checklist en `.claude/skills/data-quality-check/SKILL.md`. (2026-09-21)
- No se necesita más extracción de NotebookLM sobre el video original — lo cubierto alcanza. Investigación de hipótesis futuras la hace `investigator` directamente (WebSearch/WebFetch), caso por caso. (2026-09-21)
- **Buy-and-hold de años (múltiples años) queda descartado como estrategia viable en CFD índice/metal de Darwinex** — el swap acumulado domina y se come la ganancia bruta en 2 de 3 símbolos probados. (2026-09-22)
- **Las próximas hipótesis de `investigator` deben ser de holding corto: días, máximo pocas semanas** — nunca años. (2026-09-22)
- **El baseline obligatorio (regla 19 de CLAUDE.md) es siempre buy-and-hold neto del mismo símbolo y timeframe, con `cost_model.md` aplicado** — nunca el índice cash u otra fuente sin esos costos. (2026-09-22)

## NEXT ACTION
Hipótesis 001 formalizada y registrada (2026-09-22): `docs/hypotheses/xauusd-d1-mean-reversion-streak-extension.md` — reversión de corto plazo en XAUUSD D1 tras racha de 3+ días, holding 2-5 sesiones. Bloqueada para pasar a `protocol`/`engine` hasta que `cost_key=metal` en `docs/cost_model.md` deje de estar `SIN_CONFIRMAR` (regla 17, ratio de fricción). Pendiente manual de Alexander: confirmar spread/swap/`commission_per_side` reales de XAUUSD (Darwinex Market Watch → especificación del símbolo). No invocar `validator` todavía (ningún OOS abierto).

## OPEN QUESTIONS
1. ~~Fuente de datos histórica y bróker de referencia~~ — RESUELTO 2026-09-23: **Darwinex, vía MT5**, universo fijo de 11 símbolos CFD (ver docs/universe.md). `docs/cost_model.md` sigue en placeholder — falta que Alexander confirme spread/comisión/swap reales de su cuenta (Market Watch → especificación del símbolo). `scripts/extract_darwinex_ohlc.py` todavía no se corrió contra un terminal real — los `symbol_mt5` de docs/universe.md son candidatos de documentación pública de Darwinex, no verificados en vivo.
2. ~~Ratio mínimo expectancy/costo de bróker~~ — RESUELTO 2026-09-23: fijado en ≥3.0, CLAUDE.md regla 17.
3. ~~Límite de parámetros libres por estrategia~~ — RESUELTO 2026-09-23: fijado en 3-4, CLAUDE.md regla 16.
4. ¿GitHub remoto ahora o más adelante? El repo local ya es funcional para Claude Code tal cual está.
5. **¿Acceso a datos COT (Commitment of Traders)?** — necesario para poder usar parte del material de Larry Williams (ver docs/author_library.md). Si no hay acceso, esas hipótesis puntuales quedan descartadas, no todo el autor.
6. ¿Primer mercado/activo concreto a probar, una vez resuelta la pregunta 1? (XAUUSD ya elegido para el dry-run inicial, ver docs/universe.md — pendiente confirmar si es también el primer activo "real".)

## OPEN QUESTIONS (nuevas de ronda 3)
- "OmniRoot" — Alexander lo mencionó (conectar skills para ahorrar tokens) pero no quedó claro qué herramienta/concepto es exactamente. Pendiente de una línea de aclaración.

## PARKED IDEAS
- Dashboard interactivo en Streamlit para AED y resultados de backtest.
- Exportar estrategia aprobada a MQL5/PineScript.
- Script de comparación cruzada de fuente de datos contra el bróker real (parte del checklist de calidad, todavía no implementado como código).
- Combinación a nivel de portafolio de varias estrategias aprobadas en distintos activos (visión final del usuario: "múltiples estrategias colaborando"). No se construye todavía — cero estrategias aprobadas hasta ahora.
- "Cuentas lógicas" (Split & Compound) y matrices de correlación <0.34 para combinar estrategias — gestión de capital post-aprobación, ver docs/sources/empirical_research_notes.md.
- Conectar `.claude/skills/` entre sí para que los agentes compartan trabajo y ahorren tokens (mencionado por Alexander, sin detalle todavía).

## FILES / SOURCES
- [CLAUDE.md](CLAUDE.md) — reglas duras + alcance
- [docs/review_summary.md](docs/review_summary.md) — primera ronda de revisión externa (arquitectura general)
- [docs/review_round2.md](docs/review_round2.md) — segunda ronda de revisión (datos + biblioteca de autores), pendiente de pasar por Gemini
- [docs/author_library.md](docs/author_library.md) — catálogo vivo de autores, categoría A (hipótesis) vs. B (validación)
- [docs/architecture.md](docs/architecture.md) — mapa del pipeline con diagrama de flujo
- [docs/taxonomy.md](docs/taxonomy.md) — taxonomía del iceberg de trading (6 niveles), filtro de fuentes para investigator
- [docs/review_round3.md](docs/review_round3.md) — tercera ronda de revisión, 4 conflictos del material nuevo
- [docs/sources/empirical_research_notes.md](docs/sources/empirical_research_notes.md) — reclamos empíricos externos, con caveats de fuente
- [docs/philosophy.md](docs/philosophy.md) — método TIS y glosario
- `.claude/agents/*.md` — 4 subagentes
- `.claude/skills/data-quality-check/SKILL.md` — checklist de calidad de datos
- [docs/cost_model.md](docs/cost_model.md) — costos de bróker por cost_key/categoría (borrador, Darwinex)
- [docs/universe.md](docs/universe.md) — catálogo de 11 símbolos Darwinex + mapeo a symbol_mt5
- [docs/hypotheses/_registry.md](docs/hypotheses/_registry.md) — registro de todas las hipótesis probadas
- [scripts/extract_darwinex_ohlc.py](scripts/extract_darwinex_ohlc.py) — descarga OHLC D1/H4 desde el terminal MT5
- [scripts/build_clean_data.py](scripts/build_clean_data.py) — normaliza y corta IS/OOS físico + manifest.json

## LAST UPDATED
2026-09-22
