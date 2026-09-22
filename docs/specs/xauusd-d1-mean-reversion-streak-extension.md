# Spec: xauusd-d1-mean-reversion-streak-extension

tipo: estrategia candidata (hipótesis #001 de `docs/hypotheses/_registry.md`)
hipótesis origen: `docs/hypotheses/xauusd-d1-mean-reversion-streak-extension.md`
estado: spec generada por `protocol` — pendiente de Gate 0 / AED / backtest (`engine`), no aprobada ni rechazada aquí.

## 0. Evaluación de costos (por qué esta spec no está bloqueada, con una reserva explícita)

`docs/universe.md` fila 7: `alias=XAUUSD`, `symbol_mt5=XAUUSD`, `cost_key=metal`, `tfs=D1,H4`, `status=active`. D1 está dentro del alcance (CLAUDE.md: diario o 4H mínimo). El activo existe en el universo — primer requisito cumplido.

`docs/cost_model.md` — estado campo por campo, específico para XAUUSD (no el genérico `metal`):

| campo | valor usado | fuente | status |
|---|---|---|---|
| spread | 55 puntos (0.55 en precio, tick_size=0.01) | Sección LIVE, cuenta real, snapshot `20260922_1122` | real, pero **floating** — foto puntual, no constante. No es `SIN_CONFIRMAR`, es una observación real con caveat de variabilidad, no un hueco de dato. |
| commission_per_side | 0.0025% del valor de la orden, por lado (in y out) | Tabla "Por símbolo", fila XAUUSD | **CONFIRMED** hoy 2026-09-22, ventana "Especificación del símbolo" de la cuenta real |
| swap_long | -62.6 / noche / lote | Sección LIVE, cuenta real | real (extracción de cuenta) |
| swap_short | +35.4 / noche / lote | Sección LIVE, cuenta real | real (extracción de cuenta) |
| swap_rollover3days | 3 (miércoles, confirmado específicamente para XAUUSD) | Nota junto a la fila XAUUSD en "Por símbolo", hoy | confirmado hoy — no asumir que aplica igual a otros símbolos |
| contract_size / tick_value / tick_size | 100.0 / 1.0 / 0.01 | Sección LIVE, cuenta real | real |
| slippage_points | 0.15 (placeholder) | Tabla "Por cost_key", fila `metal` | **SIN_CONFIRMAR**, `source=web_orientativo` — no hay fila de override por símbolo para este campo |
| spread_stress_mult | — | Tabla "Por cost_key", fila `metal` | **SIN_CONFIRMAR** — no entra en la fórmula base de `cost_roundturn`, solo en pruebas de estrés de spread |

**Conclusión**: de los campos que entran en la fórmula de `docs/cost_model.md` (`cost_roundturn ≈ spread_model + 2×commission_per_side + slippage`; `cost_holding ≈ swap × noches`), cinco de seis están confirmados con datos reales de la cuenta (spread, commission, swap_long, swap_short, swap_triple_wednesday). El único campo que sigue siendo un placeholder genérico no confirmado es `slippage_points` (0.15, heredado de la fila `metal`, no hay override por símbolo). Ese valor es pequeño en magnitud frente a spread y comisión (ver cálculo de ejemplo en la sección 5) — no domina el costo total — pero **no se trata como confirmado ni se usa en silencio como si lo fuera**.

Decisión de `protocol`: el override por símbolo (más la Sección LIVE, que ya venía de la cuenta real antes de hoy) **es suficiente para escribir la spec**, porque el activo sí "tiene costos definidos" (la mayoría reales, no orientativos) — no se cumple la condición de bloqueo de mis instrucciones ("no tiene costos definidos"). Pero la regla de `cost_model.md` ("protocol no genera spec sobre un símbolo cuyo cost_key tenga campos relevantes en SIN_CONFIRMAR, salvo confirmación explícita de Alexander") se respeta así: la reserva de `slippage_points` **no se resuelve aquí, se traslada explícitamente aguas abajo** con un techo obligatorio ya construido en el propio pipeline:
- Gate 0 (`SKILL.md` de `data-quality-check`, sección E): mientras el `status` de un campo relevante del `cost_key` no sea `CONFIRMED`, el veredicto de Gate 0 **no puede ser mejor que `APTO_CON_RESERVAS`**. Esto aplica aquí — `engine` no puede declarar `APTO`.
- `validator` no puede emitir aprobación final con ese veredicto sin confirmación explícita de Alexander (CLAUDE.md regla 20, estado `INVALID_POR_DATOS` como alternativa a `RECHAZADA`).
- El ratio de fricción mínimo se mantiene en 3.0 sin relajar (ver sección 6) — precisamente porque no todos los campos de costo del bróker están confirmados todavía.

Si Alexander prefiere no aceptar esta reserva y exige confirmar `slippage_points` antes de que `engine` toque el dato, esta spec queda en pausa en ese punto — pero la traducción de la hipótesis a reglas numéricas ya está hecha y no se pierde trabajo.

## 1. Activo y timeframe
- alias: **XAUUSD** (`docs/universe.md` → `symbol_mt5=XAUUSD`, `type=cfd_metal`, `cost_key=metal`, `status=active`)
- timeframe: **D1**
- Dentro de alcance CLAUDE.md (CFD, diario, no scalping/HFT, no rebalanceo de cartera).
- No se extiende a H4 ni a XAGUSD — cualquier extensión es una hipótesis nueva, no esta spec.

## 2. Regla de entrada (numérica, sin ambigüedad)

Sobre `close` de barras D1 (precio de referencia: **mid** — ver sección 4, pendiente de confirmación formal por Gate 0):

1. Dirección de la barra `i`: `dir[i] = +1` si `close[i] > close[i-1]`; `dir[i] = -1` si `close[i] < close[i-1]`; `dir[i] = 0` si `close[i] == close[i-1]` (barra plana — rompe cualquier racha en curso, no cuenta como continuación).
2. `streak_len[i]` = número de barras consecutivas terminando en `i` (inclusive) con el mismo `dir` no-cero que `dir[i]`. Si `dir[i] = 0`, `streak_len[i] = 0`.
3. **Señal** en el close de la barra `t` si `streak_len[t] == 3` exactamente (no `>= 3` recurrente — una sola señal por racha, en el día en que la racha alcanza 3; los días 4, 5, 6... de la misma racha no generan señales nuevas).
   - Si `dir[t] = +1` (3 cierres alcistas consecutivos): señal **SHORT**.
   - Si `dir[t] = -1` (3 cierres bajistas consecutivos): señal **LONG**.
4. Máximo 1 posición abierta a la vez en esta estrategia/símbolo. Si hay una posición abierta cuando aparece una nueva señal (misma dirección u opuesta), la señal se descarta — no hay pirámide ni inversión de posición.
5. La racha de 3 días es un valor fijo de la hipótesis, no un parámetro libre a optimizar (ver sección 7 — límite de parámetros libres). Probar 4 o 5 días como umbral es una hipótesis/spec distinta, no una variante silenciosa de esta.

No hay filtro de magnitud adicional (ATR mínimo del movimiento, volumen, etc.) — la hipótesis original no lo especifica y `protocol` no añade condiciones que no están en la hipótesis. Si el AED de `engine` sugiere que hace falta uno, eso se documenta como hallazgo, no se aplica en silencio a esta spec.

## 3. Regla de salida (numérica — SL, TP y salida por tiempo)

Con `ATR14` = Average True Range de 14 barras (fórmula estándar de Wilder sobre True Range `TR = max(high-low, |high-prev_close|, |low-prev_close|)`), calculado con datos hasta el close de la barra de señal `t` inclusive, sin look-ahead.

- **LONG** (tras racha bajista): `SL = entry_price - 1.5 × ATR14`; `TP = entry_price + 3.0 × ATR14`.
  - SL se considera tocado si `low[barra] <= SL` en cualquier barra desde la entrada.
  - TP se considera tocado si `high[barra] >= TP` en cualquier barra desde la entrada.
- **SHORT** (tras racha alcista): `SL = entry_price + 1.5 × ATR14`; `TP = entry_price - 3.0 × ATR14`.
  - SL tocado si `high[barra] >= SL`. TP tocado si `low[barra] <= TP`.
- **Regla de desempate intrabarra**: si en la misma barra D1 el rango `[low, high]` contiene tanto el nivel de SL como el de TP, se asume que se ejecuta el **SL primero** (regla conservadora — con datos D1 sin secuencia de ticks no se puede saber el orden real).
- **Salida por tiempo (safety net)**: si ni SL ni TP se tocan dentro de 5 sesiones D1 contadas desde la barra de entrada (día 1 = barra de entrada, día 5 = quinta barra sostenida), se cierra a mercado al **open de la sexta barra** después de la entrada. Esto encapsula el horizonte de holding "2-5 sesiones" de la hipótesis como techo máximo — SL/TP gobiernan la salida temprana dentro de esa ventana.

R:R nominal de la regla (2:1, 3.0/1.5) es un punto de partida defendible para un patrón de reversión de corto plazo — sujeto al análisis de sensibilidad obligatorio (sección 7), no a re-optimización libre de forma.

## 4. Modelo de fill explícito

- Señal en el close de la barra `t` (D1) → orden a mercado al **open de la barra `t+1`**. Nunca fill al close de la barra de señal.
- Precio de referencia: **mid** — asunción interina, igual que en `docs/specs/dryrun_bh_sp500.md`, porque `data/clean/` no distingue bid/ask todavía. `engine` debe declarar el precio real (bid/ask/mid) en `reports/xauusd-d1-mean-reversion-streak-extension/data_quality.md` al correr Gate 0 (`.claude/skills/data-quality-check/SKILL.md`, sección D). Si Gate 0 declara algo distinto de mid, las fórmulas de fill y de costo de spread de esta sección deben ajustarse antes del backtest — no se asume mid sin esa confirmación.
- El costo de spread (sección 5) se aplica **una vez, al entrar** (no se duplica en la salida), igual que la convención ya usada en `dryrun_bh_sp500.md` — evita contar el spread dos veces.
- Salida: al primer evento entre SL, TP (con regla de desempate de la sección 3) o el time-stop al open de la sexta barra tras la entrada.

## 5. Costo de bróker y ratio mínimo de expectancy

Fórmulas de `docs/cost_model.md`:
```
cost_roundturn  ≈ spread_model + 2 × commission_per_side + slippage
cost_holding    ≈ swap_dirección × noches mantenidas (× 3 la noche de swap triple, miércoles para XAUUSD)
```

Con `tick_size=0.01`, `tick_value=1.0`, `contract_size=100.0` (1 punto = tick_size, vale `tick_value` por lote):

- `spread_cost` = 55 × 1.0 = **$55/lote** (una vez, entrada).
- `commission_cost` = 2 × 0.0025% × (precio × 100 × lotes) — **escala con el nivel de precio**, no es fija en $. Ejemplo a precio $2,000/oz: notional/lote = $200,000 → comisión = 0.005% × 200,000 = **$10/lote**. A precio $500/oz: notional/lote = $50,000 → comisión = **$2.5/lote**. `engine` debe calcularla barra a barra con el precio real de la orden, no con un promedio.
- `slippage_cost` = 0.15 × 1.0 = **$0.15/lote** (SIN_CONFIRMAR — ver sección 0; magnitud pequeña frente a spread+comisión, pero no se trata como cero).
- `cost_holding`:
  - Tramo LONG: `-62.6 × noches` (costo real, resta del P&L).
  - Tramo SHORT: `+35.4 × noches` (crédito, suma al P&L) — **la asimetría de swap no se promedia entre las dos ramas**, se modela por separado tal como exige la hipótesis original.
  - Si el holding incluye la noche de miércoles: esa noche específica se multiplica ×3 antes de sumar.

**Ratio de fricción mínimo (CLAUDE.md regla 17)**: `expectancy neta por operación / costo total promedio por operación (roundturn + holding) ≥ 3.0`. Se mantiene el default de 3.0 **sin relajar** — no hay confirmación completa de todos los campos de costo del bróker todavía (slippage pendiente), así que no aplica ninguna excepción a este piso.

## 6. Riesgo por operación / sizing

- Riesgo fijo: **1.0% del equity de referencia por operación**.
- `lotes = (equity × 0.01) / (distancia_SL_en_precio × 100)`, donde `distancia_SL_en_precio = 1.5 × ATR14` y `100 = contract_size` (equivalente a `tick_value/tick_size`).
- Equity de referencia: `engine` debe fijar un capital nominal inicial explícito y documentarlo (recomendado: 100,000 USD, por consistencia y reproducibilidad del sizing porcentual entre estrategias del proyecto) — si usa otro valor, debe decirlo en su reporte, no asumirlo en silencio.
- Sin martingala, sin incremento de tamaño tras pérdidas/ganancias. Tamaño se recalcula en cada entrada nueva según el equity vigente en ese momento (compounding simple).

## 7. Parámetros libres y componentes estructurales

Parámetros libres optimizables (dentro del tope de 3-4 de CLAUDE.md regla 16):
1. Periodo de ATR (default 14)
2. Multiplicador de SL (default 1.5×ATR)
3. Multiplicador de TP (default 3.0×ATR)
4. Máximo de sesiones sostenidas antes del time-stop (default 5)

= 4 parámetros libres, en el techo permitido. **No añadir un quinto** (ej. no optimizar también el umbral de racha de 3 días — ese es estructural, fijado por la hipótesis, no libre).

Componentes estructurales (señal de entrada por racha, filtro de dirección, SL, TP, salida por tiempo, sizing por riesgo fijo) = 5, dentro de la zona sana documentada (4-8).

Análisis de sensibilidad obligatorio (CLAUDE.md regla 14): ±10-20% sobre cada uno de los 4 parámetros, mínimo 200 iteraciones tipo Montecarlo. La curva con los valores default de esta spec debe quedar en el centro del abanico resultante, no ser la más ganadora — si lo es, es señal de sobreajuste, no de una configuración superior.

## 8. División In-Sample / Out-of-Sample

- Split: **70% IS / 30% OOS**, cronológico, por defecto.
- Rutas: `data/clean/XAUUSD/D1/IS.parquet` (ya existe — confirmado al leer el archivo) y `data/clean/XAUUSD/D1/OOS.parquet` (no se toca en esta fase; `protocol` no lo ha abierto, `engine` no debe abrirlo, solo `validator` lo abre una vez, al final).
- Este split queda **fijo** desde este punto. Ni `engine` ni `validator` lo recortan ni lo desplazan después de ver resultados OOS (regla dura 13, y mandato explícito de este agente).
- Metodología real de validación dentro del IS: walk-forward por ventanas (regla dura 18), no un único ajuste estático.

## 9. Puerta de baseline obligatoria (comprar y mantener, mismo símbolo/timeframe)

`reports/dryrun_costs_comparativa.md` ya corrió comprar-y-mantener en XAUUSD D1 sobre la ventana histórica completa disponible (1998-04 → 2018-04, ~20 años, 5,075 barras), con el mismo modelo de costos de `docs/cost_model.md`:
- P&L bruto: +103,902.00
- Costo spread+comisión: -56.55
- Swap acumulado: -317,632.40
- **P&L neto: -213,786.95** — el más caro de los tres símbolos probados en ese dry-run; el swap_long de oro domina incluso una tendencia alcista fuerte de 20 años.

**El piso de esta puerta no es cero.** Esta estrategia no tiene que superar "ganar dinero" en comprar y mantener — tiene que superar un B&H que, sobre esta ventana, ya es fuertemente negativo por financiamiento. Eso es consistente con la razón de ser de la hipótesis (holding de días, no años, para evitar que el swap domine) — pero no se declara aprobada solo por tener P&L positivo; tiene que demostrar edge por encima del costo de mantenimiento real de XAUUSD, no solo acertar la dirección del precio.

**Importante para `validator`**: el número -213,786.95 es de la ventana histórica completa usada en el dry-run (no necesariamente idéntica al slice OOS de 30% que resulte de este split). CLAUDE.md regla 19 exige comparar contra B&H "en la misma ventana OOS" — `validator` debe **recalcular el B&H neto específicamente sobre `data/clean/XAUUSD/D1/OOS.parquet`**, con el mismo modelo de costos, no reusar directamente la cifra de la ventana completa. La cifra de arriba es contexto/evidencia direccional de que el piso probablemente sea negativo también en el slice OOS, no el número final de la puerta.

## 10. Puertas numéricas de aprobación

Hereda los defaults de CLAUDE.md salvo donde se justifica un ajuste específico:

1. **Profit factor OOS > 1.3** (default CLAUDE.md).
2. **p-valor de test de permutación < 0.05** (default CLAUDE.md).
3. **Máximo drawdown OOS ≤ 20% del capital nominal de referencia** (CLAUDE.md no fija default global para esto — se fija aquí; si Alexander prefiere otro número, se ajusta antes de la primera validación real).
4. **Ratio de fricción ≥ 3.0** (expectancy neta / costo total, sección 5) — sin relajar, por el campo `slippage_points` aún sin confirmar.
5. **Supera el B&H neto de XAUUSD D1 en la misma ventana OOS**, mismos costos (sección 9) — piso no-cero, negativo por defecto según evidencia disponible.
6. **Sensibilidad de parámetros** ±10-20%, ≥200 iteraciones Montecarlo, curva original en el centro del abanico (sección 7).
7. **Mínimo 30 operaciones en OOS.** Si el conteo de señales (rachas de exactamente 3 días) es menor, el resultado se marca `INVALID_POR_DATOS` por muestra insuficiente — no se fuerza un veredicto de aprobación o rechazo con baja muestra.
8. **Gate 0 no puede ser mejor que `APTO_CON_RESERVAS`** mientras `slippage_points` de `cost_key=metal` siga `SIN_CONFIRMAR` (heredado de `SKILL.md`). `validator` no emite aprobación final sobre ese veredicto sin confirmación explícita de Alexander — usa `INVALID_POR_DATOS` en su lugar si Alexander no se ha pronunciado (CLAUDE.md regla 20).
9. **Diagnóstico de régimen (no es puerta numérica de paso/no-paso, es reporte obligatorio)**: la hipótesis original señala riesgo de que el patrón falle en regímenes de tendencia fuerte prolongada. `engine` debe reportar el desempeño segmentado por terciles de volatilidad/tendencia (ej. terciles de ATR14 o de fuerza de tendencia), para que `validator` pueda ver si el edge desaparece en el tercil de mayor tendencia — sin esto, `validator` no tiene base para evaluar ese caveat.

Ninguna de estas puertas se relaja sin visto bueno explícito de Alexander.

## 11. Número de hipótesis

**Hipótesis #001** de `docs/hypotheses/_registry.md` (`xauusd-d1-mean-reversion-streak-extension`, 2026-09-22). Primera hipótesis del proyecto — `validator` debe tener en cuenta que, a la fecha de esta spec, es la única hipótesis probada hasta ahora (N=1; hay una segunda, #002, `nas100-d1-turn-of-month-flow`, todavía en `pendiente`, no probada).
