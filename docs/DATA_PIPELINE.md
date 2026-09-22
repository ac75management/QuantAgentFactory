# Pipeline de datos — QuantAgentFactory (Darwinex MT5)

Orden fijo. No saltarse pasos ni correrlos fuera de orden — cada script asume que el anterior ya corrió.

## Requisitos
```
pip install MetaTrader5 pandas pyarrow
```

## Pasos (Windows)

1. Abrir el terminal Darwinex MT5 y loguearse en la cuenta (demo o real). Dejarlo abierto — todos los scripts que hablan con MT5 lo necesitan corriendo.

2. Descargar OHLC D1 y H4 del universo activo:
   ```
   python scripts/extract_darwinex_ohlc.py
   ```
   Escribe `data/raw/darwinex/<SYMBOL>_<TF>.parquet`. Solo usa los `symbol_mt5` de `docs/universe.md` con `status=active` — `BTCUSD` (blocked) y `DAX` (pending) quedan fuera hasta que se les cambie el status ahí.

3. Normalizar y cortar 70/30 IS/OOS:
   ```
   python scripts/build_clean_data.py
   ```
   Escribe `data/clean/<SYMBOL>/<TF>/IS.parquet` y `OOS.parquet`, más `data/clean/manifest.json`.

4. Capturar costos reales de la cuenta (spread, swap, tamaño de contrato — la comisión casi nunca viene, queda para completar a mano):
   ```
   python scripts/extract_darwinex_costs.py
   ```
   Escribe `docs/cost_snapshots/<YYYYMMDD_HHMM>.json` y actualiza la sección LIVE de `docs/cost_model.md`.

5. Correr el Gate 0 de calidad de datos sobre lo ya limpio:
   ```
   python scripts/run_gate0.py
   ```
   Escribe `reports/_data_quality/<SYMBOL>_<TF>.md` por serie, y agrega `verdict_gate0` a cada entrada de `data/clean/manifest.json`. El veredicto no puede ser mejor que `APTO_CON_RESERVAS` mientras el `cost_key` del símbolo siga en `SIN_CONFIRMAR` en `docs/cost_model.md` — por eso el paso 4 va antes que este.

## BTCUSD y DAX
Fuera del pipeline hasta que su fila en `docs/universe.md` diga `status=active` con un `symbol_mt5` confirmado. `extract_darwinex_ohlc.py` los ignora tal cual está configurado — no hace falta comentar nada a mano, basta con cambiar el status cuando se resuelvan.

## Qué no hace este pipeline todavía
- No corre AED ni backtests — eso es trabajo del agente `engine`, sobre `data/clean/`, después de que Gate 0 dé un veredicto.
- No confirma comisión por operación — sigue siendo manual (Darwinex → tipo de cuenta → tabla de comisiones), rellenar en `docs/cost_model.md`.
- No toca `investigator`, `protocol`, `engine` ni `validator`.
