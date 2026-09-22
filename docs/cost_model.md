# Modelo de costos de bróker — QuantAgentFactory (Darwinex MT5)

`protocol` y `engine` usan estos valores para calcular el ratio de fricción (CLAUDE.md regla 17) y para descontar costos del backtest. Mientras cualquier campo relevante siga en `SIN_CONFIRMAR`, el Gate 0 (`.claude/skills/data-quality-check/SKILL.md`) limita el veredicto a `APTO_CON_RESERVAS` como máximo — ver ahí.

## Fórmulas
```
cost_roundturn  ≈ spread_model + 2 × commission_per_side + slippage
cost_holding    ≈ swap × noches mantenidas (× 3 la noche de swap triple —
                   ver swap_triple_day abajo, YA NO es "no asumir miércoles":
                   confirmado por clase de activo, distinto según el grupo)
```

## Regla: nunca 0 en silencio
Un campo sin confirmar dice `SIN_CONFIRMAR`, nunca `0`. Cero es indistinguible de "no cobra nada" e infla la expectancy de forma artificial. `protocol` no genera spec sobre un símbolo cuyo `cost_key` tenga campos relevantes en `SIN_CONFIRMAR`, salvo confirmación explícita de Alexander para avanzar igual con el hueco documentado.

## Comisión y día de swap triple — confirmado para todo el universo (2026-09-22)

Fuente: tabla pública oficial de Darwinex (`darwinex.com/forex-cfds/{forex,indices,commodities}`, actualizada por Darwinex 2026-09-21 15:32 UTC, capturada hoy vía navegador) — no es una búsqueda genérica, es la página de tarifas retail del propio bróker, y cruza exactamente con los valores ya capturados de la cuenta real en la Sección LIVE (spread/swap/contract_size) y con la ventana de especificación de XAUUSD confirmada a mano. Dos fuentes independientes (página pública + cuenta real) coinciden número por número.

**Hallazgo nuevo importante**: el día de swap triple NO es "generalmente miércoles" — está fijado por clase de activo, y ahora está confirmado:
- **Forex** (todos los pares del universo): miércoles ×3. Excepción documentada por Darwinex: USDCAD sería jueves ×3 (no está en nuestro universo, dato de contexto).
- **Commodities** (metal/energy — XAUUSD, XAGUSD, PETROLEO): miércoles ×3.
- **Índices** (US30, NAS100, SP500, DAX): **viernes ×3**, no miércoles — distinto de FX/commodities.
- Esto decodifica retroactivamente el campo `swap_rollover3days` ya capturado en la Sección LIVE: `3` = miércoles, `5` = viernes (es el enum de día de semana de MT5, no un multiplicador) — coincide exactamente: FX/metal/energy tienen `3` en la Sección LIVE, los 4 índices tienen `5`.

Esto NO sube el `status` de fila completa a `CONFIRMED` en la tabla de abajo — sigue habiendo campos abiertos (`spread_typical_points`/`spread_stress_mult`/`slippage_points`, ver nota tras la tabla). Lo que cambia es que la razón de la reserva ya no es "comisión sin confirmar" (eso quedó resuelto), es específicamente spread-modelo/slippage.

## Por cost_key (spread/slippage siguen siendo un placeholder orientativo — comisión y swap ya no)

| cost_key | spread_typical_points | spread_stress_mult | commission_per_side | commission_unit | slippage_points | swap_long | swap_short | swap_triple_day | contract_size | tick_value | source comisión | as_of | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fx | SIN_CONFIRMAR | SIN_CONFIRMAR | 2.5 | [moneda base del par]/lado/1.0 lote (ej. EUR en EURUSD, GBP en GBPUSD, USD en USDJPY -- no siempre EUR) | SIN_CONFIRMAR | ver Sección LIVE | ver Sección LIVE | miércoles | ver Sección LIVE | ver Sección LIVE | Darwinex, tabla pública forex-cfds/forex, 2026-09-21 | 2026-09-22 | SIN_CONFIRMAR (spread/slippage) |
| index_us | SIN_CONFIRMAR | SIN_CONFIRMAR | ver tabla "Por símbolo" | USD/contrato | SIN_CONFIRMAR | ver Sección LIVE | ver Sección LIVE | viernes | ver Sección LIVE | ver Sección LIVE | Darwinex, tabla pública forex-cfds/indices, 2026-09-21 | 2026-09-22 | SIN_CONFIRMAR (spread/slippage) |
| index_eu | SIN_CONFIRMAR | SIN_CONFIRMAR | 2.75 | EUR/contrato (DAX/GDAXI, único símbolo de este cost_key en el universo) | SIN_CONFIRMAR | ver Sección LIVE | ver Sección LIVE | viernes | ver Sección LIVE | ver Sección LIVE | Darwinex, tabla pública forex-cfds/indices, 2026-09-21 | 2026-09-22 | SIN_CONFIRMAR (spread/slippage) |
| metal | SIN_CONFIRMAR | SIN_CONFIRMAR | 0.0025% valor orden | % valor orden, por lado (in y out deals) | SIN_CONFIRMAR | ver Sección LIVE | ver Sección LIVE | miércoles | ver Sección LIVE | ver Sección LIVE | Darwinex, tabla pública forex-cfds/commodities, 2026-09-21 | 2026-09-22 | SIN_CONFIRMAR (spread/slippage) |
| energy | SIN_CONFIRMAR | SIN_CONFIRMAR | 0.0025% valor orden | % valor orden, por lado (in y out deals) | SIN_CONFIRMAR | ver Sección LIVE | ver Sección LIVE | miércoles | ver Sección LIVE | ver Sección LIVE | Darwinex, tabla pública forex-cfds/commodities, 2026-09-21 | 2026-09-22 | SIN_CONFIRMAR (spread/slippage) |
| crypto | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | — (BTCUSD bloqueado) | — | SIN_CONFIRMAR |

**Por qué el `status` sigue en `SIN_CONFIRMAR` aunque comisión y swap ya estén confirmados**: la columna `status` de esta tabla es agregada (cubre toda la fila, la usa Gate 0 como techo binario) — `spread_typical_points`/`spread_stress_mult` (el spread real es `floating`, la Sección LIVE da una foto puntual, no una distribución típica) y `slippage_points` (ningún bróker publica esto, depende de ejecución real) siguen abiertos para todo el universo. Gate 0 (`SKILL.md`) sigue topando en `APTO_CON_RESERVAS` por esos dos campos — ya no por comisión ni por el día de swap triple, eso quedó resuelto hoy.

`metal`/`energy`: swaps diarios materiales — no asumir que son despreciables solo porque el símbolo suele operarse a corto plazo; confirmar antes de aprobar cualquier estrategia con holding > 1 día.

## Por símbolo (la comisión de índices varía por instrumento, el cost_key genérico no alcanza)

| alias | symbol_mt5 | commission_per_side | commission_unit | source | as_of | status |
|---|---|---|---|---|---|---|
| SP500 | SP500 | 0.275 | USD/contrato | Darwinex, tabla pública forex-cfds/indices, 2026-09-21 15:32 UTC | 2026-09-22 | CONFIRMED |
| NAS100 | NDX | 2.75 | USD/contrato | Darwinex, tabla pública forex-cfds/indices, 2026-09-21 15:32 UTC | 2026-09-22 | CONFIRMED |
| US30 | WS30 | 0.35 | USD/contrato | Darwinex, tabla pública forex-cfds/indices, 2026-09-21 15:32 UTC | 2026-09-22 | CONFIRMED |
| XAUUSD | XAUUSD | 0.0025 | % valor orden, cobrado por lado (in y out deals) | Darwinex MT5, ventana "Especificación del símbolo" de la cuenta real (captura manual de Alexander, 2026-09-22) + confirmado también por la tabla pública forex-cfds/commodities | 2026-09-22 | CONFIRMED |

Esta tabla de "Por símbolo" solo cubre `commission_per_side` (por eso su `status` SÍ puede decir `CONFIRMED` en limpio, sin la salvedad de spread/slippage de la tabla `Por cost_key` de arriba). Los valores web-orientativos que ya estaban puestos como placeholder (SP500=0.275, NAS100=2.75, US30=0.35) resultaron ser exactamente correctos — la tabla pública de Darwinex los confirma número por número.

**Nota XAUUSD:** de paso quedan confirmados: swap triple es miércoles ×3 para todo el grupo `metal`/`energy` (no solo XAUUSD, ver tabla de arriba), sesión de trading Lun-Vie ~01:01-23:59 (server time), cierre viernes 23:55, apalancamiento inicial 5% (~20x). Spread sigue `floating` (no fijo) — el valor de `spread_points` en la sección LIVE es una foto puntual, no una constante.

## Regla de uso
- Si un símbolo de `docs/universe.md` no tiene su `cost_key` (o su fila individual) con todos los campos relevantes confirmados, `protocol` lo marca "bloqueada por costos".
- Comisión y día de swap triple ya están confirmados para todo el universo activo (ver arriba). Spread-modelo (típico/estrés) y slippage siguen siendo placeholder hasta que Alexander los confirme o se decida una fuente para ellos.
- La comisión real casi nunca la expone `symbol_info()` de MT5 — hay que confirmarla consultando el tipo de cuenta en Darwinex y escribirla a mano en las tablas de arriba (no en la sección LIVE, que es autogenerada).

## Sección LIVE (autogenerada por scripts/extract_darwinex_costs.py — no editar a mano)

Último snapshot: `docs/cost_snapshots/20260922_1122.json`, capturado 2026-09-22T03:45:06.881861+00:00.

| alias | symbol_mt5 | spread_points | swap_long | swap_short | swap_rollover3days | contract_size | tick_value | tick_size | commission_source |
|---|---|---|---|---|---|---|---|---|---|
| XAUUSD | XAUUSD | 55 | -62.6 | 35.4 | 3 | 100.0 | 1.0 | 0.01 | manual/web |
| XAGUSD | XAGUSD | 25 | -8.6 | 6.9 | 3 | 5000.0 | 5.0 | 0.001 | manual/web |
| US30 | WS30 | 4 | -7.4 | 3.08 | 5 | 1.0 | 1.0 | 1.0 | manual/web |
| NAS100 | NDX | 9 | -45.73 | 18.53 | 5 | 10.0 | 1.0 | 0.1 | manual/web |
| SP500 | SP500 | 6 | -11.03 | 4.58 | 5 | 10.0 | 1.0 | 0.1 | manual/web |
| USDJPY | USDJPY | 8 | 0.0 | 0.0 | 3 | 100000.0 | 0.6349246661883567 | 0.001 | manual/web |
| EURUSD | EURUSD | 4 | -8.3 | 0.9 | 3 | 100000.0 | 1.0 | 1e-05 | manual/web |
| GBPUSD | GBPUSD | 7 | -4.7 | -2.7 | 3 | 100000.0 | 1.0 | 1e-05 | manual/web |
| PETROLEO | XTIUSD | 5 | 137.3 | -208.0 | 3 | 1000.0 | 10.0 | 0.01 | manual/web |
| DAX | GDAXI | 50 | -27.69 | 4.77 | 5 | 10.0 | 1.14712 | 0.1 | manual/web |

Esta tabla confirma spread/swap/tamaño de contrato con la cuenta real. `commission_per_side` sigue sin confirmar aquí — MT5 no la expone vía `symbol_info()` para cuentas Darwinex. Rellenarla a mano en las tablas "Por cost_key" / "Por símbolo" de este documento, consultando el tipo de cuenta real, y marcar `status=CONFIRMED` ahí (esta sección LIVE no se toca a mano, se regenera corriendo el script de nuevo).
`tick_size` es `trade_tick_size`/`point` de MT5 (el movimiento mínimo de precio). P&L en moneda de cuenta = (precio_salida - precio_entrada) / tick_size * tick_value * lotes. No asumir tick_size=1 -- varía por símbolo (SP500=0.1, EURUSD=0.00001, XAUUSD=0.01, ...).
