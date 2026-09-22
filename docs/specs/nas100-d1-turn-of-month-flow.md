# Spec: nas100-d1-turn-of-month-flow

tipo: estrategia candidata (hipótesis #002 de `docs/hypotheses/_registry.md`)
hipótesis origen: `docs/hypotheses/nas100-d1-turn-of-month-flow.md`
estado: spec generada por `protocol` — pendiente de Gate 0 / AED / backtest (`engine`), no aprobada ni rechazada aquí.

## 0. Evaluación de costos (por qué esta spec no está bloqueada, con reservas explícitas)

`docs/universe.md` fila 10: `alias=NAS100`, `symbol_mt5=NDX`, `type=cfd_index`, `tfs=D1,H4`, `cost_key=index_us`, `status=active`. D1 está dentro de alcance (CLAUDE.md: diario o 4H mínimo). El activo existe en el universo — primer requisito cumplido.

`docs/cost_model.md` — estado campo por campo, específico para NAS100:

| campo | valor usado | fuente | status |
|---|---|---|---|
| commission_per_side | 2.75 USD/contrato | Tabla "Por símbolo", fila NAS100 | **CONFIRMED** (2026-09-22, tabla pública Darwinex forex-cfds/indices, cruzada con cuenta real) |
| swap_long | -45.73 / noche / lote | Sección LIVE, snapshot `20260922_1122` | **CONFIRMED** (extracción de cuenta real) |
| swap_short | +18.53 / noche / lote | Sección LIVE, snapshot `20260922_1122` | CONFIRMED, pero **no se usa** — esta estrategia es solo-largo (ver sección 1 y caveat de la hipótesis) |
| swap_rollover3days | 5 = **viernes** (confirmado específicamente para el grupo índices, distinto de FX/metal/energy) | `docs/cost_model.md`, sección "Comisión y día de swap triple" | **CONFIRMED** (2026-09-22) |
| contract_size / tick_value / tick_size | 10.0 / 1.0 / 0.1 | Sección LIVE | CONFIRMED |
| spread_typical_points | **9** (usado como aproximación) | Sección LIVE, `spread_points` snapshot `20260922_1122` — foto puntual real de la cuenta, **no** una serie "típica" confirmada | **SIN_CONFIRMAR como "típico"** — instrucción explícita de Alexander (2026-09-22): usar este valor de foto puntual como aproximación conservadora, documentado como tal, no bloquear la spec por esto. |
| slippage_points | **2** (estimación) | Estimación conservadora estándar para CFD índice líquido en D1 (no hay dato real de ejecución para NAS100) | **SIN_CONFIRMAR** — no es una cifra real de la cuenta ni del bróker, es un supuesto de modelado explícito por instrucción de Alexander (2026-09-22) para poder avanzar con el hueco documentado. |

**Conclusión**: comisión, swap (ambas direcciones), día de swap triple, contract_size/tick_value/tick_size están **CONFIRMED** con datos reales. Los dos campos que siguen abiertos (`spread_typical_points`, `slippage_points`) tienen valores de trabajo explícitamente marcados como aproximación/estimación, no como dato confirmado, por instrucción directa de Alexander para no bloquear esta spec. Esto **no** sube el status de Gate 0 a `APTO` — sigue topando en `APTO_CON_RESERVAS` (igual que la spec #001), y `validator` no puede emitir aprobación final sobre ese veredicto sin confirmación explícita adicional de Alexander (CLAUDE.md regla 20, `INVALID_POR_DATOS` como alternativa a `RECHAZADA` si Alexander no se ha pronunciado para entonces).

El ratio de fricción mínimo se mantiene en **3.0 sin relajar** (sección 6) — precisamente porque spread/slippage siguen sin confirmar y porque esta estrategia tiene la estructura de costo de swap más desfavorable del universo activo (solo-largo sobre el símbolo con `swap_long` más negativo).

## 1. Activo y timeframe

- alias: **NAS100** (`docs/universe.md` → `symbol_mt5=NDX`, `type=cfd_index`, `cost_key=index_us`, `status=active`)
- timeframe: **D1**
- Dentro de alcance CLAUDE.md (CFD, diario, no scalping/HFT, no rebalanceo de cartera).
- Dirección: **solo largo** — la hipótesis es direccional en un único sentido (flujo comprador mecánico de fin/inicio de mes). No hay rama corta simétrica; extenderla a corto sería una hipótesis distinta, no esta spec.
- No se extiende a H4, US30, SP500 ni DAX — comparten `cost_key=index_us`/`index_eu` pero son series de precio distintas (la propia hipótesis lo declara explícitamente).

## 2. Regla de entrada (numérica, sin ambigüedad)

Sobre el calendario de sesiones D1 tal como aparece en los datos limpios (no calendario natural — festivos/fines de semana ya están excluidos de la serie de barras):

1. Sea `month(i)` el mes calendario de la fecha de la barra `i`.
2. **Último día de sesión del mes (LTD)**: la barra `i` es LTD de su mes si `month(i) != month(i+1)` (la barra siguiente pertenece a otro mes).
3. **Señal de entrada**: al close de la barra `LTD - 1` (la sesión inmediatamente anterior al último día de sesión del mes) se genera una señal **LONG** incondicional — sin filtro de racha, momentum, volatilidad ni ningún otro comportamiento reciente del precio. Esto es intencional: la hipótesis es de flujo mecánico por calendario, no de comportamiento de precio (ver `docs/hypotheses/nas100-d1-turn-of-month-flow.md`, sección "Lógica de comportamiento"). `protocol` no añade un filtro de precio que la hipótesis no pide.
4. **Orden**: la señal en `LTD - 1` se ejecuta al **open de la barra `LTD`** (modelo de fill estándar, sección 4 — nunca fill al close de la barra de señal).
5. **Máximo 1 posición abierta a la vez** en esta estrategia/símbolo. Dado que el ciclo (señal→salida) dura ~4-5 sesiones y el siguiente ciclo empieza ~1 mes después, no debería haber solapamiento en circunstancias normales; si por alguna razón (huecos de datos, festivos atípicos) una posición del ciclo anterior sigue abierta cuando aparece una nueva señal, la nueva señal se descarta — no hay pirámide.
6. **La definición de la ventana (día de entrada = LTD, 3 días de sesión del mes siguiente antes del cierre) es estructural, fijada por la literatura citada en la hipótesis (McConnell & Xu 2008 — ventana clásica de 4 días), no un parámetro libre a optimizar** (ver sección 7 y regla dura 10 — anti-minería). Probar otras definiciones de ventana (p. ej. -3/+3, o solo +2 días) es una hipótesis/spec distinta, no una variante silenciosa de esta.

## 3. Regla de salida (numérica — salida por tiempo como eje principal, SL/TP como válvulas de seguridad)

Con `ATR14` = Average True Range de 14 barras (fórmula de Wilder), calculado con datos hasta el close de la barra de señal (`LTD - 1`) inclusive, sin look-ahead.

- **Salida por tiempo (eje principal de esta estrategia — no es un time-stop "opcional", es la lógica de salida central que encapsula la ventana de la hipótesis)**: la posición se cierra al **open de la barra `LTD + 4`** (la cuarta sesión de trading del mes nuevo), salvo que SL o TP se toquen antes. `LTD + 1`, `LTD + 2`, `LTD + 3` son la 1ª, 2ª y 3ª sesión del mes nuevo respectivamente — la posición se sostiene a través del close de esas tres sesiones y se liquida al abrir la cuarta. Esto reproduce la ventana clásica de la literatura (último día del mes + primeros 3 días del mes siguiente) bajo el modelo de fill de la sección 4 (señal→orden siempre en la barra siguiente, nunca al close de la barra de señal, ni en la entrada ni en la salida).
- **Stop loss (válvula de seguridad)**: `SL = entry_price - 1.5 × ATR14`. Se considera tocado si `low[barra] <= SL` en cualquier barra desde la entrada hasta `LTD + 3` inclusive.
- **Take profit (válvula de seguridad)**: `TP = entry_price + 2.5 × ATR14`. Se considera tocado si `high[barra] >= TP` en cualquier barra desde la entrada hasta `LTD + 3` inclusive.
- **Regla de desempate intrabarra**: si en la misma barra D1 el rango `[low, high]` contiene tanto el nivel de SL como el de TP, se asume que se ejecuta el **SL primero** (regla conservadora, igual que en la spec #001 — con datos D1 sin secuencia de ticks no se puede saber el orden real).
- Si ni SL ni TP se tocan entre la entrada y el close de `LTD + 3`, la salida por tiempo (open de `LTD + 4`) gobierna, tal como se describe arriba.

Esto da un holding esperado de **~4 sesiones/noches** (entrada al open de `LTD`, salida al open de `LTD+4` en el caso por tiempo) — consistente con el horizonte declarado en la hipótesis y con el cálculo de costo de swap de la sección 6.

## 4. Modelo de fill explícito

- Señal en el close de una barra `t` → orden a mercado al **open de la barra `t+1`**. Nunca fill al close de la barra de señal — ni en la entrada (`t = LTD-1` → fill en open de `LTD`) ni en la salida por tiempo (`t = LTD+3` → fill en open de `LTD+4`).
- Precio de referencia: **mid** — asunción interina, igual que en `docs/specs/dryrun_bh_sp500.md` y `docs/specs/xauusd-d1-mean-reversion-streak-extension.md`, porque `data/clean/` no distingue bid/ask todavía. `engine` debe declarar el precio real (bid/ask/mid) en `reports/nas100-d1-turn-of-month-flow/data_quality.md` al correr Gate 0. Si Gate 0 declara algo distinto de mid, las fórmulas de fill y de costo de spread de esta sección deben ajustarse antes del backtest.
- El costo de spread (sección 6) se aplica **una vez, al entrar** — convención ya usada en el resto del proyecto, evita contar el spread dos veces.
- SL/TP, si se tocan intrabarra antes de `LTD+4`, se ejecutan al nivel de SL/TP (no al open de la barra siguiente) — es la única excepción al modelo "open de la barra siguiente", igual que en la spec #001, porque son órdenes condicionales ya colocadas, no una señal nueva que requiera esperar la siguiente barra.

## 5. Nota de datos — verificar disponibilidad de fecha de barra antes de implementar

La lógica de la sección 2 depende de poder derivar `month(i)` de la fecha real de cada barra en `data/clean/NAS100/D1/IS.parquet` / `OOS.parquet`. Esto debería ser trivial (el índice de fecha ya existe en los parquet limpios, confirmado en las specs previas), pero `engine` debe verificarlo explícitamente en el Gate 0 / AED antes de codificar la señal — si faltan fechas o hay huecos no explicados alrededor de cambios de mes específicamente, eso es un hallazgo de Gate 0 que puede afectar directamente el conteo de señales de esta estrategia (a diferencia de una estrategia diaria genérica, un hueco justo en el cambio de mes elimina una señal completa de ese ciclo, no solo una barra).

## 6. Costo de bróker y ratio mínimo de expectancy

Fórmulas de `docs/cost_model.md`:
```
cost_roundturn  ≈ spread_model + 2 × commission_per_side + slippage
cost_holding    ≈ swap_long × noches mantenidas (× 3 la noche de swap triple, viernes para índices)
```

Con `tick_size=0.1`, `tick_value=1.0`, `contract_size=10.0` → valor por punto por lote = `tick_value / tick_size` = **10 USD/punto/lote**.

- `spread_cost` = 9 puntos × 10 = **$90/lote** (una vez, entrada — ver sección 0, foto puntual usada como aproximación, no "típico" confirmado).
- `commission_cost` = 2 × 2.75 = **$5.50/lote** (CONFIRMED).
- `slippage_cost` = 2 puntos × 10 = **$20/lote** (estimación conservadora, no confirmada — aplicada una vez por roundturn, siguiendo la convención de la fórmula de `docs/cost_model.md`, que no duplica el término de slippage como sí hace explícitamente con comisión).
- `cost_roundturn` total = 90 + 5.50 + 20 = **$115.50/lote**.

**`cost_holding` — esto NO es un dato incierto, es 100% calculable por `engine` a partir de la fecha real de cada ciclo** (a diferencia de spread/slippage, que sí son estimaciones). Cada uno de los 4 tramos nocturnos (`LTD→LTD+1`, `LTD+1→LTD+2`, `LTD+2→LTD+3`, `LTD+3→LTD+4`) se paga a `-45.73 USD/noche/lote`, salvo el tramo cuya barra de origen sea **viernes** (swap_rollover3days=5), que se paga ×3. `engine` debe calcular esto operación por operación con las fechas reales, no usar un promedio fijo. Para dimensionar el orden de magnitud en esta spec (análisis por día de semana en que cae `LTD`, el último día de sesión del mes):

- Si `LTD` cae en **lunes**: los 4 tramos son lun→mar, mar→mié, mié→jue, jue→vie — ninguno es el tramo vie→lun (la salida es al open de `LTD+4`=viernes, antes de que se cargue el swap de esa noche). **Sin swap triple.** Costo holding = 4 × -45.73 = **-$182.92/lote**.
- Si `LTD` cae en **martes, miércoles, jueves o viernes**: el tramo `viernes→lunes` cae dentro de la ventana de 4 noches en los cuatro casos. **Con swap triple.** Costo holding = 3 × -45.73 + 1 × (-45.73 × 3) = -137.19 + -137.19 = **-$274.38/lote**.

Asumiendo que el día de la semana en que cae el último día de sesión del mes se reparte aproximadamente uniforme entre los 5 días hábiles (no hay razón estructural fuerte para esperar sesgo, aunque no se ha verificado empíricamente contra el calendario real), **~80% de los ciclos (4 de 5 días de la semana posibles para `LTD`) incluyen la noche de swap triple del viernes**. Por instrucción de Alexander de usar aproximaciones conservadoras donde haya duda, el caso "con swap triple" (**-$274.38/lote**) se usa como referencia para el piso del ratio de fricción de esta spec, no el caso optimista de lunes.

**Costo total por ciclo (referencia para el gate, `engine` debe recalcular exacto por operación)**:
- Caso optimista (LTD=lunes, ~20% de ciclos): 115.50 + 182.92 = **$298.42/lote**.
- Caso típico/conservador (LTD=martes-viernes, ~80% de ciclos): 115.50 + 274.38 = **$389.88/lote**.

**Ratio de fricción mínimo (CLAUDE.md regla 17)**: `expectancy neta promedio por operación / costo total promedio por operación ≥ 3.0`. Usando el costo conservador (~$389.88/lote) como referencia, esto exige una expectancy neta promedio ≥ **~$1,170/lote por ciclo** para pasar el gate — una barra alta, coherente con que esta es la estrategia con peor estructura de costo de financiamiento del universo activo (solo-largo sobre el `swap_long` más negativo de los 10 símbolos, sin nunca beneficiarse de `swap_short`). Este piso **no se relaja** — ni por la falta de confirmación de spread/slippage (que ya jugaría en contra, no a favor, de relajarlo) ni por la baja convicción a priori que la propia hipótesis declara.

## 7. Riesgo por operación / sizing

- Riesgo fijo: **0.5% del equity de referencia por operación** (más conservador que el 1.0% usado en la spec #001 — razón concreta: esta hipótesis tiene menor convicción a priori declarada por `investigator`, sección "Por qué el edge no se ha comprimido del todo" de la hipótesis origen, y la peor estructura de costo de financiamiento del universo; no es un ajuste arbitrario).
- `lotes = (equity × 0.005) / (distancia_SL_en_precio × 10)`, donde `distancia_SL_en_precio = 1.5 × ATR14` (en puntos) y `10 = tick_value/tick_size` (valor por punto por lote, sección 6).
- Equity de referencia: `engine` debe fijar un capital nominal inicial explícito y documentarlo — recomendado **100,000 USD**, por consistencia con la spec #001 y reproducibilidad del sizing porcentual entre estrategias del proyecto. Si usa otro valor, debe decirlo en su reporte, no asumirlo en silencio.
- Sin martingala, sin incremento de tamaño tras pérdidas/ganancias. Tamaño se recalcula en cada entrada nueva según el equity vigente (compounding simple).

## 8. Parámetros libres y componentes estructurales

Parámetros libres optimizables (dentro del tope de 3-4 de CLAUDE.md regla 16 — aquí se usan **2**, deliberadamente por debajo del techo, dado que esta estrategia dispara ~12 señales/año, muy por debajo de la frecuencia de la spec #001, y menos operaciones significa menos tolerancia a sobreajuste por parámetro libre):

1. Multiplicador de SL (default 1.5×ATR14)
2. Multiplicador de TP (default 2.5×ATR14)

**Fijos, no optimizables** (estructurales, definidos por la literatura citada en la hipótesis, no por ajuste a la curva de equidad — regla dura 10, anti-minería):
- Periodo de ATR: 14 (convención estándar, no se optimiza).
- Día de entrada de la señal: `LTD - 1` → fill en `LTD` (definición de "último día del mes", fijada por la hipótesis).
- Longitud de la ventana de salida por tiempo: 4 sesiones (`LTD` a `LTD+4`), ventana clásica de McConnell & Xu (2008) citada como fuente principal más cercana en clase de activo.

Componentes estructurales (señal de entrada por calendario, filtro de dirección solo-largo, SL, TP, salida por tiempo, sizing por riesgo fijo) = 6, dentro de la zona sana documentada (4-8).

Análisis de sensibilidad obligatorio (CLAUDE.md regla 14): ±10-20% sobre cada uno de los 2 parámetros libres (SL mult, TP mult), mínimo 200 iteraciones tipo Montecarlo. La curva con los valores default de esta spec debe quedar en el centro del abanico resultante, no ser la más ganadora.

## 9. División In-Sample / Out-of-Sample

- Split: **70% IS / 30% OOS**, cronológico, por defecto.
- Rutas: `data/clean/NAS100/D1/IS.parquet` y `data/clean/NAS100/D1/OOS.parquet` — `protocol` no ha abierto ninguno de los dos para escribir esta spec. `engine` solo lee IS durante el desarrollo; `validator` abre OOS una sola vez, al final (regla dura 13).
- Este split queda **fijo** desde este punto. Ni `engine` ni `validator` lo recortan ni lo desplazan después de ver resultados OOS (regla dura 4 y 13).
- Metodología real de validación dentro del IS: **walk-forward por ventanas** (regla dura 18), no un único ajuste estático. Dado que esta estrategia dispara ~12 señales/año (muy inferior a la spec #001), se propone: ventana de entrenamiento de **4 años** (~48 señales), ventana de prueba de **1 año** (~12 señales), avanzando 1 año por paso (rolling, no anchored), repitiendo hasta agotar el IS disponible. El número exacto de folds depende del rango real de fechas de `IS.parquet`, que `engine` debe inventariar antes de correr el walk-forward — no se asume aquí cuántos años de histórico hay disponibles.

## 10. Puerta de baseline obligatoria (comprar y mantener, mismo símbolo/timeframe)

**No se ha corrido todavía comprar-y-mantener neto para NAS100** (a diferencia de SP500, XAUUSD y EURUSD, ya corridos en `reports/dryrun_costs_comparativa.md` — ver `PROJECT_STATE.md`). No se asume el resultado. Antes de que `validator` pueda aplicar esta puerta, se necesita un dry-run análogo (`scripts/dryrun_bh.py --alias NAS100`, mismo patrón que los 3 ya corridos) sobre `data/clean/NAS100/D1/OOS.parquet` específicamente (CLAUDE.md regla 19 exige la misma ventana OOS, no la ventana histórica completa).

**Contexto direccional, no el número final de la puerta**: `NAS100` tiene el `swap_long` más negativo de los 10 símbolos activos del universo (-45.73/noche, ver `docs/cost_model.md` sección LIVE) — más negativo que SP500 (-11.03, cuyo B&H neto ya dio -11,062.16 sobre la ventana completa) y que XAUUSD en términos relativos al tamaño de la posición. Es razonable esperar que un B&H de años en NAS100 sea también fuertemente negativo neto de swap, posiblemente el peor de los tres ya probados — pero esto **no se declara como hecho aquí**, es una expectativa a confirmar con el dry-run real. `validator` debe correr el número real sobre el slice OOS antes de aplicar el gate.

**El piso de esta puerta no es cero** de forma consistente con el resto del proyecto (decisión de sesión 2026-09-22 en `PROJECT_STATE.md`): si el B&H neto de NAS100 en la ventana OOS resulta negativo, la estrategia no queda aprobada solo por "perder menos que el baseline" — tiene que demostrar edge por encima del costo real de financiamiento y no solo acertar la dirección del precio. Dado que esta propia estrategia también paga `swap_long` (aunque solo 4 noches por ciclo, no años), el mismo principio aplica a escala menor: superar el B&H no es suficiente por sí solo si el ratio de fricción de la sección 6 no se cumple de forma independiente.

## 11. Puertas numéricas de aprobación

Hereda los defaults de CLAUDE.md salvo donde se justifica un ajuste específico (ninguno se relaja sin visto bueno explícito de Alexander):

1. **Profit factor OOS > 1.3** (default CLAUDE.md).
2. **p-valor de test de permutación < 0.05** (default CLAUDE.md) — `validator` debe tratar este umbral con cautela adicional dado el bajo número de operaciones esperado (~12/año), no relajarlo, pero sí reportar el tamaño de muestra junto al p-valor para que la lectura sea honesta.
3. **Máximo drawdown OOS ≤ 20% del capital nominal de referencia** (mismo default que la spec #001, sin razón concreta identificada todavía para ajustarlo; si Alexander prefiere otro número dado el perfil de menor convicción de esta hipótesis, se ajusta antes de la primera validación real).
4. **Ratio de fricción ≥ 3.0** (expectancy neta / costo total, sección 6) — sin relajar. Umbral de referencia: expectancy neta promedio ≥ ~$1,170/lote por ciclo (usando el costo conservador de la sección 6).
5. **Supera el B&H neto de NAS100 D1 en la misma ventana OOS**, mismos costos (sección 10) — piso no-cero, resultado todavía no conocido (a diferencia de SP500/XAUUSD/EURUSD, ya corridos). `validator` debe correr el dry-run antes de aplicar este gate, no asumir el signo.
6. **Sensibilidad de parámetros** ±10-20%, ≥200 iteraciones Montecarlo, curva original en el centro del abanico (sección 8).
7. **Mínimo 30 operaciones en OOS.** Dado que la frecuencia de señal es ~12/año, esto exige ≥2.5 años de cobertura OOS real. Si el 30% de OOS del histórico disponible produce menos de 30 ciclos completos, el resultado se marca **`INVALID_POR_DATOS`** por muestra insuficiente (CLAUDE.md regla 20) — no se fuerza un veredicto de aprobación o rechazo con baja muestra, y no se baja este umbral solo para poder emitir un veredicto.
8. **Gate 0 no puede ser mejor que `APTO_CON_RESERVAS`** mientras `spread_typical_points` y `slippage_points` de `cost_key=index_us` sigan `SIN_CONFIRMAR` (sección 0). `validator` no emite aprobación final sobre ese veredicto sin confirmación explícita adicional de Alexander — usa `INVALID_POR_DATOS` en su lugar si Alexander no se ha pronunciado para entonces (CLAUDE.md regla 20).
9. **Diagnóstico de deterioro temporal (no es puerta numérica de paso/no-paso, es reporte obligatorio)**: la hipótesis origen cita evidencia académica reciente (fuente 4, ScienceDirect 2024) de que el efecto turn-of-month desapareció en mercados de EE.UU. después de 2001, y evidencia de nivel 2-3 (Quantseeker, sobre QQQ específicamente) de que se diluyó "gradualmente a cero" con el tiempo. `engine` debe reportar el desempeño segmentado en al menos 2 mitades cronológicas del IS+OOS disponible (o terciles si el histórico lo permite), para que `validator` pueda ver si el edge está concentrado en el tramo más antiguo de los datos y desapareciendo en el tramo más reciente — sin esto, `validator` no tiene base para evaluar ese caveat, que es el riesgo más alto declarado explícitamente por la propia hipótesis.

## 12. Número de hipótesis

**Hipótesis #002** de `docs/hypotheses/_registry.md` (`nas100-d1-turn-of-month-flow`, 2026-09-22). Segunda hipótesis del proyecto — `validator` debe tener en cuenta que, a la fecha de esta spec, hay 2 hipótesis en total probadas/en curso (N=2: #001 `xauusd-d1-mean-reversion-streak-extension`, ya con spec, y esta). El registro de control de sobreajuste por múltiples pruebas debe reflejar N=2 al momento de evaluar el p-valor de esta estrategia (regla dura 22).
