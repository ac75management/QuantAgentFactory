# Modelo de costos de bróker — QuantAgentFactory (Darwinex MT5)

`protocol` y `engine` usan estos valores para calcular el ratio de fricción (CLAUDE.md regla 17) y para descontar costos del backtest. Mientras cualquier campo relevante siga en `SIN_CONFIRMAR`, el Gate 0 (`.claude/skills/data-quality-check/SKILL.md`) limita el veredicto a `APTO_CON_RESERVAS` como máximo — ver ahí.

## Fórmulas
```
cost_roundturn  ≈ spread_model + 2 × commission_per_side + slippage
cost_holding    ≈ swap × noches mantenidas (× 3 la noche de swap triple —
                   ver swap_rollover3days en la sección LIVE, no asumir que
                   siempre es miércoles, cada bróker/símbolo lo fija distinto)
```

## Regla: nunca 0 en silencio
Un campo sin confirmar dice `SIN_CONFIRMAR`, nunca `0`. Cero es indistinguible de "no cobra nada" e infla la expectancy de forma artificial. `protocol` no genera spec sobre un símbolo cuyo `cost_key` tenga campos relevantes en `SIN_CONFIRMAR`, salvo confirmación explícita de Alexander para avanzar igual con el hueco documentado.

## Por cost_key (valores orientativos — de documentación pública de Darwinex, NO de la cuenta real)

| cost_key | spread_typical_points | spread_stress_mult | commission_per_side | commission_unit | slippage_points | swap_long | swap_short | swap_triple_wednesday | contract_size | tick_value | source | as_of | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fx | SIN_CONFIRMAR | SIN_CONFIRMAR | 2.5 | EUR/lado/1.0 lote | 0.3 pip | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | web_orientativo | 2026-09-24 | SIN_CONFIRMAR |
| index_us | SIN_CONFIRMAR | SIN_CONFIRMAR | ver tabla "Por símbolo" | USD/contrato | 1 pt | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | web_orientativo | 2026-09-24 | SIN_CONFIRMAR |
| index_eu | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | 1 pt | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | — | — | SIN_CONFIRMAR |
| metal | SIN_CONFIRMAR | SIN_CONFIRMAR | 0.0025% valor orden | % valor orden | 0.15 | SIN_CONFIRMAR (material) | SIN_CONFIRMAR (material) | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | web_orientativo | 2026-09-24 | SIN_CONFIRMAR |
| energy | SIN_CONFIRMAR | SIN_CONFIRMAR | 0.0025% valor orden | % valor orden | 0.02 | SIN_CONFIRMAR (material) | SIN_CONFIRMAR (material) | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | web_orientativo | 2026-09-24 | SIN_CONFIRMAR |
| crypto | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | SIN_CONFIRMAR | — | — | SIN_CONFIRMAR |

`metal`/`energy`: swaps diarios materiales — no asumir que son despreciables solo porque el símbolo suele operarse a corto plazo; confirmar antes de aprobar cualquier estrategia con holding > 1 día.

## Por símbolo (la comisión de índices varía por instrumento, el cost_key genérico no alcanza)

| alias | symbol_mt5 | commission_per_side | commission_unit | source | as_of | status |
|---|---|---|---|---|---|---|
| SP500 | SP500 | 0.275 | USD/contrato | web_orientativo, verificar | 2026-09-24 | SIN_CONFIRMAR |
| NAS100 | NDX | 2.75 | USD/contrato | web_orientativo, verificar | 2026-09-24 | SIN_CONFIRMAR |
| US30 | WS30 | 0.35 | USD/contrato | web_orientativo, verificar | 2026-09-24 | SIN_CONFIRMAR |

## Regla de uso
- Si un símbolo de `docs/universe.md` no tiene su `cost_key` (o su fila individual) con todos los campos relevantes confirmados, `protocol` lo marca "bloqueada por costos".
- Todo valor de este documento por encima de la sección LIVE es un placeholder orientativo hasta que `scripts/extract_darwinex_costs.py` corra contra la cuenta real, o Alexander lo confirme a mano.
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
