# Spec: dryrun_bh_sp500 — Baseline comprar y mantener, SP500

tipo: dry-run (baseline de referencia — no es una estrategia candidata, no se aprueba ni se rechaza)

## Activo y timeframe
- alias: SP500 (`docs/universe.md` → symbol_mt5 `SP500`, cost_key `index_us`, status `active`)
- timeframe: D1
- datos: `data/clean/SP500/D1/IS.parquet` (solo IS — un dry-run también respeta la separación física IS/OOS; OOS no se toca aquí)

## Regla de entrada
Una sola operación: comprar 1 contrato al open de la primera barra de IS. Sin señal, sin indicador — es la definición de comprar y mantener.

## Regla de salida
Mantener hasta el close de la última barra de IS (mark-to-market barra a barra para la curva de equity intermedia). Sin stop loss, sin take profit — un baseline de comprar y mantener no gestiona salida por diseño.

## Riesgo / sizing
1 contrato fijo. No hay gestión de riesgo por operación — el propósito es medir el activo, no una estrategia de sizing.

## Modelo de fill
- Entrada: open de la primera barra de IS + spread_points de `docs/cost_model.md` (sección LIVE, alias SP500).
- Valoración intermedia: close de cada barra.
- Salida: close de la última barra de IS.
- Precio de referencia: mid — `data/clean/` no distingue bid/ask; declarar esto en `reports/dryrun_bh_sp500/data_quality.md` cuando engine corra el Gate 0.

## Costos (`docs/cost_model.md`, sección LIVE, alias SP500, snapshot `20260922_1122`)
- spread_points: 6 (una vez, en la entrada)
- swap_long: -11.03 por noche mantenida en largo (SP500 es CFD de índice — swap diario no despreciable en un holding de años)
- swap_rollover3days: 5 (triple swap una noche/semana — no asumir que siempre es miércoles)
- commission_per_side: 0.275 USD/contrato — **status SIN_CONFIRMAR** en `docs/cost_model.md` (cifra web, no de cuenta real). Se usa igual aquí porque es un dry-run ilustrativo con el hueco documentado, no una estrategia que se aprueba.
- contract_size: 10.0, tick_value: 1.0

## Split IS/OOS
- IS: `data/clean/SP500/D1/IS.parquet` (70% cronológico, ya generado por `scripts/build_clean_data.py`)
- OOS: `data/clean/SP500/D1/OOS.parquet` — no se toca en este dry-run (regla de agentes: solo `validator` abre OOS, y este dry-run no llega a fase `validator` todavía — ver recomendación de orden más abajo en el reporte de chat).

## Puerta de baseline
N/A — esta spec ES el baseline. Su expectancy neta, drawdown y curva de equity son la referencia que toda hipótesis real sobre SP500 deberá superar (regla CLAUDE.md de puerta de baseline obligatoria).

## Puertas numéricas de aprobación
N/A — no es una estrategia candidata, solo se reporta.

## Número de hipótesis (`docs/hypotheses/_registry.md`)
N/A — no nace de `investigator`, es un control metodológico, no una hipótesis de mercado.

## Gate 0
`engine` corre el checklist de `.claude/skills/data-quality-check/SKILL.md` sobre `data/clean/SP500/D1/IS.parquet` igual que en cualquier otra spec, y escribe el veredicto en `reports/dryrun_bh_sp500/data_quality.md`. Se espera `APTO_CON_RESERVAS` (cost_key `index_us` / fila SP500 individual con `commission_per_side` SIN_CONFIRMAR). Por la excepción `tipo: dry-run` añadida a `.claude/agents/engine.md`, `engine` puede continuar sin detenerse a pedir confirmación en chat — pero debe dejar la reserva documentada de forma visible en el reporte.
