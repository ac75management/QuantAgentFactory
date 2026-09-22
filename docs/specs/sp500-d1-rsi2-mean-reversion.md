# Spec: sp500-d1-rsi2-mean-reversion

tipo: estrategia candidata (hipótesis #003 de `docs/hypotheses/_registry.md`)
hipótesis origen: `docs/hypotheses/sp500-d1-rsi2-mean-reversion.md`
estado: spec generada por `protocol` — pendiente de Gate 0 / AED / backtest (`engine`), no aprobada ni rechazada aquí.

## Honestidad de mecanismo (recordatorio obligatorio, no se repite como si fuera nuevo)

Esta spec traduce a reglas numéricas la versión **debilitada y genérica** del mecanismo de Connors que la hipótesis ya declaró explícitamente: "reversión de precio tras sobreventa extrema medida por RSI en el índice", no la mecánica completa de capitulación retail + recompra institucional alrededor del cierre real de acciones (MOC) que describe la fuente original. Un CFD de índice de Darwinex no reproduce esa microestructura (`price_basis: "unknown"`, `calendar_verified: false` en `config/instruments.json`). Un resultado positivo en AED/backtest confirma (o no) esta hipótesis débil — no la evidencia completa de Connors sobre el S&P 500 real. Ver `docs/hypotheses/sp500-d1-rsi2-mean-reversion.md` sección "El matiz honesto" para el desarrollo completo; no se reproduce aquí en extenso.

## 0. Evaluación de costos (por qué esta spec no está bloqueada, con reservas explícitas)

`docs/universe.md` fila 11 / `config/instruments.json`: `alias=SP500`, `symbol_mt5=SP500`, `asset_class=index_cfd`, `timeframes=["H1","H4","D1"]`, `status=research`. D1 está dentro del alcance (CLAUDE.md: diario o 4H mínimo). Datos limpios IS/OOS confirmados en disco: `data/clean/SP500/D1/{IS,OOS}.parquet`.

Campos de costo citados textualmente de `config/instruments.json` (SP500):

| campo | valor | status |
|---|---|---|
| `spread_points` | 6 | real (Sección LIVE, snapshot `docs/cost_snapshots/20260922_1122.json`), pero **floating** — foto puntual, no distribución histórica |
| `slippage_points_per_side` | 1.5 | **SIN_CONFIRMAR** (`costs_verified: false`) — escenario, no histórico |
| `commission_type` / `commission_per_side` | `cash` / 0.275 USD/contrato/lado | **CONFIRMED** (2026-09-22, `docs/cost_model.md` tabla "Por símbolo", cruzado con tabla pública Darwinex `forex-cfds/indices`) |
| `swap_long` / `swap_short` | -11.03 / +4.58 (USD/noche/lote) | real (Sección LIVE, cuenta real) |
| `swap_schedule` / `triple_weekday` | `triple` / 4 (viernes) | **CONFIRMED** — índices usan viernes ×3, no miércoles (`docs/cost_model.md`, hallazgo `swap_rollover3days`) |
| `contract_size` / `tick_value` / `tick_size` / `point` | 10.0 / 1.0 / 0.1 / 0.1 | real (Sección LIVE) |
| `rollover_timezone` / `rollover_time` | `America/New_York` / `17:00` | real (Sección LIVE) |
| `price_basis` | `unknown` | **RESERVA** — Gate 0 debe evaluarlo, no se asume mid sin confirmación |
| `calendar_verified` | `false` | **RESERVA** |

**Conclusión**: comisión y día de swap triple están `CONFIRMED` para SP500 (igual que para todo el universo activo, `docs/cost_model.md`). Los campos abiertos son `spread_typical_points`/`spread_stress_mult` (variabilidad real del spread, no un hueco de dato) y `slippage_points_per_side` (escenario, nunca publicado por el bróker). Igual que en la spec de la hipótesis 001 (XAUUSD), esta reserva **no bloquea** escribir la spec — se traslada aguas abajo con el mismo techo ya construido en el pipeline:
- Gate 0 no puede declarar mejor que `APTO_CON_RESERVAS` mientras `slippage_points_per_side`/spread-modelo sigan sin confirmar (`.claude/skills/data-quality-check/SKILL.md`).
- `validator` no puede emitir aprobación final sobre ese veredicto sin confirmación explícita de Alexander (CLAUDE.md regla 20, `INVALID_POR_DATOS` como alternativa a `RECHAZADA`).
- El ratio de fricción mínimo (sección 5) se mantiene en 3.0 sin relajar.

Adicionalmente, esta familia (`oscillator_reversion`) genera señales con más frecuencia que `streak_reversal`/`trend_cross` (la hipótesis ya lo señala en su justificación de elegir SP500 sobre NAS100 por menor fricción estructural) — cada entrada nueva paga fricción completa, así que un slippage mal calibrado pesa más acumulativamente aquí que en las hipótesis 001/002. Esto no es motivo para bloquear la spec, pero sí para que `engine`/`validator` traten el conteo de operaciones y el costo acumulado con más atención que en las hipótesis previas.

## 1. Activo y timeframe

- alias: **SP500** (`config/instruments.json` → `symbol_mt5=SP500`, `asset_class=index_cfd`, `status=research`)
- timeframe: **D1**
- Dentro de alcance CLAUDE.md (CFD, diario, no scalping/HFT, no rebalanceo de cartera).
- No se extiende a H1/H4 ni a NAS100/US30/DAX — cualquier extensión es una hipótesis nueva, no esta spec.

## 2. Regla de entrada (numérica, sin ambigüedad)

Familia `oscillator_reversion` (`qaf/signals.py::generate`, `qaf/contracts.py::FAMILIES`). Sobre `close` de barras D1 (precio de referencia: **mid** — ver sección 4, pendiente de confirmación formal por Gate 0):

1. **RSI de Wilder** de periodo `rsi_period` sobre `close` (`qaf/signals.py::rsi` — implementación causal, `result[i]` depende solo de barras `<= i`, sin look-ahead).
2. **Filtro de tendencia**: `SMA(trend_filter_sma)` sobre `close`.
3. **Señal LARGA** en la barra `t` si `RSI[t] < entry_threshold` **Y** `close[t] > SMA[t]` (sobreventa extrema dentro de un régimen de tendencia de fondo alcista).
4. **Señal CORTA** en la barra `t` si `RSI[t] > 100 - entry_threshold` **Y** `close[t] < SMA[t]` (simétrico invertido: sobrecompra extrema dentro de un régimen de tendencia de fondo bajista).
5. Máximo 1 posición abierta a la vez en esta estrategia/símbolo (comportamiento del motor `qaf.engine.simulate`, no específico de esta spec). Mientras haya una posición abierta, cualquier señal nueva (misma dirección u opuesta) se descarta — no hay pirámide ni inversión de posición.
6. A diferencia de la hipótesis #001 (racha de 3 días, evento puntual), el RSI puede permanecer por debajo de `entry_threshold` varias barras seguidas — cada barra en la que la condición se cumple y no hay posición abierta genera una señal nueva evaluable (no hay deduplicación adicional más allá de la restricción de una sola posición abierta del punto 5).

### Valores fijos (no son parámetros libres — ver sección 7)

| parámetro | valor | justificación |
|---|---|---|
| `rsi_period` | **2** | Valor canónico de Connors RSI(2), la formulación específica citada en la hipótesis y en `docs/author_library.md`. No es un placeholder: es el valor con el que la literatura fuente (Connors & Alvarez, *Short Term Trading Strategies That Work*, 2008) documenta el patrón. |
| `entry_threshold` | **10** | Umbral clásico de sobreventa/sobrecompra extrema de la misma fuente (RSI(2) < 10 para largos, > 90 para cortos vía la fórmula simétrica `100 - entry_threshold`). Válido por rango de `qaf/contracts.py` (`(0, 50]`). |
| `trend_filter_sma` | **200** | Filtro de tendencia de largo plazo clásico de la literatura de Connors/ConnorsRSI (SMA200 como definición estándar de "régimen alcista/bajista de fondo"), y el mismo horizonte ya usado en `docs/author_library.md` para catalogar a este autor ("filtro de tendencia SMA200"). Válido por rango de `qaf/contracts.py` (`2-500`). |

Estos tres valores están **anclados a la fuente**, no optimizados sobre `data/clean/SP500/D1/IS.parquet` — ningún archivo de precio fue tocado para fijarlos. Se declaran fijos (estructurales), igual que el `streak=3` de la hipótesis #001: probar RSI(3), umbral 5, o SMA100 es una hipótesis/spec distinta, no una variante silenciosa de esta. Si el AED de `engine` muestra que el filtro SMA200 deja muy pocas señales en el IS de SP500 (riesgo ya señalado como pregunta abierta en la hipótesis), eso se documenta como hallazgo — no se ajusta el valor en silencio.

No hay filtro de magnitud adicional (volumen, ATR mínimo del movimiento) más allá del filtro de tendencia — la hipótesis no lo especifica y `protocol` no añade condiciones que no están en la hipótesis.

## 3. Regla de salida (numérica — SL, TP y salida por tiempo)

**Reserva de motor ya declarada, se reitera aquí porque aplica directamente a esta spec** (`docs/author_library.md`, fila Connors; hipótesis sección "Horizonte de holding esperado"): la fuente original de Connors sale de la posición cuando el precio cruza de vuelta sobre una SMA5, **sin stop fijo**. El motor `qaf` no soporta esa salida — esta spec, como toda estrategia de este proyecto, sale siempre por SL/TP de ATR o por time-stop. Es un híbrido, no una réplica exacta de Connors; no se trata un resultado de este backtest como validación de "el sistema RSI(2) completo de Connors funciona", sino de esta versión híbrida con stops.

Con `ATR(atr_period)` = Average True Range de Wilder (`qaf/signals.py::atr`, fórmula estándar sobre `TR = max(high-low, |high-prev_close|, |low-prev_close|)`), calculado con datos hasta el close de la barra de señal inclusive, sin look-ahead:

- **LARGA**: `SL = entry_price - sl_atr × ATR`; `TP = entry_price + tp_atr × ATR`.
- **CORTA**: `SL = entry_price + sl_atr × ATR`; `TP = entry_price - tp_atr × ATR`.
- Resolución intrabarra (`qaf/engine.py::resolve_exit`, comportamiento del motor, no específico de esta spec): si la barra abre ya más allá del SL, se cierra al open (`STOP_GAP`) — el gap tiene prioridad incluso sobre el time-stop programado. Si abre ya más allá del TP sin haber tocado el SL, se cierra al open de forma conservadora (`TARGET_GAP_CONSERVATIVE`). Si ambos niveles caen dentro del rango `[low, high]` de la misma barra sin gap, se asume que el **SL se toca primero** (`STOP_TIE`, regla conservadora — con datos D1 sin secuencia de ticks no se puede saber el orden real).
- **Salida por tiempo (safety net)**: si ni SL ni TP se tocan dentro de `max_holding` sesiones D1 desde la barra de entrada, se cierra a mercado en la apertura de la sesión `max_holding + 1`.

### Valores por defecto de estos parámetros libres (sección 7 explica por qué son 4, al tope de la regla 16)

| parámetro | default | justificación |
|---|---|---|
| `atr_period` | **14** | Estándar de Wilder, mismo valor ya usado en la hipótesis #001 — consistencia de proyecto, no hay razón específica de esta hipótesis para desviarse. |
| `sl_atr` | **1.5** | Punto de partida defendible: stop moderado que absorbe ruido intradía sin invalidar la señal de sobreventa en la primera vela adversa. |
| `tp_atr` | **1.0** | A diferencia de la hipótesis #001 (2:1, reversión tras racha estructural), el edge que reclama Connors para RSI(2) es de **alta tasa de acierto con ganancia modesta por operación** (reversión parcial de corto plazo, no una reversión de tendencia completa) — un objetivo más cercano a 1:1 que a 2:1 es más consistente con esa narrativa que un TP amplio que rara vez se alcanza antes del time-stop. Sujeto a la sensibilidad obligatoria de la sección 7: no se declara óptimo. |
| `max_holding` | **5** | Coincide con el horizonte de holding "2 a 5 sesiones" que la propia hipótesis atribuye al holding típico del sistema original de Connors (sección "Horizonte de holding esperado" del documento de hipótesis) — se usa como techo de seguridad, no como duración esperada fija. |

## 4. Modelo de fill explícito

- Señal en el close de la barra `t` (D1) → orden a mercado en la **apertura de la barra `t+1`** (`qaf/engine.py::simulate`: `signal[i-1]` dispara entrada en `o[i]`). Nunca fill al close de la barra de señal.
- Precio de referencia: **mid** — asunción interina (`price_basis: "unknown"` en `config/instruments.json`). `engine` debe declarar el precio real (bid/ask/mid) en `reports/sp500-d1-rsi2-mean-reversion/data_quality.md` al correr Gate 0. Si Gate 0 declara algo distinto de mid, las fórmulas de costo de esta spec deben ajustarse antes del backtest.
- Costo de spread: el motor (`qaf/costs.py::execution_cost`) lo aplica como **la mitad del `spread_points` en la entrada y la mitad en la salida** — la suma sobre el round-trip es el spread completo (convención estándar de comprar al ask/vender al bid), no "una vez, en la entrada". Esto se documenta aquí explícitamente porque es el comportamiento real del motor (`qaf/engine.py` líneas de `execution_cost` en entrada y en salida), y evita una descripción incorrecta de la mecánica de costos.
- Salida: al primer evento entre SL, TP (con la regla de desempate/gap de la sección 3) o el time-stop.

## 5. Costo de bróker y ratio mínimo de expectancy

Fórmulas de `docs/cost_model.md`:
```
cost_roundturn  ≈ spread_points (completo, mitad+mitad) + 2 × slippage_points_per_side + 2 × commission_per_side
cost_holding    ≈ swap_dirección × noches mantenidas (× 3 la noche de swap triple = VIERNES para índices, no miércoles)
```

Con `tick_size=0.1`, `tick_value=1.0`, `point=0.1` (para SP500, `point == tick_size`, así que 1 punto = $1.00/lote directamente):

- `spread_cost` (round-trip completo) = 6 × 1.0 = **$6.00/lote**.
- `slippage_cost` (round-trip, 2 lados) = 2 × 1.5 × 1.0 = **$3.00/lote** (`slippage_points_per_side` SIN_CONFIRMAR — ver sección 0; magnitud pequeña frente a spread, pero no se trata como cero).
- `commission_cost` (round-trip, 2 lados, `commission_type=cash`) = 2 × 0.275 × 1.0 = **$0.55/lote** (no escala con precio, a diferencia de XAUUSD que usa `notional_fraction`).
- **Total costo de ejecución round-trip ≈ $9.55/lote** — cifra ya verificada de forma independiente en `scripts/verify_buy_and_hold.py` (ver sección 9, tabla de `PROJECT_STATE.md`: "costos (spread+slip+comisión): -9.55" para SP500, 1 lote).
- `cost_holding`:
  - Tramo LARGO: `-11.03 × noches` (costo real, resta del P&L).
  - Tramo CORTO: `+4.58 × noches` (crédito, suma al P&L) — la asimetría de swap no se promedia entre ramas, se modela por separado. **Nota de honestidad**: un crédito de swap en el tramo corto no es "edge" de la hipótesis — es un artefacto del pricing de financiación del bróker; no debe interpretarse como parte del mecanismo de reversión que se está probando.
  - Si el holding incluye la noche de **viernes** (día 4, `triple_weekday=4` en `config/instruments.json` — confirmado específicamente para índices en `docs/cost_model.md`, distinto de FX/metales que usan miércoles): esa noche se multiplica ×3 antes de sumar.
- A diferencia de la hipótesis #001 (holding también corto pero sobre XAUUSD, swap ~5-10× más grande en magnitud), el costo de financiación esperado por operación aquí es estructuralmente menor — coherente con la razón ya documentada en la hipótesis para preferir SP500 sobre NAS100 (10x menos comisión, ~33% menos spread, ~4x menos swap en magnitud).

**Ratio de fricción mínimo (CLAUDE.md regla 17)**: `expectancy neta por operación / costo total promedio por operación (roundturn + holding) ≥ 3.0`. Se mantiene el default de 3.0 sin relajar — `slippage_points_per_side` sigue sin confirmar y esta familia opera con más frecuencia que las hipótesis 001/002, así que el ratio agregado es más sensible a ese campo, no menos.

## 6. Riesgo por operación / sizing

- Riesgo fijo: **1.0% del equity de referencia por operación** (`risk_fraction=0.01`, dentro del rango `(0, 0.02]` de `qaf/contracts.py`; consistente con la hipótesis #001, sin razón específica de esta hipótesis para desviarse).
- Sizing gestionado por `qaf/engine.py::simulate`: `lots = risk_cash / (distancia_SL_en_cash + costo_de_ejecución_estimado)`, acotado por margen disponible (`max_leverage`) y por `volume_max`/`volume_step`/`volume_min` del instrumento — comportamiento del motor, no específico de esta spec.
- Equity de referencia: **100,000 USD** (`initial_equity`), por consistencia y reproducibilidad del sizing porcentual entre estrategias del proyecto.
- Sin martingala, sin incremento de tamaño tras pérdidas/ganancias. Tamaño se recalcula en cada entrada nueva según el equity vigente (compounding simple).

## 7. Parámetros libres y componentes estructurales

**Parámetros libres optimizables** (dentro del tope de 3-4 de CLAUDE.md regla 16):
1. `atr_period` (default 14)
2. `sl_atr` (default 1.5)
3. `tp_atr` (default 1.0)
4. `max_holding` (default 5)

= 4 parámetros libres, en el techo permitido. **No añadir un quinto** — en particular, `rsi_period`, `entry_threshold` y `trend_filter_sma` **no cuentan como parámetros libres de esta spec**: están fijados a valores clásicos de la literatura fuente (sección 2), no se someten a optimización dentro de este ciclo. Ampliar el barrido a esos tres valores (ej. probar RSI(3) o SMA100) constituiría una hipótesis/spec nueva, no una variante de ésta.

**Componentes estructurales** (señal RSI de sobreventa/sobrecompra, filtro de tendencia SMA, SL, TP, salida por tiempo, sizing por riesgo fijo) = 6, dentro de la zona sana documentada (4-8).

**Análisis de sensibilidad obligatorio** (CLAUDE.md regla 14): ±10-20% sobre cada uno de los 4 parámetros libres, mínimo 200 iteraciones tipo Montecarlo. La curva con los valores default de esta spec debe quedar en el centro del abanico resultante, no ser la más ganadora — si lo es, es señal de sobreajuste, no de una configuración superior.

## 8. División In-Sample / Out-of-Sample

- Split: **70% IS / 30% OOS**, cronológico, físico, por defecto (`qaf.ingest`, regla dura 13).
- Rutas: `data/clean/SP500/D1/IS.parquet` (ya existe, confirmado) y `data/clean/SP500/D1/OOS.parquet` (no se toca en esta fase; `protocol` no lo ha abierto, `engine` no debe abrirlo — solo `validator` lo abre una vez, al final, cuando exista el mecanismo de holdout habilitado).
- Este split queda **fijo** desde este punto. Ni `engine` ni `validator` lo recortan ni lo desplazan después de ver resultados OOS.
- Metodología real de validación dentro del IS: walk-forward por ventanas (regla dura 18), no un único ajuste estático.

## 9. Puerta de baseline obligatoria (comprar y mantener, mismo símbolo/timeframe)

`scripts/verify_buy_and_hold.py` (motor de costos real de `qaf`, no aritmética ad-hoc) ya corrió comprar-y-mantener en SP500 D1 sobre la partición **IS** (`qaf.data.load_is`, la única que expone hoy ese script), con el mismo modelo de costos de `docs/cost_model.md` (ver `PROJECT_STATE.md`, sección "Comprar-y-mantener re-verificado con el motor de costos real de `qaf`"):

- P&L bruto: +26,303.00
- Costo spread+slippage+comisión: -9.55
- Financiación acumulada: -50,396.07
- **P&L neto (IS): -24,102.62**

**Esta cifra es evidencia sobre la partición IS, no el número final de la puerta.** CLAUDE.md regla 19 exige comparar contra B&H "en la misma ventana OOS" — `validator` debe recalcular el B&H neto específicamente sobre `data/clean/SP500/D1/OOS.parquet` (con el mismo modelo de costos; `scripts/verify_buy_and_hold.py` no expone hoy una ruta OOS — `validator` deberá adaptarlo o usar el mecanismo de holdout equivalente al abrir OOS, una sola vez). El número de arriba es contexto direccional (el piso de holding largo en SP500 ya es negativo en la ventana IS completa) — no se reutiliza como sustituto del cálculo OOS real.

**El piso de esta puerta no es cero.** Esta estrategia no tiene que superar "ganar dinero" en comprar y mantener — dado que el B&H neto de SP500 ya es negativo por financiación en la ventana IS (y no hay razón a priori para esperar signo distinto en OOS), la estrategia debe demostrar edge por encima de ese piso negativo, no solo acertar la dirección del precio. Esto es consistente con la razón de ser de la hipótesis (holding de días, no años, para evitar que el swap domine como sí lo hace en B&H).

## 10. Puertas numéricas de aprobación

Hereda los defaults de CLAUDE.md salvo donde se justifica un ajuste específico:

1. **Profit factor OOS > 1.3** (default CLAUDE.md / `config/runner.json::min_profit_factor`).
2. **p-valor de test de permutación < 0.05** (default CLAUDE.md).
3. **Máximo drawdown OOS ≤ 20% del capital nominal de referencia** (`config/runner.json::max_drawdown_fraction=0.2`).
4. **Ratio de fricción ≥ 3.0** (`config/runner.json::min_friction_ratio`, expectancy neta / costo total, sección 5) — sin relajar, por `slippage_points_per_side` aún sin confirmar y por la mayor frecuencia de señales de esta familia.
5. **Supera el B&H neto de SP500 D1 en la misma ventana OOS**, mismos costos (sección 9) — piso no-cero, negativo por defecto según evidencia IS disponible; `validator` recalcula sobre OOS real, no reutiliza la cifra IS.
6. **Sensibilidad de parámetros** ±10-20%, ≥200 iteraciones Montecarlo, curva original en el centro del abanico (sección 7).
7. **Mínimo 30 operaciones en OOS** (`config/runner.json::min_trades`). Si el conteo de señales (RSI bajo umbral + filtro de tendencia) es menor, el resultado se marca `INVALID_POR_DATOS` por muestra insuficiente — no se fuerza un veredicto de aprobación o rechazo con baja muestra. Dado que esta familia genera señales con más frecuencia que `streak_reversal`, el riesgo aquí es más bien que el filtro SMA200 recorte demasiado las señales válidas (pregunta abierta ya señalada en la hipótesis) — `engine` debe reportar el conteo crudo de cruces de umbral RSI vs. el conteo tras aplicar el filtro de tendencia, para diagnosticar cuál de los dos componentes es el que más restringe.
8. **Gate 0 no puede ser mejor que `APTO_CON_RESERVAS`** mientras `spread_typical_points`/`spread_stress_mult`/`slippage_points_per_side` de SP500 sigan `SIN_CONFIRMAR`. `validator` no emite aprobación final sobre ese veredicto sin confirmación explícita de Alexander — usa `INVALID_POR_DATOS` en su lugar si Alexander no se ha pronunciado (CLAUDE.md regla 20).
9. **Diagnóstico de régimen (reporte obligatorio, no puerta de paso/no-paso)**: `engine` debe reportar el desempeño segmentado por terciles de tendencia/volatilidad (ej. terciles de ATR o de distancia `close` a `SMA200`), para que `validator` pueda evaluar si el edge depende de un régimen de tendencia alcista fuerte particular dentro del IS/OOS, en línea con la pregunta abierta de la hipótesis sobre si el filtro de tendencia deja suficientes señales.
10. **Diagnóstico de compresión de edge (reporte obligatorio)**: dado que la propia hipótesis señala el riesgo de que el patrón RSI(2)/ConnorsRSI esté comprimido por publicación masiva desde 2008, `engine` debe reportar el desempeño por sub-períodos del IS (ej. mitades o terciles cronológicos), para que `validator` pueda ver si el edge (si existe) se concentra en la parte más antigua de la muestra y se desvanece hacia el final — mismo tipo de diagnóstico ya exigido en la spec de la hipótesis #001, aplicado aquí por la misma razón de honestidad.

Ninguna de estas puertas se relaja sin visto bueno explícito de Alexander.

## 11. Número de hipótesis

**Hipótesis #003** de `docs/hypotheses/_registry.md` (`sp500-d1-rsi2-mean-reversion`, 2026-09-22). Tercera hipótesis del proyecto — las dos anteriores (#001 XAUUSD streak-reversal, #002 NAS100 turn-of-month) no sobrevivieron el IS (`DISCARDED_IS` y resultado exploratorio débil respectivamente). `validator` debe ajustar la exigencia del p-valor de permutación teniendo en cuenta N=3 hipótesis probadas en total (CLAUDE.md regla 22), no evaluar esta hipótesis de forma aislada como si fuera la primera.
