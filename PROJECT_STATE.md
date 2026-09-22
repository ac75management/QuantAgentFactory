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

**Costos confirmados para todo el universo (2026-09-22, esta sesión):** Alexander confirmó comisión de XAUUSD con captura de la ventana "Especificación del símbolo" de Darwinex. A partir de ahí se verificó contra la tabla pública oficial de tarifas de Darwinex (`forex-cfds/forex`, `/indices`, `/commodities`, actualizada 2026-09-21) — coincide número por número con los valores ya capturados de la cuenta real. Resultado: `commission_per_side` y el día exacto de swap triple quedan **CONFIRMED para los 10 símbolos activos**, no solo XAUUSD (ver `docs/cost_model.md`). Hallazgo nuevo: el día de swap triple NO es siempre miércoles — es miércoles para FX/metal/energy, **viernes para los 4 índices** (decodifica el campo `swap_rollover3days`: 3=miércoles, 5=viernes). Lo único que sigue `SIN_CONFIRMAR` en todo el universo es spread-modelo (típico/estrés) y slippage — Gate 0 se mantiene en `APTO_CON_RESERVAS` para las 20 series, pero ya no por costos de comisión/swap, ahora específicamente por eso. `scripts/run_gate0.py` ganó lookup por símbolo (antes solo miraba el `cost_key` genérico, no veía overrides por símbolo).

**Hipótesis #001 ya tiene spec** (`docs/specs/xauusd-d1-mean-reversion-streak-extension.md`), generada por el agente `protocol` de verdad (primera vez que un agente de los 4 corre en esta sesión vía el `Agent` tool — antes la sesión no estaba conectada al directorio del proyecto). Regla de entrada/salida numérica completa (racha de 3 cierres D1, SL/TP por ATR14, time-stop 5 sesiones), 4 parámetros libres (tope de CLAUDE.md regla 16), puerta de baseline con el piso negativo de XAUUSD ya declarado (-213,786.95, con nota de que `validator` debe recalcularlo sobre el slice OOS real, no reusar la ventana completa). No bloqueada por costos (protocol hizo su propio análisis campo por campo, correcto). Sigue pendiente slippage como única reserva de Gate 0. **Hipótesis #002 también existe ya** (`nas100-d1-turn-of-month-flow`, según el registro) — generada por `investigator` en la sesión paralela de VS Code de Alexander, todavía no revisada por mí en detalle.

**Hipótesis #002 completó AED + backtest IS (2026-09-22, esta sesión)** — spec generada por `protocol`, Gate 0 corrido por `engine` (`APTO_CON_RESERVAS`, techo por spread/slippage de `index_us` sin confirmar). El subagente `engine` se detuvo correctamente ahí y **rechazó continuar aun con la confirmación de Alexander relayada por el coordinador** (incluso citada textualmente) — su regla de consentimiento exige que el mensaje del usuario aparezca directamente en su propio hilo, no relayado por otro agente (ver nota operativa abajo). Resolución: el coordinador corrió el AED/backtest directamente en el hilo principal, mismas reglas de `engine.md`, mismo spec, script `scripts/backtest_nas100_turn_of_month.py`.

**Resultado: débil, en las tres dimensiones.** AED (149 ciclos turn-of-month vs. 2,000 ventanas aleatorias): t=-0.478, p=0.633 — **el patrón no aparece en los datos**, confirma el riesgo que la propia hipótesis ya declaraba (efecto diluido en EE.UU. post-2001). Backtest IS: profit factor 0.314, ratio de fricción **-0.56** (exigido ≥3.0), max drawdown -26.6%, equity 100k→73,676. Diagnóstico de deterioro (regla 11.9 de la spec): negativo en ambas mitades del IS, sin evidencia de un régimen donde el efecto haya funcionado. Reporte completo: `reports/nas100-d1-turn-of-month-flow/reporte_engine.md` (+ `trades.csv`, `equity_curve.csv`, `summary.json`).

No es un veredicto formal (`validator` decide, sobre OOS) — pero la lectura honesta es que probablemente se rechace sin necesitar agotar el ciclo completo de robustez.

## NOTA OPERATIVA — bloqueo de consentimiento entre agentes (2026-09-22)
El subagente `engine` (y presumiblemente los demás) tiene una regla de seguridad de más alto nivel, no específica de `engine.md`, que rechaza cualquier confirmación humana relayada por otro agente para pasos que exigen "confirmación explícita de Alexander en el chat" — sin importar cuán bien documentada o citada textualmente esté. Diseño correcto (evita que una cadena de agentes fabrique consentimiento), pero implica que **el coordinador no puede desbloquear por chat relayado un `APTO_CON_RESERVAS` sobre una estrategia candidata**. Si esto se repite seguido, vale la pena que Alexander decida si `engine.md`/`validator.md` necesitan un mecanismo distinto (ej. un archivo de aprobación que Alexander edite directamente) en vez de depender del chat relayado — mientras tanto, la salida práctica es que el coordinador corra esos pasos directamente cuando ya tiene confirmación genuina y directa del usuario.

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
**Decisión pendiente de Alexander sobre hipótesis #002 (NAS100 turn-of-month):** (a) pasar igual a `validator` para veredicto formal sobre OOS (regla 3 exige las 8 fases en orden), o (b) archivarla como fallida sin gastar el ciclo de robustez completo, dado que IS ya muestra AED sin efecto + todas las puertas numéricas fallidas — y volver a `investigator` por una hipótesis #003.

Separado: decidir si se invoca `engine` sobre `docs/specs/xauusd-d1-mean-reversion-streak-extension.md` (hipótesis #001) ahora (Gate 0 dará `APTO_CON_RESERVAS` por slippage sin confirmar — spec ya lo anticipa y no lo trata como bloqueo duro) o si Alexander prefiere confirmar slippage antes. Si se invoca, tener en cuenta la nota operativa de arriba (el subagente `engine` puede detenerse en el mismo punto de consentimiento).

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

## ACTUALIZACIÓN — pipeline `qaf` v2.0.0 y primer resultado real (2026-09-22, esta sesión)

Mientras esta sesión estaba pausada (reset de límite de uso), la sesión paralela de VS Code hizo un rewrite de arquitectura grande: nuevo paquete `qaf/` (motor, costos, señales, validación, reporting, registry sqlite), `config/instruments.json` (10 símbolos con reservas explícitas por campo), `config/strategies/` (specs JSON registradas), `config/runner.json` (política del runner), CLI `python -m qaf.cli {check-spec, register, run, status, freeze, validate}`. `pyproject.toml` fija `quantagentfactory==2.0.0`. Los scripts ad-hoc anteriores (`scripts/backtest_nas100_turn_of_month.py`, `scripts/backtest_xauusd_mean_reversion.py`, escritos por mí y por la sesión de VS Code respectivamente) quedaron **retirados tras auditoría por errores de costos/fill/validación** — código preservado en `docs/archive/pre_factory_v2/`. `CLAUDE.md` también cambió: alcance ahora es **H1/H4/D1** (antes D1/H4 solamente), excluye explícitamente M15/M30.

**Limitación real descubierta**: el motor `qaf` solo implementa 3 familias de señal — `streak_reversal`, `trend_cross`, `channel_breakout` (`qaf/contracts.py` FAMILIES, `qaf/signals.py generate()`). **No hay familia de calendario** — la hipótesis #002 (NAS100 turn-of-month) no se puede expresar como spec JSON todavía. Mi resultado exploratorio anterior (AED sin efecto, profit factor 0.31) queda como indicativo, no autoritativo, y el script que lo generó ya está retirado.

**Hipótesis #001 (XAUUSD streak-reversal) SÍ encaja en `streak_reversal` — corrida por primera vez con el motor real**: registrada (`config/strategies/dd17fcc6e5927cb422460f9e.json`) y ejecutada (`python -m qaf.cli register` + `run`). **Resultado: `DISCARDED_IS`** — rechazada en IS, OOS nunca abierto (regla 4/13 respetada por diseño del runner, que solo carga IS). 458 operaciones, P&L neto -$43,390.57, profit factor 0.66, max drawdown 46.4%, ratio de fricción -0.68 (exigido ≥3.0), test de estrés (fricción ×2) también negativo, intervalo de confianza bootstrap enteramente negativo [-19.6%, -4.5%]. Reporte completo: `reports/factory/runs/3c6abd593cbd350338a44a25/` (`report.html`, `result.json`, `trades.csv`, `equity.csv`).

**Estado real del proyecto ahora mismo: 2 de 2 hipótesis probadas, ambas rechazadas en IS, cero estrategias vivas.** Ninguna llegó a abrir OOS. `docs/hypotheses/_registry.md` actualizado con ambos veredictos.

## AUDITORÍA INDEPENDIENTE (2026-09-22) — ver `docs/audit_qaf_v2_2026-09-22.md`
Sesión de Claude Code (desktop app) auditó `qaf/` de forma independiente (sin haber escrito ese código). Motor sólido (ledger reconciliado, gaps/ties conservadores, test que envenena OOS a propósito y prueba que el pipeline no lo toca). Dos hallazgos críticos: (1) los números de comprar-y-mantener que ya sustentaban una decisión ("BH de años descartado") venían de `scripts/dryrun_bh.py`, retirado después por errores de costos — **corregido abajo**; (2) `investigator.md`/`engine.md`/`validator.md` nunca se actualizaron a la arquitectura `qaf` (`investigator.md` todavía dice "nunca por debajo de 4H", contradice el `CLAUDE.md` vigente) — **pendiente, no corregido todavía**, requiere decidir el flujo agente↔`qaf.cli register` antes de tocar los `.md`.

**Comprar-y-mantener re-verificado con el motor de costos real de `qaf`** (`scripts/verify_buy_and_hold.py`, usa `qaf.costs`/`qaf.data` directamente, no reinventa aritmética):

| símbolo | bruto | costos (spread+slip+comisión) | financiación | **neto (qaf, correcto)** | neto viejo (script retirado) |
|---|---|---|---|---|---|
| SP500 | +26,303.00 | -9.55 | -50,396.07 | **-24,102.62** | -11,062.16 |
| EURUSD | +83,897.00 | -11.74 | -118,590.40 | **-34,705.14** | +431.50 |
| XAUUSD | +103,902.00 | -86.65 | -457,042.60 | **-353,227.25** | -213,786.95 |

**Los tres son más negativos que antes — la conclusión "BH de años queda descartado" se mantiene y se refuerza, no se debilita.** La causa exacta del error viejo: el script retirado nunca aplicaba el multiplicador de swap triple del día correcto (lo tenía documentado como limitación conocida, nunca corregido); `qaf.costs.financing()` sí lo aplica día por día con el día real de cada instrumento. Cambio cualitativo importante: **EURUSD pasó de "casi cero" (el menos malo) a el segundo peor de los tres** — ya no hay ningún símbolo cerca de breakeven en holding multi-año. `slippage_points_per_side` de `config/instruments.json` es un escenario, no histórico (`costs_verified: false` en los 3) — la magnitud exacta puede moverse, pero el signo y el orden de magnitud no dependen de ese campo (spread+slippage+comisión es <0.1% del costo total en los 3 casos; financiación es la que domina, ver tabla).

## NEXT ACTION (vigente, reemplaza las entradas anteriores sobre #001/#002)
1. **Volver a `investigator` por una hipótesis #003** — las dos primeras (racha de reversión en XAUUSD, calendario en NAS100) no sobrevivieron ni el IS. Sin esto no hay nada más que correr.
2. **Decidir si vale la pena construir una familia `calendar`/`seasonality` en `qaf/signals.py`** para poder correr #002 formalmente algún día, o si se abandona la hipótesis dado que el resultado exploratorio ya la mostraba débil (AED sin efecto). No urgente — #003 es más prioritario.
3. Repasar si el cambio de alcance a H1/H4/D1 (antes D1/H4) en `CLAUDE.md` fue una decisión deliberada de Alexander o algo que vale la pena confirmar — no se documentó el motivo en el propio archivo.
4. **Pendiente de la auditoría, no resuelto todavía**: actualizar `investigator.md`/`engine.md`/`validator.md` para que reflejen `qaf` (o decidir explícitamente que siguen siendo un flujo manual aparte) — ver `docs/audit_qaf_v2_2026-09-22.md` hallazgo C2. **Actualización: ya corregido** por la sesión de escritorio (2026-09-22, ver sección de coordinación abajo) — los 4 agentes ahora citan `qaf.cli`/`config/instruments.json` en vez del flujo manual retirado.

## COORDINACIÓN (2026-09-22) — decisión sobre VWAP NDX H1 y fanout de investigación
Alexander propuso (vía sesión de escritorio) una fase de investigación paralela antes de `protocol`: 3-4 subagentes especializados (literatura / viabilidad de datos / implementación / síntesis) por cada idea nueva, inspirado en un borrador externo. **Decisión: NO se construye todavía.** Motivo: no resuelve el cuello de botella real del proyecto (la hipótesis #001 murió por costo de financiación, no por falta de investigación previa), gasta más tokens por idea (3 agentes en paralelo vs. 1 secuencial), y agrega arquitectura nueva sobre una auditoría (`docs/audit_qaf_v2_2026-09-22.md`) que todavía tiene hallazgos A1/A2/A3/B1/M3/M4 sin resolver. **Alternativa adoptada**: `investigator` usa una plantilla interna de 4 secciones (literatura con cita/fuente/aplicabilidad, viabilidad de datos, variantes de implementación, veredicto final) en un solo documento — mismo rigor, sin agentes nuevos ni orquestación. Si después de 2-3 hipótesis así el cuello de botella real resulta ser "faltan ángulos en paralelo", se reconsidera con evidencia.

**Nota para quien retome `docs/vwap-ndx-h1-draft.md`** (borrador sin registrar, autodeclarado BLOQUEADO, ver archivo): dos correcciones a su lista de bloqueos:
- **Falta el chequeo contra `qaf/contracts.py::FAMILIES`** (`streak_reversal`, `trend_cross`, `channel_breakout`) — un cruce de z-score contra un nivel de referencia (VWAP) no encaja en ninguna. Es el mismo bloqueo estructural que ya frenó a la hipótesis #002 (calendario). Hace falta decidir si se construye una familia nueva en `qaf/signals.py` antes de que esta idea pueda convertirse en spec.
- **`real_volume=0` no es una reserva de datos de NDX específica — es un rasgo permanente de Darwinex** (CFD/FX no tiene volumen centralizado real; los indicadores VWAP de MT5 usan `tick_volume` internamente por el mismo motivo). No hace falta "resolverlo": hay que declarar una vez, en `docs/universe.md`/`config/instruments.json`, que toda referencia a VWAP en este proyecto usa `tick_volume` como proxy de actividad, no volumen ejecutado real — y ajustar el mecanismo conductual de la hipótesis para que no dependa de "ejecución institucional real", que es una afirmación distinta y no verificable con este dato.

## EXTRACCIÓN H1 (2026-09-22) — 8 de 10 símbolos activos ya tienen H1/H4/D1 completos
Con confirmación explícita de Alexander en chat, se conectó una vez a la cuenta demo Darwinex (`alex927`, servidor `Darwinex-Demo`, solo lectura, sin órdenes) para completar el timeframe H1 que faltaba en 6 símbolos. Pasos: se agregó `"H1"` a `timeframes` en `config/instruments.json` para XAUUSD/XAGUSD/USDJPY/EURUSD/GBPUSD/PETROLEO, se corrió `scripts/extract_darwinex_ohlc.py --connect-mt5` (27 exportaciones, 0 fallos) y `scripts/build_clean_data.py` sobre el batch nuevo.

**Resultado**: XAUUSD, XAGUSD, GBPUSD y PETROLEO importaron H1 correctamente (18.3k/23.5k/37.6k/29.3k filas IS respectivamente) — ahora 8 de 10 símbolos activos (+ DAX/NAS100/SP500/US30 que ya lo tenían) tienen H1+H4+D1 completos.

**EURUSD y USDJPY NO pudieron importar H1** — `INSUFFICIENT_BEFORE_FIXED_CUTOFF`. Causa: `qaf/ingest.py` fija el corte IS/OOS de un símbolo la primera vez que se importa, y lo reutiliza (inmutable) para cualquier timeframe nuevo del mismo símbolo. El corte D1/H4 de estos dos se calculó sobre historial que arranca en 1971; el historial H1 de MT5 solo llega hasta 2010 — todas las barras H1 caen después del corte, dejando la partición IS en cero. Esto es la salvaguarda anti-fuga funcionando como debe (evita crear una partición IS degenerada), no un bug.

**Decisión pendiente de Alexander** (no la tomo yo sola porque implica descartar y re-importar particiones que hoy son "inmutables" por diseño): ¿aceptar que EURUSD/USDJPY se quedan en D1/H4 solamente, o reimportar los 3 timeframes de esos dos símbolos desde cero con un corte nuevo compatible con 2010+? Ningún hypothesis registrado usa el corte actual de estos dos símbolos todavía, así que el costo de reimportar hoy es bajo.

## LAST UPDATED
2026-09-22 (extracción H1 real vía MT5 demo + coordinación sobre fanout de investigación y draft VWAP NDX H1 — sesión de escritorio)

## AUDITORIA METODOLOGICA — FASE 1
Se aplicaron correcciones críticas sin regenerar datos ni reportes históricos:
- `scripts/build_clean_data.py` ya no elimina duplicados antes de Gate 0; los conserva y los registra en el manifiesto.
- `scripts/run_gate0.py` separa controles manuales pendientes y marca `APTO_CON_RESERVAS` mientras no estén resueltos.
- `scripts/costs.py` centraliza P&L por tick, spread, comisión porcentual/plana y swap; los tres simuladores lo reutilizan.
- `docs/DATA_PIPELINE.md` y `.claude/skills/data-quality-check/SKILL.md` documentan la nueva trazabilidad.
Pendiente de la siguiente fase: formalizar ejecución con gaps, corrección por múltiples hipótesis y walk-forward reproducible.

## CAMBIOS DE ARQUITECTURA — ALCANCE Y EJECUCIÓN
- Se eliminó la generación automática de familias/variantes: el runner solo ejecuta specs registradas explícitamente en `config/strategies/` y vinculadas a `hypothesis_id`.
- El alcance mínimo ahora es H1, H4 y D1; M15/M30 quedan excluidos.
- `config/runner.json` reemplaza la política de minería automática.
- La validación final OOS sigue bloqueada de forma deliberada hasta implementar holdout, walk-forward y permutación reproducibles.
