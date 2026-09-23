# Modelo de costos — QuantAgentFactory (Darwinex MT5)

Documento explicativo. **Los valores viven solo en `config/instruments.json`** (CLAUDE.md regla 17): `qaf` no lee este archivo y aquí no se copian números, para que no se desincronicen. Si algo de este texto contradice el JSON, manda el JSON.

## Cómo aplica `qaf` los costos (`qaf/costs.py`)

- **Ejecución, por lado:** medio `spread_points` + `slippage_points_per_side` + comisión. La comisión es efectivo por lote (`commission_type: cash`) o una fracción del nocional (`notional_fraction`), convertida con `currency_to_account`.
- **Financiación:** `swap_long` / `swap_short` en efectivo por lote, cobrados en cada instante de rollover (`rollover_timezone` + `rollover_time`). Con `swap_schedule: triple`, el día `triple_weekday` (lunes = 0) cobra ×3.
- **P&L:** (salida − entrada) / `tick_size` × `tick_value` × lotes.
- **Estrés:** el diagnóstico `cost_stress_2x` multiplica spread, slippage, comisión y swap por 2.
- **Ratio de fricción:** neto / costos pagados ≥ 3.0 (regla 17).

## Procedencia confirmada

- **Comisión:** tabla pública de tarifas retail de Darwinex (`darwinex.com/forex-cfds/{forex,indices,commodities}`, actualizada el 2026-09-21). La de XAUUSD también se confirmó con la ventana "Especificación del símbolo" de la cuenta real, capturada por Alexander el 2026-09-22. El forex cobra en la moneda base del par; el JSON la convierte con `currency_to_account`.
- **Día de swap triple:** forex, metales y energía cobran el miércoles; los índices, el viernes. Coincide con `swap_rollover3days` de MT5 (3 = miércoles, 5 = viernes).
- **Spread, swap, tamaño de contrato y tick:** snapshot de MT5 `docs/cost_snapshots/20260922_1122.json` (campo `source_snapshot` de cada símbolo). Los tres snapshots anteriores del mismo día son capturas previas que se conservan como evidencia.

## Qué sigue sin verificar (`costs_verified: false` en todos los símbolos)

- El spread es flotante: el snapshot es una foto, no una distribución típica ni de estrés.
- El slippage es un supuesto: ningún bróker lo publica.
- Los costos son constantes, sin reconstrucción histórica (limitación C4): el swap actual aplicado a precios históricos bajos sobrestima la financiación, sobre todo en el baseline.
- `price_basis: unknown`: no se confirmó si las barras son bid, ask o mid.

Mientras `costs_verified` sea `false`, Gate 0 queda en `RESERVE` y ninguna estrategia pasa de `EXPLORATORY_CANDIDATE` (ver `docs/VALIDATION_ROADMAP.md`).

## Cómo actualizar

1. Capturar un snapshot nuevo: `python scripts/extract_darwinex_costs.py --connect-mt5` (solo lectura; escribe `docs/cost_snapshots/<fecha>.json`).
2. Copiar a mano los campos verificados a `config/instruments.json`, con `as_of` y `source_snapshot` nuevos. El script nunca escribe el contrato.
3. Si cambian los símbolos o timeframes, regenerar el espejo: `python -m qaf.consistency --write-universe`.
4. Poner `costs_verified: true` solo con evidencia documentada para ese símbolo, nunca por defecto.
