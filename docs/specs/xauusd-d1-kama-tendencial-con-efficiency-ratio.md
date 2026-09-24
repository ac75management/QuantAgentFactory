# Hipótesis 007: XAUUSD D1 — KAMA Tendencial con Efficiency Ratio

**Estado: LISTO PARA VALIDACIÓN IS**

- Hipótesis: **#007** de `docs/hypotheses/_registry.md` (espejo de `config/hypotheses.json`, `id: "007"`, estado `pending` al escribir esta spec).
- Hipótesis origen: `docs/hypotheses/xauusd-d1-kama-tendencial-con-efficiency-ratio.md`. Revisión de fuente: `docs/sources/pilot-001-kama-xauusd-d1.review.json` (`source_rule_id: oxford-kama-turn-filter-atr6`).
- Fuente primaria registrada: Oxford Capital Strategies Ltd, "Kaufman Adaptive Moving Average | Trading Strategy (Setup)", https://oxfordstrat.com/trading-strategies/adaptive-moving-average-2/ (indicador de Perry J. Kaufman). Los hechos de la fuente citados en esta spec fueron **verificados por el coordinador en esa página el 2026-09-22**; `protocol` no tuvo acceso web y los usa tal cual.
- Fecha: 2026-09-22. Autor: `protocol`. Confirmación de fase: `python -m qaf.pipeline --hypothesis 007 --as protocol` → PERMITIDO (`NEEDS_SPEC`), informada por el coordinador.
- Tipo: **adaptación, no réplica** (cartera de 42 futuros → un solo CFD XAUUSD D1; entrada "al cierre" → entrada causal al open siguiente).
- Causas del bloqueo:
  1. **Por evidencia**: la fuente registrada no declara los valores base de `ER_Length` ni de `FastMA_Length`, ni ninguna salida distinta del stop (sección 8).
  2. **Por arquitectura**: qaf no implementa la familia de señal ni el tipo de salida que la regla necesita (sección 9).
- Esta spec no afirma rentabilidad ni contiene resultados. No se abrió ningún archivo de datos; OOS cerrado.

## 1. Alcance y verificación de instrumento

- `config/instruments.json` → `XAUUSD`: `status: "research"`, `timeframes: ["H1","H4","D1"]`, `asset_class: commodity_cfd`. `docs/universe.md`: alias `XAUUSD`, `symbol_mt5 XAUUSD`, `active`, D1 disponible. Dentro del alcance de CLAUDE.md (CFD de materia prima, diario, no scalping, no rebalanceo de cartera).
- Datos: `data/clean/XAUUSD/D1/IS.parquet` (1998-04-22 a 2018-04-18, 5075 filas, según el coordinador). OOS desde 2018-04-19, cerrado.
- Reservas del instrumento (no bloquean escribir la spec; sí bloquean una aprobación final de `validator`): `costs_verified: false`, `calendar_verified: false`, `provenance_verified: false`, `price_basis: "unknown"`.
- Familia: ninguna de `qaf/contracts.py::FAMILIES` (`streak_reversal`, `trend_cross`, `channel_breakout`, `oscillator_reversion`). La hipótesis declara que "requiere una familia KAMA nueva y no debe forzarse dentro de trend_cross". Esta spec no la fuerza en ninguna familia existente.

## 2. Réplica frente a adaptación

| dimensión | fuente (Oxford) | esta spec | tipo |
|---|---|---|---|
| Instrumento / vehículo | cartera de 42 futuros de EE. UU. (materias primas, divisas, tipos, índices), 1980-01-01 a 2011-12-31 | un CFD XAUUSD de Darwinex | adaptación (declarada por la hipótesis) |
| Cartera | 42 mercados con capital común | un solo instrumento con capital propio | adaptación |
| Timeframe | no declarado | D1 | adaptación (la fuente no lo fija) |
| Momento de ejecución | "buy at the close" de la barra que cumple la condición | señal al cierre de la barra i → orden a mercado al open de i+1 | **desviación obligatoria** (causalidad) |
| Precio "Entry" del stop | cierre de la barra de señal | precio de fill (open de i+1) | consecuencia de la desviación anterior |
| Sizing | Fixed_Fractional 1% sobre 1,000,000 USD de cartera | 1% del balance vigente por operación, capital 100,000 USD | adaptación |
| Costos | escenarios de 0 y 100 USD por vuelta | contrato XAUUSD de `config/instruments.json` | adaptación obligatoria |
| Datos | futuros continuos (construcción y rollover no detallados) | serie CFD Darwinex, rollover NY 17:00 supuesto | adaptación, con reservas |
| Señales con posición abierta | no declarado | una sola posición; señales ignoradas mientras está abierta | supuesto de adaptación (motor) |
| Salida distinta del stop | no declarada | **PENDIENTE** | bloqueante |

## 3. Reglas congeladas (determinadas por la fuente)

Notación: barras D1 indexadas `0..N−1` en el orden que entrega qaf. `n = ER_Length` (**PENDIENTE**), `L_fast = FastMA_Length` (**PENDIENTE**). Todas las series usan el `close` de la barra. Todo valor en la barra `i` depende solo de barras `≤ i`.

### 3.1 Efficiency Ratio y AMA (fórmula de Kaufman, tal como la publica la fuente)

```
ER[i]   = |Close[i] − Close[i−n]| / Σ_{j=i−n+1..i} |Close[j] − Close[j−1]|     (definido para i ≥ n)
Fast    = 2 / (L_fast + 1)
Slow    = 2 / (30 + 1)                  SlowMA_Length = 30, fijo en la fuente
c[i]    = (ER[i] · (Fast − Slow) + Slow)^2
AMA[i]  = AMA[i−1] + c[i] · (Close[i] − AMA[i−1])
```

### 3.2 Pivotes de giro

```
si AMA[i] > AMA[i−1] y AMA[i−1] < AMA[i−2]  →  MinAMA = AMA[i−1]
si AMA[i] < AMA[i−1] y AMA[i−1] > AMA[i−2]  →  MaxAMA = AMA[i−1]
```

Desigualdades estrictas (literales). Entre pivotes, `MinAMA` y `MaxAMA` conservan su último valor: la fuente solo los asigna en el giro.

### 3.3 Filtro de confirmación

```
ΔAMA[j]   = AMA[j] − AMA[j−1]
Filter[i] = 0.01 · StdDev(ΔAMA[i−19], …, ΔAMA[i])        ventana de 20 barras que termina en i
```

### 3.4 Regla de entrada

- **Larga** en la barra `i`: `AMA[i] > AMA[i−1]` **y** `(AMA[i] − MinAMA) > Filter[i]`.
- **Corta** en la barra `i`: `AMA[i] < AMA[i−1]` **y** `(MaxAMA − AMA[i]) > Filter[i]` (simétrico, como lo describe la fuente).
- La condición es **de estado, no de evento**: se evalúa en cualquier barra posterior al giro, no solo en la barra del giro (incluye la propia barra en la que se registra el pivote; ver 4.4). No se aplica deduplicación del tipo "un evento por excursión" (la que qaf usa en `oscillator_reversion`): añadirla sería una regla que la fuente no tiene.
- Larga y corta son mutuamente excluyentes en una misma barra (`AMA[i] > AMA[i−1]` frente a `AMA[i] < AMA[i−1]`).
- `direction`: **both** (la fuente opera los dos lados).

### 3.5 Stop loss

- Largo: `Stop = Entry − 6 · ATR(20)[i]`. Corto: `Stop = Entry + 6 · ATR(20)[i]`.
- `ATR(20)` calculado con datos hasta el cierre de la barra de señal `i` inclusive. `Entry` = precio de fill al open de `i+1` (sección 5).
- **Fijo** durante toda la vida de la posición: sin trailing y sin breakeven.
- En qaf equivale a `atr_period = 20` y `sl_atr = 6`. Son valores de la fuente, no parámetros libres.
- Resolución (comportamiento de `qaf/engine.py::resolve_exit`): si el open ya está más allá del stop, se cierra al open (`STOP_GAP`); si lo toca dentro de la barra, se cierra al nivel del stop (`STOP`). Si la resolución de la sección 8 añade un take profit, rige la regla conservadora del motor (el stop gana el empate intrabarra, `STOP_TIE`).

### 3.6 Posición y señales concurrentes (supuesto de adaptación)

La fuente no declara pirámide, inversión ni qué ocurre con una señal mientras hay posición abierta. Esta spec adopta lo que `qaf/engine.py::simulate` hace hoy, declarado como supuesto y no como regla de la fuente:

- Como máximo una posición abierta.
- Una señal en la barra `i` solo se ejecuta si no había posición abierta al cierre de `i`. Mientras hay posición, las señales (de la misma dirección o de la opuesta) se descartan: no hay pirámide ni inversión.
- Tras una salida (por ejemplo, un stop en la barra `k`), si la condición de estado sigue vigente al cierre de `k`, hay una nueva entrada al open de `k+1`. Es la consecuencia de la lectura literal de estado y se declara como supuesto.
- **Advertencia**: este supuesto depende del bloqueante de salida (8.3). Si la regla original resulta ser stop-and-reverse o salida por señal opuesta, "ignorar la señal opuesta" deja de ser neutral, porque es justamente la regla que falta. Este apartado se reescribe entonces con esa evidencia, nunca a la vista de resultados.

### 3.7 Riesgo por operación y sizing

- Fuente: Fixed_Fractional = 1% sobre un capital de 1,000,000 USD, cartera de 42 futuros. **Interpretación de adaptación**: se arriesga hasta el stop el 1% del balance vigente en cada operación.
- qaf: `risk_fraction = 0.01` (dentro de `(0, 0.02]`). `initial_equity = 100,000 USD` es una convención de proyecto (`config/runner.json`): el 1,000,000 de la fuente era capital de cartera y no se asignaba por instrumento.
- Mecánica del motor (no es específica de esta spec): `lots = risk_cash / (distancia al stop en cash + costo round-trip estimado)`. El resultado se limita por margen (`max_leverage` 10) y por `volume_max`, y se redondea hacia abajo a `volume_step` 0.01; si queda por debajo de `volume_min`, la entrada se omite. Como el costo estimado entra en el denominador, la posición queda algo menor que un fixed fractional puro. Es una desviación menor y queda declarada.
- `config/runner.json` fija `risk_fraction: 0.005` como default de campaña; esta spec fija 0.01 porque así lo dice la fuente. Si al registrar hay un conflicto de precedencia, decide Alexander. No se cambia en silencio.
- Sin martingala y sin aumentar el tamaño tras ganancias o pérdidas.

## 4. Convenciones de implementación (no son parámetros)

La fuente no las fija y no afectan a la lógica del edge. Se congelan aquí para que el cálculo sea único. No entran en la sensibilidad ni se cambian después de ver resultados.

- **4.1 Semilla de la AMA**: `AMA[n] = Close[n]`, la primera barra con ER definido. La recursión empieza en `n+1`.
- **4.2 ER con denominador cero** (todos los cierres de la ventana iguales): `ER[i] = 0`, con lo que `c[i] = Slow²`.
- **4.3 StdDev poblacional** (divisor 20). La variante muestral (divisor 19) multiplica `Filter` por `√(20/19) ≈ 1.026` sobre un umbral que ya es de 0.01σ. No importa para el edge, pero se fija para evitar ambigüedad.
- **4.4 Orden de evaluación en cada barra `i`**:
  1. ER, `c` y AMA.
  2. `Filter`.
  3. Actualizar `MinAMA`/`MaxAMA` según 3.2.
  4. Evaluar la entrada con los pivotes ya actualizados.

  Es la lectura del orden en que la fuente enumera sus reglas. Permite entrar en la misma barra del giro si `AMA[i] − AMA[i−1] > Filter[i]`.
- **4.5 Pivotes durante el calentamiento**: se registran desde que existe `AMA[i−2]` (`i ≥ n+2`). `MinAMA` y `MaxAMA` quedan indefinidos hasta el primer pivote de su tipo; sin pivote definido no hay señal de ese lado.
- **4.6 Calentamiento**: ninguna señal antes de `i0 = n + 20`, la primera barra con `Filter` definido. El `ATR(20)` de qaf ya existe desde la barra 20, antes de `i0`. Además, el motor omite la entrada si el ATR no es finito.
- **4.7 ATR**: el de `qaf/signals.py::atr`. True Range estándar; semilla igual a la media simple de `TR[1..20]` en la barra 20 y suavizado de Wilder a partir de ahí. Según los hechos verificados, la fuente no precisa el método de suavizado.
- **4.8 Ventanas medidas en barras** del dataset tal como lo entrega `qaf/ingest.py`. Con `calendar_verified: false`, si Gate 0 detecta barras de domingo o sesiones parciales, eso afecta a todas las ventanas en barras (`n`, 20, 20). Se reporta; la spec no lo corrige.
- **4.9 Encadenamiento IS→OOS**: la semilla se aplica a la primera barra de la serie que recibe el cálculo. Si `validator` usa historial previo como calentamiento (`start_bar`), el estado de la AMA y de los pivotes continúa. Es el mismo tratamiento que reciben los indicadores recursivos ya existentes (ATR y RSI de Wilder). Se documenta en el reporte y no se elige por resultado.

**Reserva sobre la semilla**: el peso de la semilla decae como `Π(1 − c[k])`. Como `c ≥ Slow² ≈ 0.00416`, en el peor caso (ER ≈ 0 sostenido) su vida media es de unas 166 barras. No se añade un burn-in extra, que sería una elección sin fuente. `engine` debe reportar cuántas señales caen en las primeras 166 barras elegibles.

## 5. Modelo de fill

- La señal se evalúa al cierre de la barra `i` y la orden va a mercado al **open de la barra `i+1`**: en `qaf/engine.py::simulate`, `signal[i−1]` dispara la entrada en `o[i]`. Es una **desviación obligatoria** respecto de "buy at the close" de la fuente, porque ese fill usa el mismo cierre que revela la señal y no es causal con OHLC de barra.
- El stop se fija sobre ese precio de fill con el `ATR(20)` de la barra `i` (3.5).
- Precio de referencia: `price_basis: "unknown"` en `config/instruments.json`, cuya lista `reserves` supone mid ("Referencia mid supuesta; bid/ask pendiente"). Es una reserva, no un hecho confirmado: Gate 0 debe declararlo.
- Costos por lado (`qaf/costs.py::execution_cost`): medio spread, más el slippage por lado, más la comisión por lado.
- No se abre posición en la última barra del tramo. Una posición que sigue abierta al final se cierra al close de la última barra (`END_OF_SAMPLE`).
- Salida por tiempo: solo si la resolución de 8.3 la incluye. En ese caso, qaf cierra al open de la barra `entrada + max_holding`, y solo un gap en ese open (`STOP_GAP` o `TARGET_GAP_CONSERVATIVE`) la precede.

## 6. Costo de bróker (referencia, sin cálculo manual)

Campos de `config/instruments.json` → `XAUUSD` (`as_of` 2026-09-22, snapshot `docs/cost_snapshots/20260922_1122.json`):

| campo | valor |
|---|---|
| `spread_points` | 55 |
| `slippage_points_per_side` | 13.75 (escenario, no histórico) |
| `commission_type` / `commission_per_side` | `notional_fraction` / 2.5e-05 |
| `swap_unit` | `account_cash_per_lot` |
| `swap_long` / `swap_short` | −62.6 / +35.4 |
| `swap_schedule` / `triple_weekday` | `triple` / 2 (miércoles) |
| `rollover_timezone` / `rollover_time` | `America/New_York` / `17:00` |
| `point` / `tick_size` / `tick_value` / `contract_size` | 0.01 / 0.01 / 1.0 / 100 |
| `max_leverage` / `volume_min` / `volume_step` / `volume_max` | 10 / 0.01 / 0.01 / 10 |
| `costs_verified` / `calendar_verified` / `provenance_verified` / `price_basis` | false / false / false / unknown |

- **Ratio de fricción mínimo**: expectancy neta / (spread + comisión + slippage + swap) **≥ 3.0** (CLAUDE.md regla 17; `config/runner.json::min_friction_ratio`). No se relaja mientras `costs_verified` sea `false`.
- El costo de financiación crece con las noches que dura la posición, y esa duración la determina la salida pendiente (8.3). El largo paga swap y el corto lo cobra: los dos lados se reportan por separado. El crédito del corto es pricing del bróker, no parte del mecanismo. El swap actual se aplica a precios históricos (limitación C4). **La salida no se elige para reducir swap: se toma de la fuente.**
- Los escenarios de 0 y 100 USD por vuelta de la fuente son evidencia externa y no se usan.

## 7. División In-Sample / Out-of-Sample

- Fijada por `qaf/ingest.py` y no se redefine: IS de 1998-04-22 a 2018-04-18 (5075 filas); OOS desde 2018-04-19. Solo `validator` abre el OOS, una vez, al final.
- Validación dentro del IS por walk-forward (CLAUDE.md regla 18).
- **Solape temporal con la fuente**: la muestra de Oxford (1980-2011) cubre el tramo del IS que va de 1998-04-22 a 2011-12-31, aproximadamente dos tercios del IS. Las consecuencias están en 8.5.

## 8. Bloqueantes de especificación

Estos elementos no pueden congelarse sin **elegir**, y esta spec no elige.

- **8.1 Valor base de `ER_Length`**: la fuente solo publica el rango de sensibilidad `[2, 100]`, paso 2.
- **8.2 Valor base de `FastMA_Length`**: la fuente solo publica el rango `[2, 28]`, paso 1.
- **8.3 Salida distinta del stop**: la fuente no declara take profit, ni salida por señal opuesta, ni stop-and-reverse, ni salida por tiempo. La lectura "solo stop, hasta que salte" es técnicamente codeable, pero no se adopta por dos motivos: la fuente no dice que su descripción de salidas sea exhaustiva, y adoptarla sería elegir entre lecturas posibles. Además, no se puede expresar en qaf, que exige `tp_atr > 0` y un `max_holding` entero.
- **8.4 Horizonte del AED**: `qaf/aed.py` usa `max_holding` como horizonte. Sin regla de salida no hay horizonte que no sea inventado.

**8.5 Por qué no se toman de los gráficos de Oxford.** Los gráficos de sensibilidad de `ER_Length` × `FastMA_Length` son resultados sobre 1980-2011, un periodo que se solapa con unos dos tercios de nuestro IS. Elegir el pico o la meseta de esos gráficos sería **seleccionar por resultados sobre datos que se solapan con el IS**: contamina el IS, oculta pruebas múltiples dentro del conteo de hipótesis y vacía de contenido la sensibilidad posterior. Queda prohibido (CLAUDE.md regla 10; límites de la evidencia en la hipótesis). Por la misma razón, tampoco se eligen valores mirando el IS de XAUUSD.

**8.6 Qué no se acepta como salida provisional.** No se emula la ausencia de TP o de salida por tiempo con valores centinela (por ejemplo, `tp_atr` enorme y `max_holding = 2000`):
- Sería una aproximación, y el protocolo exige no aproximar.
- La sensibilidad de ±10/20% sobre un centinela no significa nada.
- Un horizonte AED de 2000 barras equivale a cerca del 40% del IS.

**8.7 Candidato a verificar, no adoptado.** KAMA(10, 2, 30) (`ER_Length = 10`, `FastMA_Length = 2`, `SlowMA_Length = 30`) se cita ampliamente como el valor por defecto de Kaufman. Aquí figura **solo como candidato a verificar** en su texto original (Kaufman, *Smarter Trading*, 1995; *Trading Systems and Methods*), no como valor adoptado. Lo que lo haría admisible no es que sea popular: es que un valor publicado en 1995 quedaría fijado antes del IS (1998-2018), sin mirar nuestros datos. La misma verificación debe establecer la regla de salida original.

**8.8 Conflicto de fuentes.** Si el texto original de Kaufman difiere de Oxford en algo que esta spec ya congeló (fórmulas, multiplicador 0.01 del filtro, ventana de 20, stop 6 × ATR(20)), lo congelado no se reemplaza. La fuente registrada es Oxford (`oxford-kama-turn-filter-atr6`). La discrepancia se reporta a Alexander: cambiar la regla fuente sería otra hipótesis u otra regla, no un ajuste de esta.

## 9. Capacidades que faltan en qaf

Descripción de capacidades, sin proponer código:

1. **Familia de señal KAMA con giro y filtro**:
   - ER y AMA recursiva.
   - Estado persistente de pivotes `MinAMA`/`MaxAMA`.
   - Filtro por StdDev de `ΔAMA`.
   - Condición de estado evaluada en cada barra.

   No existe ni en `FAMILIES`, ni en `qaf/signals.py::generate`, ni en `validate_spec`. Tampoco hay validación de sus parámetros (enteros, rangos de la fuente, `FastMA_Length < SlowMA_Length`, coherente con los rangos publicados).
2. **Salida**, según cómo se resuelva 8.3:
   - (a) salida por señal opuesta;
   - (b) stop-and-reverse (cierre e inversión en el mismo fill);
   - (c) posición sin take profit (hoy `tp_atr > 0` es obligatorio);
   - (d) posición sin salida por tiempo (hoy `max_holding` entero de 1 a 2000 es obligatorio).
3. **AED con salida por señal**: si la salida no es por tiempo, el horizonte fijo `max_holding` no representa la duración de la operación. Hay que definir de dónde sale el horizonte del AED. También hay que confirmar que tratar como entrada cada barra en la que la señal de estado está activa (lo que hace hoy `qaf/aed.py`, que conserva las rachas mediante la rotación) es la prueba adecuada para esta familia.
4. **Decisión de diseño pendiente**: si `SlowMA_Length = 30`, el multiplicador 0.01 y la ventana de 20 del filtro van dentro de `parameters` o son constantes de la familia. Si van dentro, la sensibilidad de qaf los moverá. Eso vale como diagnóstico, pero no los convierte en parámetros libres.

## 10. Contrato previsto (no registrable)

| campo | valor | estado | causa / origen |
|---|---|---|---|
| `id` | `xauusd-d1-kama-tendencial-con-efficiency-ratio` | congelado | slug de la hipótesis |
| `family` | — | **PENDIENTE** | no existe en `FAMILIES`; requiere familia nueva (sección 9); prohibido usar `trend_cross` u otra |
| `symbol` | `XAUUSD` | congelado | hipótesis; `config/instruments.json` |
| `timeframe` | `D1` | congelado | adaptación (la fuente no declara timeframe) |
| `parameters.atr_period` | 20 | congelado | fuente: ATR_Length = 20 |
| `parameters.sl_atr` | 6 | congelado | fuente: ATR_Stop = 6, fijo |
| `parameters.tp_atr` | — | **PENDIENTE** | la fuente no declara TP; qaf exige > 0; sin centinelas (8.6) |
| `parameters.max_holding` | — | **PENDIENTE** | la fuente no declara salida por tiempo; qaf exige un entero de 1 a 2000 y lo usa como horizonte del AED |
| `parameters.<er_length>` | — | **PENDIENTE** | la fuente solo da el rango [2,100] paso 2 (8.1) |
| `parameters.<fast_length>` | — | **PENDIENTE** | la fuente solo da el rango [2,28] paso 1 (8.2) |
| `parameters.<slow_length>` | 30 | congelado (nombre de campo pendiente) | fuente: SlowMA_Length = 30 |
| `parameters.<filter_multiplier>` | 0.01 | congelado (nombre de campo pendiente) | fuente |
| `parameters.<filter_std_window>` | 20 | congelado (nombre de campo pendiente) | fuente |
| `rationale` | "Giro confirmado de la media adaptativa de Kaufman (Efficiency Ratio) como señal de persistencia direccional en XAUUSD D1, con stop fijo de 6 ATR(20); adaptación causal de la regla publicada por Oxford Capital Strategies." | congelado | hipótesis |
| `hypothesis_id` | `"007"` (string) | congelado | existe en `config/hypotheses.json` |
| `risk_fraction` | 0.01 | congelado | fuente: Fixed_Fractional 1% (3.7) |
| `initial_equity` | 100000 | congelado | convención de proyecto (3.7) |
| `direction` | `both` | congelado | la fuente opera largos y cortos |
| `version` | 1 | congelado | primera versión |

Los nombres entre `< >` los fija quien implemente la familia; no están definidos en qaf.

## 11. Parámetros libres y componentes estructurales

**Fijados por la fuente (no libres)**: `SlowMA_Length = 30`, `atr_period = 20`, `sl_atr = 6`, multiplicador del filtro 0.01 y ventana de 20. Si terminan dentro de `parameters`, la sensibilidad de qaf los moverá como diagnóstico, igual que hizo con `rsi_period` en la spec #003, sin contarlos como libres.

**Libres (necesitan valor base)**: `ER_Length` y `FastMA_Length`, que son las dos dimensiones que la propia fuente barre. Son **2**. A eso se suma lo que traiga la salida:

- Salida por señal opuesta o stop-and-reverse: 0 parámetros extra, **2 libres** en total.
- Salida por TP en ATR más salida por tiempo: +2 (`tp_atr`, `max_holding`), **4 libres**. Sería el tope de la regla 16, con dos de ellos sin respaldo en la fuente, lo que justifica sospecha y exigiría evidencia propia para cada uno.

**Componentes estructurales**:
1. señal de giro de la AMA con ER;
2. filtro de confirmación 0.01σ(ΔAMA, 20);
3. stop fijo 6 × ATR(20);
4. salida (pendiente);
5. sizing fixed fractional del 1%.

Son **5**; con TP y salida por tiempo serían 6 o 7. En ambos casos quedan dentro de la zona sana de 4 a 8.

**Sensibilidad** (regla 14; `config/runner.json`): cada parámetro de `parameters` se mueve ±10/20%, más 200 vecinos conjuntos a ±20% (`sensitivity_mc_iterations` 200, `sensitivity_mc_range` 0.2, `sensitivity_min_valid` 100, `sensitivity_max_original_percentile` 0.8, `sensitivity_min_positive_share` 0.5). La spec falla si su configuración es el pico aislado de su vecindad. La sensibilidad es un diagnóstico y nunca selecciona un vecino.

## 12. Puertas de aprobación (heredadas; no se relajan sin visto bueno explícito de Alexander)

1. **Profit factor OOS > 1.3** (CLAUDE.md regla 5; `config/runner.json::min_profit_factor` 1.3).
2. **p-valor de permutación < 0.05** (`qaf/aed.py`, rotación circular, `bootstrap_iterations` 2000, `seed` 20260922). El horizonte (`max_holding`) está **PENDIENTE** (8.4). `validator` ajusta la exigencia por el número de hipótesis (sección 13).
3. **Drawdown máximo ≤ 20%** (`config/runner.json::max_drawdown_fraction` 0.2). Esta spec no fija un valor distinto porque no hay justificación de la fuente para hacerlo.
4. **Ratio de fricción ≥ 3.0**, swap incluido (sección 6).
5. **Mínimo 30 operaciones** (`config/runner.json::min_trades`). Si no se alcanzan, no se fuerza un veredicto ni se ajusta nada para conseguir más operaciones.
6. **Baseline obligatorio**: superar el comprar y mantener de **XAUUSD D1** con el **mismo capital invertido 1x**, los costos de `config/instruments.json` y la misma ventana. Lo calcula `qaf/baseline.py` en cada corrida; aquí no se copia ninguna cifra. El piso no es cero: con swap largo negativo, el baseline de CFD a varios años suele ser negativo, así que la estrategia debe ser rentable neta por sí misma.
7. **Sensibilidad** según la sección 11.
8. **Robustez completa** antes de cualquier aprobación (regla 3): Montecarlo, OOS y permutación. Después, incubación (regla 15), que Alexander confirma paso a paso.
9. **Gate 0**: el techo es `APTO_CON_RESERVAS` mientras `costs_verified`, `calendar_verified` y `provenance_verified` sean `false` y `price_basis` sea `unknown`. `validator` no emite aprobación final sin confirmación de Alexander; en su lugar usa `INVALID_POR_DATOS` (regla 20).

**Diagnósticos obligatorios de reporte** (no son puertas):
- resultados por lado, largo y corto (por la asimetría del swap);
- distribución de motivos de salida;
- el IS partido en 2011-12-31 (tramo que se solapa con la muestra de la fuente frente al que no), para ver si algún efecto existe solo en el periodo solapado;
- terciles cronológicos del IS;
- conteo de señales dentro de la ventana de decaimiento de la semilla (sección 4).

## 13. Número de hipótesis

**Hipótesis #007 de 7 registradas** en `docs/hypotheses/_registry.md`:
- 001, 003, 004 y 006: descartadas en IS;
- 002: bloqueada por arquitectura;
- 005: rechazada por el usuario;
- 007: esta.

`validator` debe tener en cuenta ese N al exigir la evidencia de permutación (regla 22). No debe evaluar esta hipótesis como si fuera la primera.

## 14. Qué la desbloquea (en orden)

1. **Evidencia de la fuente original** para el valor base de `ER_Length`, el de `FastMA_Length` y la regla de salida: Kaufman, *Smarter Trading* (1995) y/o *Trading Systems and Methods*, con cita de edición y página, entregada en `docs/research_external/<slug>.md`. Si no se consigue, **Alexander decide** si acepta una fuente secundaria, y cuál. Queda prohibido tomar los valores de gráficos de resultados que se solapen con 1998-2018.
2. **Decisión de Alexander** sobre si se implementa en qaf la familia de la sección 9, junto con la capacidad de salida que exija el punto 1.
3. Solo entonces, **`protocol` genera el JSON a partir de esta spec** sin cambiar nada de lo congelado (secciones 3, 4, 5, 6, 10 y 12). Solo completa los campos PENDIENTE con la evidencia del punto 1. `engine` lo valida y lo registra.

## 15. Pregunta propuesta para `docs/research_queue.md`

Esta pregunta **no se escribió** en `docs/research_queue.md` porque el encargo del coordinador limita a `protocol` a este único archivo. El texto está listo para que el coordinador lo añada:

```
### kama-kaufman-valores-base-y-salida — PENDIENTE
- Pregunta: ¿Qué valores de ER_Length y FastMA_Length (con SlowMA_Length = 30) y qué regla de salida distinta del stop (señal opuesta, stop-and-reverse, take profit, salida por tiempo u otra) define Perry Kaufman para el sistema AMA/KAMA con giro y filtro en Smarter Trading (1995) y/o Trading Systems and Methods? ¿Declara también la inicialización de la AMA y el timeframe de sus ejemplos?
- Origen: protocol, hipótesis #007 / docs/specs/xauusd-d1-kama-tendencial-con-efficiency-ratio.md (secciones 8 y 14), 2026-09-22
- Fuentes esperadas: texto original de Kaufman (edición y página); en segundo lugar, documentación que cite ese texto con página
- Qué debe traer el informe: fuente + cita textual, qué demuestra, qué no demuestra, año de publicación de los valores (deben ser anteriores al IS 1998-2018 o independientes de él), aplicabilidad a XAUUSD D1, nivel de confianza; señalar cualquier discrepancia con la regla de Oxford (filtro 0.01 x StdDev(ΔAMA, 20), stop 6 x ATR(20))
- Criterio de rechazo: valores por defecto de plataformas sin cita al texto de Kaufman; valores elegidos por optimización sobre datos que se solapen con 1998-2018 (incluidos los gráficos de sensibilidad de Oxford); blogs o cursos sin cita verificable
```

`protocol` no pudo listar `docs/research_external/` (no tiene herramienta de listado). Antes de encolar la pregunta, el coordinador debe confirmar que no existe ya un informe que la resuelva.
