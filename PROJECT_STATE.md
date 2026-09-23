## CURRENT OBJECTIVE
Construir una fábrica de agentes (Claude Code) que lleve hipótesis de trading desde la idea hasta una estrategia validada, siguiendo el método TIS. Proyecto nuevo e independiente de ZOO2 — no toca cuentas ni capital en vivo.

## CURRENT STATUS
**Actualización operativa más reciente (2026-09-22):** el catálogo ya tiene una puerta controlada entre idea externa e hipótesis. `catalog-review` exige evidencia estructurada y `catalog-promote` solo acepta ideas `eligible` del carril `mt5_now`; registra una única hipótesis, genera su documento, actualiza el registro y deja una sola tarea para `protocol`. La promoción es idempotente, serializa procesos concurrentes mediante SQLite, bloquea IDs/rutas inválidos y detecta duplicados por fuente + regla estable + objetivo. OOS continúa cerrado.

**Piloto 001:** KAMA tendencial + ER sobre XAUUSD D1 completó revisión de evidencia y originó la hipótesis **007** como adaptación explícita; `protocol:007` está en cola y todavía no existe spec ni backtest. La fuente pública documenta fórmula, giro, filtro, entrada, stop y sizing, pero la ficha conserva cuatro reservas: fuente secundaria respecto del libro de Kaufman, frecuencia original no declarada, entrada al mismo cierre no causal y traslado de cartera de 42 futuros a un CFD. Donchian + ER sobre DAX H4 (58/100) y media móvil con banda porcentual sobre EURUSD H4 (58/100) continúan en `evidence_review` y conservan `needs_information`. Suite completa tras integrar los cambios AED concurrentes: **82 pruebas aprobadas**.

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
Procesar `protocol:007`. Debe decidir si puede congelar una variante causal sin seleccionar a posteriori `ER_Length` y `FastMA_Length`; si no existe una convención fuente defendible, bloquear con `AMBIGUOUS_FREE_PARAMETERS` en vez de escoger el mejor backtest. También debe declarar que hace falta una familia KAMA nueva y que la entrada será como pronto en la barra siguiente. Después revisar Donchian+ER y media móvil con banda. No ejecutar IS hasta que exista un contrato validado.

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

## HIPÓTESIS #003 — SPEC GENERADA POR `protocol` (2026-09-22)

`docs/specs/sp500-d1-rsi2-mean-reversion.md` + `.json` escritos, sobre `docs/hypotheses/sp500-d1-rsi2-mean-reversion.md` (hipótesis #003, familia `oscillator_reversion`, primera vez que se especifica formalmente esta familia). Ningún dato de precio tocado, ningún backtest corrido — eso queda para `engine`.

**Valores fijados** (anclados a la fuente, no optimizados): `rsi_period=2`, `entry_threshold=10`, `trend_filter_sma=200` (RSI(2) clásico de Connors, no son parámetros libres de esta spec). **Parámetros libres** (tope de 4, regla 16): `atr_period=14`, `sl_atr=1.5`, `tp_atr=1.0` (1:1, distinto del 2:1 de la hipótesis #001 — razonado por el tipo de edge que reclama Connors: alta tasa de acierto, ganancia modesta), `max_holding=5`. `risk_fraction=0.01`, `direction=both`.

**Costos citados de `config/instruments.json`/`docs/cost_model.md`**: comisión y día de swap triple `CONFIRMED` (viernes ×3 para índices); `spread_points`/`slippage_points_per_side` siguen sin confirmar (mismo techo `APTO_CON_RESERVAS` que el resto del universo). Costo de ejecución round-trip calculado: $9.55/lote (coincide exacto con `scripts/verify_buy_and_hold.py` sobre IS).

**Baseline (sección 9 de la spec)**: B&H neto de SP500 D1 sobre partición **IS** = -24,102.62 (bruto +26,303.00, costos -9.55, financiación -50,396.07 — cifra ya existente de `scripts/verify_buy_and_hold.py`, no recalculada aquí). Es evidencia direccional, no la puerta final — `validator` debe recalcularla sobre `data/clean/SP500/D1/OOS.parquet` específicamente (regla 19), y hoy `scripts/verify_buy_and_hold.py` no expone una ruta OOS todavía.

La spec pide a `engine` dos diagnósticos obligatorios además de las puertas estándar: (a) desempeño por terciles de tendencia/volatilidad, y (b) desempeño por sub-períodos cronológicos del IS (para ver si el edge, si existe, está concentrado en la parte más antigua de la muestra — riesgo de compresión post-publicación que la propia hipótesis ya señala).

## NEXT ACTION (vigente, reemplaza la entrada anterior)
1. **Invocar `engine` sobre `docs/specs/sp500-d1-rsi2-mean-reversion.json`** — Gate 0 primero (se espera `APTO_CON_RESERVAS` por spread/slippage sin confirmar, igual que el resto del universo; la spec ya lo anticipa y no lo trata como bloqueo duro), luego AED y backtest IS. Primera vez que la familia `oscillator_reversion` corre de punta a punta con el runner real — tratar con el mismo escrutinio que cualquier código nuevo (ver hipótesis, sección de caveats).
2. Recordar la nota operativa sobre consentimiento entre agentes (arriba): si `engine` se detiene en un punto que exige confirmación explícita de Alexander, esa confirmación tiene que llegar directamente en el hilo de `engine`, no relayada.
3. Pendiente sin relación directa: decisión de Alexander sobre archivar formalmente la hipótesis #002 (NAS100 turn-of-month) o pasarla igual a `validator` para veredicto formal — no bloquea el avance de #003.

## LAST UPDATED
2026-09-22 (spec de hipótesis #003 generada por `protocol` — sp500-d1-rsi2-mean-reversion, familia oscillator_reversion)

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

## CORRECCIONES DE AUDITORÍA GPT + FAMILIA NUEVA (2026-09-22)
Segunda auditoría adversarial (ChatGPT, sobre el motor `qaf` real) encontró 7 problemas reproducibles — verifiqué los 7 directamente contra el código antes de corregir, los 7 se confirmaron:

1. **Margen forex roto** (`engine.py`): USDJPY calculaba ~$1,570,000 de margen por lote (157x lo real). Corregido reusando `costs.price_cash` (la misma conversión ya validada para P&L) en vez de una fórmula distinta e inconsistente. **0.00% de cambio para XAUUSD/índices/materias primas** — verificado numéricamente antes y después.
2. **Puertas aceptaban métricas imposibles**: profit factor infinito, drawdown -1, bootstrap CI invertido pasaban las 7 puertas. `screening_gates` ahora valida finitud/dominio, y `quality.status=FAIL` bloquea el veredicto adentro de la función (antes dependía de que quien llamara ya lo hubiera filtrado).
3. **Gate 0 no verificaba la frecuencia real** (barras de 2h pasaban como "H4") ni exigía manifiesto/OOS antes de confiar en una partición. Ambos corregidos en `qaf/data.py`.
4. **Registro con reservas `RUNNING` zombis**: un proceso caído entre `reserve()` y `finish()` bloqueaba ese `run_id` (y su cupo de campaña) para siempre. `qaf/registry.py` ahora recupera reservas `RUNNING` de más de 1 hora.

**Verificación de que nada de esto tocó lo ya decidido**: recorrí la hipótesis 001 (XAUUSD) después de cada tanda de cambios — métricas idénticas hasta 15 decimales, mismo veredicto `DISCARDED_IS`, tres veces seguidas. 24 tests pasan (6 nuevos, uno por cada bug reproducido).

**Familia nueva: `oscillator_reversion`** (`qaf/signals.py`, `qaf/contracts.py`) — RSI(n) Wilder + filtro de tendencia SMA, basado en Larry Connors (RSI(2), ConnorsRSI, R3 — agregado a `docs/author_library.md`, ya citado en hipótesis 001 pero nunca formalizado). Parámetros: `rsi_period`, `entry_threshold`, `trend_filter_sma` + los universales (`atr_period`, `sl_atr`, `tp_atr`, `max_holding`). **Reserva declarada**: la fuente original sale por SMA5 sin stop fijo; este motor siempre usa SL/TP por ATR — es un híbrido, no una réplica exacta, documentado en `protocol.md`. Literatura validada específicamente en índices (S&P 500) — el candidato natural para la próxima hipótesis es NAS100 o SP500, no XAUUSD/forex.

**No construido todavía** (documentado, no descartado): DVO (fuente es un sistema de blog, no paper — confianza sobreestimada), ConnorsRSI completo (compuesto de 3 sub-indicadores, mayor complejidad), DVI (Gemini no dio fórmula exacta, no reproducible en código).

## PARKED IDEAS
- **Futuros reales (CME) en vez de CFD Darwinex** — Alexander preguntó si convendría migrar para tener mejor calidad de dato (volumen real, libro de órdenes real, sin el proxy CFD que ya limitó VWAP y la hipótesis 003). Decisión: **no ahora** — no es un cambio de fuente de datos, es cambiar de bróker/infraestructura entera (otro modelo de margen, otro modelo de costos, otro feed), y todavía ninguna estrategia sobrevivió IS en el CFD actual como para justificar esa inversión. **Reconsiderar cuando** una hipótesis sobreviva IS+OOS en CFD — ahí futuros sería una etapa de confirmación adicional antes de capital real (encaja con la fase de incubación de la regla 15 de CLAUDE.md), no un reemplazo del pipeline actual.

## COORDINACIÓN #003 (2026-09-22) — ACTUALIZADO: spec entregada
Hipótesis 003 (SP500/D1, `oscillator_reversion`) escrita por `investigator`; `protocol` ya entregó spec+contrato ejecutable: `docs/specs/sp500-d1-rsi2-mean-reversion.md` + `.json` (ver sección "HIPÓTESIS #003 — SPEC GENERADA POR `protocol`" arriba para el detalle completo de parámetros, costos y baseline). Ya no está pendiente de `protocol` — el siguiente paso es invocar `engine` sobre ese contrato JSON.

## COORDINACIÓN #004 — US30 H1 CHANNEL BREAKOUT (2026-09-22)
Se registró la hipótesis #005 (`docs/hypotheses/us30-h1-channel-breakout.md`) y
se entregó su spec narrativa y contrato JSON en `docs/specs/`. Es una hipótesis
separada de #004: el momentum D1 `trend_cross` no se transformó artificialmente
en una ruptura de canal H1. Instrumento primario: US30/WS30; NAS100 y SP500
quedan como alternativas futuras, fuera de esta corrida. Parámetros fijados:
canal 24 barras, ATR14, SL 1.5 ATR, TP 3 ATR y time stop 24 barras, con riesgo
del 1%. No se ejecutó backtest ni se abrió OOS. H1 está permitido por
`CLAUDE.md`, `docs/universe.md` y `config/instruments.json`; quedan declaradas
las reservas actuales de `price_basis=unknown` y `costs_verified=false`.

## HIPÓTESIS #003 — VEREDICTO FINAL: DESCARTADA EN IS (2026-09-22)

`validator` cerró formalmente la hipótesis 003 (SP500/D1, RSI(2) Connors, familia `oscillator_reversion`) sobre `reports/factory/runs/a543fd86979556de4dfa743b/result.json`. **Decisión: DISCARDED_IS.** OOS no se abrió (nunca correspondía para una estrategia descartada en IS).

Números clave (detalle completo en `docs/hypotheses/_registry.md` fila 003): 148 operaciones, profit factor 1.12 (umbral 1.3, FAIL), P&L neto IS +$5,550 (positivo pero insuficiente), max drawdown 7.8% (única puerta adicional que pasa junto con mínimo de operaciones y net positivo). **Ratio de fricción 0.37 frente a un mínimo de 3.0** — financiación/swap es el 63% de los $14,920 de costos totales pagados, el componente dominante, no spread/slippage/comisión. Estrés de fricción ×2 lleva el resultado a -$9,283 neto (FAIL). Bootstrap de 2000 iteraciones: IC 95% del retorno medio [-6.8%, +14.1%] — **cruza cero**, p unilateral centrado = 0.213, ya por encima del piso mínimo resolvible de la campaña (`minimum_resolvable_adjusted_p`=0.1199) *antes* de corregir por ser la 3ª hipótesis probada (`p_campaign_bonferroni_upper_bound`=1 — cota trivial que no cambia nada). El diagnóstico por terciles temporales muestra el único tramo ganador entre 2012-07 y 2016-09 (PF 1.83); el resto de la muestra (2008-2012 y 2016-2021) es negativo o casi plano.

### Patrón tras 3 hipótesis seguidas descartadas en IS (001, 002, 003)

No hay una causa mecánica única compartida por las tres — no se inventa una donde no se ve:
- **001** (XAUUSD D1, `streak_reversal`): el edge bruto ya es negativo *antes* de costos (gross_pnl -$2,929). El mecanismo (reversión tras racha de 3 cierres) no está presente en el precio de XAUUSD D1 en esta muestra.
- **002** (NAS100 D1, calendario turn-of-month): el AED exploratorio (pre-motor real, indicativo no autoritativo) ya mostró que el efecto no aparece en los datos (p=0.633) — tampoco hay edge real, pero por una razón distinta (estacionalidad diluida, no mecánica de precio).
- **003** (SP500 D1, `oscillator_reversion`): esta sí tiene edge bruto real (+$19,397 antes de costos), pero es débil, temporalmente inestable (concentrado en un tercio de la muestra) y estadísticamente no distinguible de cero.

**Lo único verdaderamente común a las tres**: ninguna se acercó al ratio de fricción mínimo (≥3.0), ni siquiera la única con edge bruto genuino (003 llegó a 0.37, casi un orden de magnitud por debajo). Para operar en este bróker a holding D1, el listón real no parece ser solo "encontrar un edge de precio", sino uno lo bastante grande por operación (o con un patrón de holding que acumule menos financiación/swap) para sobrevivir una barra de costos donde la financiación domina (63% en 003, 32% en 001) muy por encima de spread+slippage+comisión. Segundo patrón parcial, más débil: en las dos hipótesis corridas por el motor real (001, 003), el resultado agregado no es estable en el tiempo — un tercio del período concentra lo mejor (o lo único bueno), los otros dos son negativos o casi nulos.

**Sugerencia para `investigator` antes de continuar con #004/#005** (ambas ya escritas y en estado `pendiente` en el registro — `us30-d1-time-series-momentum` y `us30-h1-channel-breakout` — no hace falta escribir una hipótesis nueva desde cero): antes de que `protocol`/`engine` inviertan un ciclo completo en cualquiera de las dos, conviene que la propia hipótesis razone explícitamente sobre la economía de fricción esperada (frecuencia de operaciones × costo de financiación del holding típico, no solo la lógica de comportamiento) — es el gate que ha reprobado peor las tres veces, independientemente de la familia o de si el edge de precio existe. No hay evidencia todavía de que el problema sea "familia de señal equivocada"; podría ser simplemente que el tamaño de edge necesario para este bróker/timeframe es mayor de lo que las hipótesis probadas hasta ahora asumían.

## NEXT ACTION (vigente, reemplaza la entrada anterior sobre #003)
1. **Hipótesis #003 cerrada** (`descartada_IS`, ver arriba). Decisión de Alexander: invocar `protocol`/`engine` sobre #004 (`us30-d1-time-series-momentum`) o #005 (`us30-h1-channel-breakout`) — ambas ya tienen spec escrita, ninguna corrida todavía —, o pedirle primero a `investigator` que revise la economía de fricción de ambas contra el patrón de arriba antes de gastar el ciclo completo de nuevo.
2. Sin relación directa: sigue pendiente la decisión de Alexander sobre archivar formalmente la hipótesis #002 o pasarla a `validator` para veredicto formal (no bloquea el punto 1).
3. Estado real del proyecto: **3 de 3 hipótesis probadas hasta ahora descartadas en IS, cero estrategias vivas, cero aperturas de OOS.**

## LAST UPDATED
2026-09-22 (protocol entrega spec y contrato de hipótesis #006, DAX/GDAXI H4, familia trend_cross; no se ejecutó backtest ni se abrió OOS)

## CENTRO DE CONTROL Y REGISTRO ESTRUCTURADO (2026-09-22)

Se añadió un Centro de Control local (`python -m qaf.cli dashboard`; snapshot con `--snapshot`) que muestra contratos, estado de hipótesis, causa del último resultado, siguiente acción, tareas/eventos y enlaces a reportes. La fuente estructurada de hipótesis es ahora `config/hypotheses.json`; el Markdown se conserva para lectura humana. `check-spec`, `register` y el runner validan los IDs contra este catálogo.

Corrección operativa: el runner solo ejecuta hipótesis con estado `pending` o `ready`. Las descartadas, bloqueadas o rechazadas permanecen visibles, pero no vuelven a ejecutarse cuando cambia el hash del código. La verificación real posterior al cambio ejecutó 0 ensayos nuevos, por lo que no consumió otro intento de campaña. Las hipótesis 004 y 006 se sincronizaron como `discarded_is` según sus resultados ya existentes.

Auditoría de skills: el único skill local es `.claude/skills/data-quality-check/SKILL.md`; se actualizó para usar `config/instruments.json` y los artefactos reales de `qaf` como fuentes autoritativas. Los skills globales de productividad, Pine Script, documentos o análisis se mantienen fuera del motor y se invocan solo cuando su tarea lo exige. Detalle: `docs/SKILLS_AUDIT.md`.

## COORDINACIÓN #006 — DAX H4 TIME-SERIES MOMENTUM

`protocol` entregó `docs/specs/dax-h4-time-series-momentum-replication.md` y
su contrato JSON. La hipótesis #006 se consideró semánticamente admisible
frente a #004: mantiene el mecanismo y la familia, pero cambia de US30 D1 a
DAX H4 como replicación cross-asset/cross-timeframe preespecificada. Se
tradujo a `trend_cross` con SMA20/SMA60, ATR14, SL 2 ATR, TP 4 ATR y time
stop de 20 barras; dirección larga y corta y riesgo de 0.5% por operación.

El instrumento `DAX` existe en `config/instruments.json`, está en
`status=research` y declara H4. La spec hereda las reservas de Gate 0
(`price_basis=unknown`, `costs_verified=false`, spread/slippage y dividendos)
sin bloquear la escritura; `validator` no puede aprobar mientras
`costs_verified` sea falso. El baseline obligatorio es comprar y mantener
del mismo DAX H4, neto de los costos del instrumento. No se ejecutó código,
backtest, optimización ni se abrió OOS.

## COORDINACIÓN #004 — US30 D1 TIME-SERIES MOMENTUM

`protocol` entregó `docs/specs/us30-d1-time-series-momentum.md` y su contrato
JSON. La hipótesis quedó traducida a `trend_cross` con SMA20/SMA60, ATR14,
SL 2 ATR, TP 4 ATR y time stop de 20 barras; dirección larga y corta y riesgo
de 0.5% por operación, conforme al default de `config/runner.json`.

La spec documenta la limitación: el motor no implementa retorno acumulado ni
salida por cruce contrario, por lo que esta prueba no es una réplica exacta de
la literatura de time-series momentum. No se añadió una familia nueva ni se
duplicó la hipótesis. El instrumento `US30` existe en
`config/instruments.json`, está en `status=research` y declara D1. Se heredan
las reservas de Gate 0 (`price_basis=unknown`, `costs_verified=false`) sin
bloquear la escritura; `validator` no puede aprobar mientras `costs_verified`
sea falso. No se ejecutó código, backtest ni se abrió OOS.

## C2 IMPLEMENTADO — PUERTA DE BASELINE DENTRO DE `qaf` (2026-09-22, esta sesión)

Alexander pidió corregir lo que la auditoría de GPT (`docs/audit_qaf_complete_2026-09-22.md`) marcó como necesario, sin tocar archivos que GPT tuviera abiertos. Confirmé por `git status`/`git diff` que GPT estaba trabajando en `qaf/cli.py`, `io.py`, `registry.py`, `runner.py` (parte de `run_daily`) y `tests/test_factory.py` (que referencia `qaf/dashboard.py`, también en progreso) — así que implementé **C2 (puerta de baseline)** en archivos nuevos o en partes de archivos que GPT no tocó:

- **`qaf/baseline.py` (nuevo)**: `simulate_baseline()` reutiliza literalmente `execution_cost`/`financing`/`price_cash` de `qaf/costs.py` — mismo ledger exacto que `qaf.engine.simulate`, no una reimplementación paralela. 1 lote fijo (no sizing por riesgo, para aislar "la regla es mejor que nada" del tamaño de posición), entra al open de la primera barra, mark-to-market hasta el close de la última, sin señal/SL/TP/time-stop — la definición de comprar y mantener. Verificado contra `data/clean/{SP500,EURUSD,XAUUSD}/D1/IS.parquet` reales.
- **`qaf/validation.py`**: `screening_gates()` gana un parámetro `baseline_metrics=None` (compatible hacia atrás — `tests/test_factory.py` todavía llama con la firma vieja de 5 argumentos, ahí no se rompe nada) y una puerta `beats_baseline`: exige `estrategia > 0 Y estrategia > baseline` — perder menos que un baseline ya negativo no aprueba (regla 19 de CLAUDE.md, "el piso no es cero").
- **`qaf/runner.py`** (solo la función `execute`, que GPT no tocó — su trabajo fue en `run_daily`): calcula el baseline y lo pasa a `screening_gates` y al `record` de cada corrida.
- **`qaf/reporting.py`**: la sección "Comparador" del reporte HTML ya no dice el texto fijo "B&H no calculado" — ahora muestra el baseline real y si la estrategia lo superó.
- **`tests/test_baseline.py` (nuevo, no toca `test_factory.py`)**: 8 tests — reconciliación del ledger, cálculo bruto correcto con `tick_size`, recómputo independiente llamando a `costs.py` directo (no solo confía en `baseline.py`), corto invierte dirección y usa `swap_short`, validación de entradas, puerta falla si no supera baseline, puerta falla si la estrategia es negativa aunque pierda menos que el baseline, y compatibilidad hacia atrás sin `baseline_metrics`. Los 8 pasan (`pytest tests/test_baseline.py`, aislado de `test_factory.py` que hoy no colecciona).

**Hallazgo real al verificar** (no un ajuste cosmético): el baseline de comprar-y-mantener sobre datos reales es **más negativo** que lo reportado el turno anterior — `qaf.baseline` aplica el multiplicador de swap triple en el día exacto de la semana (via `qaf.costs.financing`, que ya lo tenía implementado correctamente), mientras que el script suelto de antes (`scripts/dryrun_bh.py`) contaba "1 cargo por barra" sin ese multiplicador. Nuevos números sobre IS completo D1: SP500 -24,102.62 (antes -11,062.16), EURUSD -34,705.14 (antes +431.50 — **cambia de signo**), XAUUSD -353,227.25 (antes -213,786.95). El hallazgo de fondo (holding largo en CFD es caro) se refuerza, no cambia de dirección salvo en EURUSD, que ahora también es negativo.

**Verificación end-to-end sin tocar estado compartido**: corrí `execute()` sobre la spec real `config/strategies/00196adf527efa117f6bc53c.json` (hipótesis #004, US30) en una carpeta temporal aislada — no escribió en `reports/factory/` ni en `state/research.sqlite3` (evité correr `qaf.cli run` completo por el riesgo de colisión con lo que GPT pudiera estar escribiendo ahí mismo). Resultado: `DISCARDED_IS`, la puerta `beats_baseline` aparece y falla correctamente (estrategia -7,929.87 > baseline -14,063.30, pero al ser negativa igual no pasa).

**No implementado (fuera de este alcance, sigue en la lista de la auditoría):** C1 (AED), C3 (freeze/OOS, deliberadamente bloqueado en `holdout.py`), C4 (costos históricos reales). `qaf/holdout.py` no se tocó.

**Pendiente de decisión de Alexander**: no hice commit — hay trabajo sin commit de GPT en curso (`qaf/dashboard.py`, `docs/CONTROL_CENTER_ROADMAP.md`, catálogo `config/hypotheses.json`). Recomiendo commitear cuando ambos flujos estén en un punto estable, no a mitad de la edición de GPT.

## C1 IMPLEMENTADO — AED (CONFIRMACIÓN ESTADÍSTICA DE LA SEÑAL ANTES DEL BACKTEST) (2026-09-22, esta sesión)

Alexander pidió seguir con C1 después de revisar el orden de fases del pipeline (flowchart pegado en el chat). Reconfirmé por `git status`/`git diff` antes de tocar nada: el diff existente en `validation.py`/`runner.py`/`reporting.py` resultó ser mi propio trabajo de C2 sin commitear, no de GPT — GPT solo había tocado `registry.py`/`cli.py`/`io.py` y la función `run_daily()` de `runner.py` (tracking de tareas). Cero colisión.

- **`qaf/aed.py` (nuevo)**: `permutation_test(df, spec, policy)` — toma la señal cruda de `qaf.signals.generate` (la misma que usa `qaf.engine.simulate`, sin costos/SL/TP/sizing) y prueba H0: "el momento en que dispara la señal no aporta información sobre el retorno direccional futuro". Fija el número y la mezcla de direcciones de señales observadas, aleatoriza en qué barras caen (permutación de temporalidad), y compara contra el retorno direccional medio observado. `horizon_bars` reutiliza `spec['parameters']['max_holding']` — ya validado por `contracts.py`, cero parámetros libres nuevos que se pudieran ajustar después de ver el resultado. Con menos de 20 señales crudas en la ventana IS, devuelve `INCONCLUSIVE` en vez de forzar un resultado con muestra insuficiente.
- **`qaf/validation.py`**: `diagnose()` ya no deja `permutation_test` como stub fijo `NOT_EXECUTED` — llama a `aed.permutation_test()` de verdad. `screening_gates()` gana la puerta `aed_pattern_confirmed` (exige `p_value_one_sided < 0.05`, el umbral que la regla dura 5 de CLAUDE.md ya pedía por defecto y que nunca estaba implementado). Solo se activa si `diagnostics` trae un `permutation_test` con `status: EXECUTED` real — ausente, `INCONCLUSIVE` o el viejo stub `NOT_EXECUTED` hacen que la puerta se omita (no finge PASS ni bloquea sola), igual que el patrón ya usado para `beats_baseline`.
- **`tests/test_aed.py` (nuevo, no toca `test_factory.py`)**: 6 tests — detecta un efecto direccional real y repetido construido a propósito (dataset sintético con breakout + continuación de 3 barras + meseta, p<0.05), reporta `INCONCLUSIVE` con pocas señales, rango de p-valor válido sobre un random walk, puerta PASS/FAIL correctos, y puerta omitida (no rompe compatibilidad) cuando `permutation_test` está ausente o `INCONCLUSIVE`. Los 6 pasan, y los 8 de `test_baseline.py` siguen pasando (14/14 total).

**Verificación end-to-end real**: corrí `execute()` sobre la misma spec real `config/strategies/00196adf527efa117f6bc53c.json` (US30 D1, hipótesis #004) en una carpeta temporal aislada, con los datos reales de `data/clean/US30/D1/IS.parquet` (3389 filas) y la política real de `config/runner.json` (2000 iteraciones de bootstrap/permutación). 0.49s de ejecución total. Resultado: sigue `DISCARDED_IS`, y ahora con evidencia directa de que nunca hubo señal — `aed_pattern_confirmed` FALLA (p=0.61, retorno direccional medio observado ligeramente NEGATIVO, -0.0015). Antes solo sabíamos que la estrategia perdía dinero después de costos; ahora sabemos que el cruce SMA20/SMA60 de US30 D1 no tiene ventaja direccional cruda ni antes de aplicar ningún costo.

**También verificado sin dañar nada existente**: `tests/test_factory.py` ya colecciona (antes fallaba por `ModuleNotFoundError: qaf.dashboard`, que GPT resolvió creando ese archivo) — 28/43 tests pasan ahí; los 15 restantes fallan por un `PermissionError` de Windows en el directorio temporal de pytest (`pytest-of-keysi`), un problema de entorno/concurrencia no relacionado con este cambio (probablemente otra sesión corriendo pytest al mismo tiempo).

**No implementado (sigue en la lista de la auditoría):** C3 (freeze/OOS, deliberadamente bloqueado en `holdout.py`), C4 (costos históricos reales, no solo el snapshot actual). `qaf/holdout.py` no se tocó.

**Pendiente de decisión de Alexander**: mismo estado que C2 — no hice commit, hay trabajo de GPT sin commitear en curso.

## ENCARGO DE COPILOT AUDITADO E IMPLEMENTADO — FILTRO IS FAIL-CLOSED (2026-09-22 16:10, Claude app escritorio)

Detalle completo: `docs/implementation_report_2026-09-22.md`. Coordinación entre agentes: `AGENTS.md` (nuevo "cerebro" con tablero de reclamos; `CLAUDE.md` lo importa y `.github/copilot-instructions.md` lo exige a Copilot).

**Estado real ahora:**
- Todas las puertas IS son obligatorias y fallan cerradas: un diagnóstico ausente es `FAIL`, una puerta `INCONCLUSIVE` deja la decisión en `INCONCLUSIVE` (antes el AED `INCONCLUSIVE` se omitía en silencio).
- AED (`qaf/aed.py`) usa permutación por rotación circular: calibrada ~4% de rechazos a α=5% sobre random walks; el diseño anterior daba 8.5%.
- Baseline (`qaf/baseline.py`) con el mismo capital invertido 1x y liquidación por insolvencia; ya no 1 lote fijo.
- Sensibilidad por parámetro ±10/20% + 200 vecinos Montecarlo (regla 14), con puerta `parameter_sensitivity` (umbrales provisionales: percentil ≤0.8, ≥50% vecinos rentables).
- Time-stop: el punto 4 del encargo (aplicar time-stop "si no se tocó stop/target intrabar") era look-ahead y **no se implementó**. Sí se corrigió que un gap a través del target en la barra límite se pagaba al open (optimista) en vez del target.
- Las 28 particiones de `data/clean/manifest.json` están selladas (sha256 IS/OOS, esquema, rangos); `load_is` verifica ambos hashes en cada corrida. OOS nunca se parsea en el flujo IS.
- `qaf/holdout.py` sigue cerrado con 7 prerrequisitos explícitos; `diagnostics.walk_forward = NOT_IMPLEMENTED`.
- `python -m qaf.consistency`: registros de hipótesis coherentes (0 divergencias).
- Tests: **99 pasados, 0 fallidos** (`--basetemp` propio; el `PermissionError` anterior era concurrencia de pytest entre agentes).

**Corrida real IS de las 5 estrategias registradas (carpeta temporal):** todas siguen `DISCARDED_IS`; ninguna señal cruda supera la permutación (p entre 0.11 y 0.99). La 003 (SP500 RSI2) además es ganadora aislada en su vecindad (percentil 0.92). El baseline con mismo capital queda **insolvente en las 5 series (≈ -100.5k)**, en buena parte por C4 (swap actual en efectivo por lote aplicado a precios históricos bajos): no cambia decisiones, pero el baseline no es referencia fina hasta resolver C4.

**Otro agente activo en paralelo:** la orden de Copilot para detener su agente delegado falló; siguió editando (`catalog.py`, `dashboard.py`, `test_factory.py`, este archivo, y una vez `tests/test_aed.py` — cambio correcto, conservado). Creó la hipótesis 007 (KAMA XAUUSD D1), sin spec todavía.

**NEXT ACTION:** Alexander decide (1) si el baseline con mismo capital y los umbrales de sensibilidad quedan como criterio; (2) cuándo commitear este lote junto con el de GPT. Después: C4 (costos históricos), que hoy distorsiona el baseline más que cualquier otra cosa.

## ORQUESTACIÓN DETERMINISTA DE FASES (2026-09-22 16:40, Claude app escritorio)

Origen: revisión de Copilot sobre el diseño de los 4 agentes, auditada contra el repo. Válida en sus 4 puntos accionables; de acuerdo con no agregar agentes (optimizer/sizing/deploy) hasta tener walk-forward y OOS.

- **`qaf/pipeline.py` (nuevo)**: controlador de solo lectura, no un quinto agente. Deriva de los artefactos la fase de cada hipótesis y el único agente al que le toca (`NEEDS_HYPOTHESIS_DOC` → investigator, `NEEDS_SPEC` → protocol, `NEEDS_REGISTRATION`/`NEEDS_IS_RUN` → engine, `NEEDS_VALIDATOR_REVIEW` → validator, `RUNNING` → nadie, `INCONSISTENT`/`BLOCKED`/`NEEDS_DECISION` → Alexander, `CLOSED`). Vínculo por contenido: `digest(spec)` = estrategia registrada, `canonical(spec)` = corridas en SQLite; una spec editada después de registrar se detecta sola. `python -m qaf.pipeline --hypothesis <id> --as <agente>` devuelve 0 (permitido) o 3 (detenerse). `CLAUDE.md` obliga al hilo principal a consultarlo antes de invocar cualquier agente; `engine`/`validator`/`investigator` lo corren como paso 0; `protocol` (sin Bash) exige que quien lo invoque lo haya confirmado.
- **Estado real hoy**: 007 (KAMA XAUUSD D1) en `NEEDS_SPEC` → protocol (coincide con la tarea `protocol:007` en cola); 002 `BLOCKED` → Alexander; 001, 003–006 `CLOSED`. Una advertencia histórica: la estrategia registrada de la 001 (`dd17…`) no tiene contrato JSON de protocol en `docs/specs` (se creó antes de que existiera ese formato); no bloquea porque la hipótesis está cerrada.
- **`investigator.md`**: el `description` (lo que usa Claude Code para decidir cuándo invocarlo) decía "diario o 4H"; ahora H1, H4 o D1. Tomado del reclamo de GPT con autorización de Alexander, registrado en `AGENTS.md`.
- **`READY_FOR_FROZEN_VALIDATION`**: el reporte HTML/MD de cada corrida muestra el significado de cada decisión ("lista para ENTRAR en validación congelada… no es una estrategia validada"); también en `validator.md`, `CLAUDE.md` y `docs/architecture.md`.
- **`AGENTS.md`**: la fila de GPT pasa de DESCONOCIDO a INACTIVO desde 16:01 (sin ediciones; no confirmado por el propio agente).
- Corrección menor: `qaf.partition.seal` ya no reescribe el manifest cuando no sella nada.
- Tests: **121 pasados, 0 fallidos** (22 nuevos en `tests/test_pipeline.py`).

**NEXT ACTION:** igual que arriba — decisión de criterios y commit. Para avanzar la 007: invocar `protocol` (el controlador ya lo permite).

## ESTABILIZACIÓN OPERATIVA Y POLÍTICA DE OPTIMIZACIÓN (2026-09-22 16:49, Codex app escritorio)

- Se auditó la orquestación de Claude: `qaf.pipeline` es consistente, deja 007 en `NEEDS_SPEC → protocol`, 002 bloqueada y el resto cerrado. La ausencia histórica del contrato JSON de 001 permanece como advertencia no bloqueante.
- El tablero Markdown ya no es el mecanismo de exclusión. `qaf.coordination` usa SQLite, transacción `BEGIN IMMEDIATE` y clave única por ruta: una reclamación conflictiva no adquiere ningún archivo; hay heartbeat, vencimiento a 120 minutos, recuperación auditada y liberación con resultado.
- `qaf.preflight` reúne fuentes obligatorias, coherencia de hipótesis, controlador de fases, reservas, estado git y crecimiento de la bitácora. `PROJECT_STATE.md` queda explícitamente como historial; no se usa para inferir el estado vigente.
- `docs/OPERATIONS.md` fija el ciclo de agentes y el proceso de investigación/optimización: spec congelada antes del backtest, sensibilidad solo diagnóstica, ningún vecino sustituye la spec, cualquier cambio posterior cuenta como hipótesis nueva y OOS nunca retroalimenta IS.
- Decisiones pendientes resueltas: baseline de igual capital 1x se conserva como costo de oportunidad absoluto (estrategia positiva y por encima del baseline; no se afirma que esté ajustado por riesgo). Los umbrales de sensibilidad quedan versionados en `config/runner.json`: 200 vecinos, rango ±20%, mínimo 100 válidos, percentil original ≤0.80 y ≥50% de vecinos rentables. Solo pueden cambiarse antes de una campaña nueva, nunca para rescatar un resultado.
- Se añadió workflow de verificación para GitHub y se corrigió el mensaje obsoleto de `qaf.runner` para apuntar a `config/hypotheses.json`.
- Verificación: compilación Python correcta; **131 pruebas aprobadas / 0 fallidas**; consistencia 0 errores; pipeline 0 violaciones bloqueantes. Preflight `WARN` únicamente por la advertencia histórica 001, la bitácora larga y **67 cambios sin consolidar**. Sin commit.

**NEXT ACTION:** consolidar este lote en un commit cuando Alexander lo autorice. Después, `protocol:007`; OOS continúa cerrado por `docs/VALIDATION_ROADMAP.md`.

## CONSOLIDACIÓN AUTORIZADA (2026-09-22)

Alexander autorizó consolidar el lote completo. Se repitieron las **131 pruebas (todas aprobadas)**, se revisaron los 68 archivos preparados, se corrigieron únicamente advertencias de whitespace documental y se creó un único commit local. No se hizo push. El working tree quedó limpio; el siguiente paso operativo vuelve a ser `protocol:007`.

## PROTOCOL 007 — SPEC CONGELADA Y BLOQUEADA (2026-09-22 17:40, Claude-app)

Preflight `qaf.pipeline --hypothesis 007 --as protocol` → PERMITIDO; reserva atómica de los archivos exactos; tarea SQLite `protocol:007` marcada running mientras duró el trabajo.

- La fuente primaria registrada (Oxford, verificada dos veces hoy) **no declara** los valores base de `ER_Length` ni `FastMA_Length` (solo rangos de sensibilidad [2,100] y [2,28]) ni ninguna salida distinta del stop 6×ATR(20). Su muestra 1980-2011 se solapa con ~2/3 del IS de XAUUSD (1998-2018), así que tomar valores de sus gráficos sería seleccionar por resultados.
- `qaf` no implementa familia KAMA ni salida por señal opuesta. El contrato previsto, validado en memoria, falla con `validate_spec`: "Familia no implementada"; forzarlo en cualquiera de las 4 familias existentes también falla (falta `max_holding`).
- **Creado**: `docs/specs/xauusd-d1-kama-tendencial-con-efficiency-ratio.md` (agente `protocol`, auditado): congela fórmulas ER/AMA, pivotes, filtro 0.01·σ(ΔAMA,20), entrada larga/corta como condición de estado, stop fijo 6×ATR(20), riesgo 1%, fill causal al open siguiente, costos XAUUSD, 9 convenciones de implementación y la tabla de contrato previsto con los PENDIENTES. **No se creó el JSON.**
- **Registro**: 007 → `blocked_architecture` (`RULES_UNDERSPECIFIED_AND_FAMILY_NOT_IMPLEMENTED`) en `config/hypotheses.json` y en su espejo; pregunta `kama-kaufman-valores-base-y-salida` en `docs/research_queue.md`; tarea `protocol:007` cerrada como `blocked`.
- Verificación: `qaf.pipeline` → 007 `BLOCKED` (le toca a Alexander); `qaf.consistency` sin errores; suite completa **131 pasados, 0 fallidos**. Sin backtest, sin OOS, sin cambios de código, sin commit.
- Pendiente menor: `docs/hypotheses/xauusd-d1-kama-tendencial-con-efficiency-ratio.md` (documento de investigator) sigue diciendo "Estado: pendiente de protocolo"; el estado autoritativo es `config/hypotheses.json`.

**NEXT ACTION (Alexander):** conseguir la evidencia de Kaufman para ER_Length/FastMA_Length/salida (o decidir aceptar una fuente secundaria) y decidir si se implementa la familia KAMA. Hasta entonces no hay hipótesis ejecutable en cola.
## 2026-09-22 — Revisión de evidencia Donchian + Efficiency Ratio

- `IDEA-PILOT-DONCHIAN-ER-DAX` quedó `rejected` con `EXACT_RULE_NOT_VERIFIED`.
- La fuente confirma ambos conceptos por separado, pero no una regla combinada reproducible con ventanas, umbral, salida y sizing definidos.
- No se creó hipótesis, contrato ni backtest. Reabrir exige una fuente primaria que documente la combinación completa.

## 2026-09-22 — Catálogo versionado y extracción periódica

- El catálogo canónico pasó de `state/catalog/` (ignorado por Git) a `catalog/candidates/`; se migraron sin cambios semánticos los tres pilotos existentes. `state/` queda solo para colas SQLite, reservas y cachés.
- `qaf.source_sync` implementa cosecha manual por lotes desde arXiv, Crossref y metadatos de archivos de QuantConnect LEAN. No descarga PDFs, no copia ni ejecuta código externo y fija las referencias GitHub a un commit SHA exacto.
- Cada observación externa produce un snapshot inmutable en `catalog/discoveries/` con SHA-256 calculado sobre sus metadatos canónicos. Se deduplica por DOI, URL o repositorio/ruta.
- La primera observación crea un candidato `captured` y una tarea para `investigator`. Una revisión posterior de la fuente nunca sobreescribe el expediente: crea otro snapshot y una tarea `evidence_refresh`.
- La frontera está aplicada en código y pruebas: discovery no crea hipótesis, contratos, estrategias, reportes ni backtests. Quantpedia, Alpha Architect, SSRN y Qlib permanecen manuales/deshabilitados.
- Prueba real `--dry-run --limit 1`: arXiv, Crossref y GitHub respondieron correctamente; no se escribió ningún artefacto. Suite completa: **137 pasados / 0 fallidos**.

**NEXT ACTION:** ejecutar `python -m qaf.cli source-sync --limit <N>` solo cuando se quiera refrescar la cantera. Cada candidato nuevo queda en revisión; no avanzar OOS hasta resolver costos, `price_basis`, contrato congelado y walk-forward.

## REVISIÓN DE SOURCE-SYNC (2026-09-22 19:40, Claude-app, sobre el lote sin commit de Codex)

Alexander pidió revisar lo integrado por Codex antes de que se le acabaran los tokens. Se verificó con consultas reales de solo lectura y reproducciones en carpeta temporal; no se ejecutó ninguna extracción que escriba.

**Correcto y conservado:** catálogo canónico en `catalog/candidates/` (los 3 pilotos migrados son idénticos a sus copias en `state/catalog/`), lectura de respaldo de la ubicación antigua, sin ejecución de código externo, sin promoción ni backtest automáticos, dry-run, reintentos con espera, commits de GitHub fijados.

**Errores encontrados y corregidos (`qaf/source_sync.py`, `config/source_providers.json`):**
1. arXiv: una versión nueva de un paper (v1→v2) creaba un segundo candidato. Ahora la identidad es el ID sin versión y la versión nueva genera `evidence_refresh`.
2. GitHub: un cambio real de contenido de un archivo se contaba como "duplicado" y se descartaba; además cada commit del repo habría cambiado la identidad. Ahora la identidad es `repo:ruta` y el cambio se detecta por `blob_sha`; un commit que no toca el archivo no genera tarea.
3. Crossref ordenado por fecha devolvía 10/10 registros ajenos (marketing, medicina, "Title Pending", fechas 2036-2115). Ahora: relevancia, `until-pub-date` = hoy, `type:journal-article`, y descarte de fechas futuras → 25/25 papers de trading en la prueba real. `access_level` pasa a `unknown` (un DOI no garantiza acceso abierto).
4. LEAN: la regex capturaba 423 de 460 archivos (236 son pruebas de regresión). Ahora `include_regex` de palabras de estrategia + `exclude_regex` de regresiones/opciones → 10 archivos de estrategia, 0 regresiones.
5. `.claude/agents/investigator.md` seguía diciendo que las ideas llegan a `state/catalog/`; ahora apunta a `catalog/candidates/` y explica qué es un descubrimiento `unverified_discovery`.

Huella nueva: `metadata_sha256` excluye `source_url` y `source_revision`. No había candidatos `IDEA-SRC-*` todavía, así que no hay datos previos que migrar. Documentado en `docs/CATALOG_AUTOMATION.md` (tabla de identidad por conector y calidad de fuentes).

**Verificación:** 4 pruebas nuevas en `tests/test_source_sync.py`; suite completa **141 pasados / 0 fallidos**, sin advertencias; `source-sync --dry-run --limit 5` crearía 15 candidatos y no escribió nada; preflight sin errores. Sin commit.

**Pendiente para GPT/Codex** (anotado también en `AGENTS.md`): `--limit` no pagina (GitHub siempre devuelve los mismos archivos en orden alfabético); Crossref puede traer el mismo trabajo con varios DOI; `state/catalog/` conserva copias antiguas idénticas, que no se borraron.

**NEXT ACTION:** Alexander decide cuándo consolidar en un commit este lote (Codex + 007 + esta revisión) y cuándo correr la primera extracción real pequeña (`source-sync --limit 5`, hasta 15 candidatos).

## COMMIT + DUPLICADOS DE CROSSREF (2026-09-22 19:40, Claude-app)

- Alexander autorizó el commit: `fca47a1` consolida el lote de Codex (catálogo versionado, source-sync), la spec bloqueada de la 007, la revisión de evidencia Donchian-ER y la revisión de source-sync. 141 pasados / 0 fallidos antes del commit.
- Resuelto el pendiente "mismo trabajo con varios DOI": `qaf/source_sync.py::_work_key` (título normalizado de 4+ palabras + apellido del primer autor). El candidato nuevo se crea igual y lleva `provenance.possible_duplicate_of`; nunca se descarta, porque título + autor puede colisionar. Contador `possible_duplicates` en el resumen. 1 prueba nueva; suite **142 pasados / 0 fallidos**. Dry-run real `--limit 25`: crearía 60 candidatos, 0 posibles duplicados, sin escrituras.
- Aclarado el pendiente de paginación: `--limit` ≤ 200 cabe en una sola petición; lo que falta es un cursor entre corridas (los trabajos nuevos fuera del top N no se ven nunca). Queda para GPT/Codex como decisión de diseño.
- `state/catalog/` conserva las copias antiguas; no se borraron (borrar es decisión de Alexander).

**NEXT ACTION:** Alexander decide cuándo correr la primera extracción real (`source-sync --limit 5`, hasta 15 candidatos). La 007 sigue bloqueada hasta tener la evidencia de Kaufman (`docs/research_queue.md`).
