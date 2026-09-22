# Catálogo de universo — QuantAgentFactory

Bróker: **Darwinex, vía MT5**. Mapeo **fijo** — confirmado contra un terminal Darwinex real el 2026-09-24 (extracción OHLC ya corrida). `investigator`, `protocol` y `engine` consultan este archivo antes de aceptar o codificar una hipótesis. `scripts/extract_darwinex_ohlc.py` y `scripts/extract_darwinex_costs.py` usan **solo** `symbol_mt5` de las filas `status=active` — nada de fallback difuso, ya no hace falta.

| alias | symbol_mt5 | type | tfs | cost_key | status |
|---|---|---|---|---|---|
| XAUUSD | XAUUSD | cfd_metal | D1,H4 | metal | active |
| XAGUSD | XAGUSD | cfd_metal | D1,H4 | metal | active |
| US30 | WS30 | cfd_index | H1,D1,H4 | index_us | active |
| NAS100 | NDX | cfd_index | H1,D1,H4 | index_us | active |
| SP500 | SP500 | cfd_index | H1,D1,H4 | index_us | active |
| USDJPY | USDJPY | cfd_fx | D1,H4 | fx | active |
| EURUSD | EURUSD | cfd_fx | D1,H4 | fx | active |
| GBPUSD | GBPUSD | cfd_fx | D1,H4 | fx | active |
| PETROLEO | XTIUSD | cfd_energy | D1,H4 | energy | active |
| BTCUSD | - | cfd_crypto | - | crypto | blocked |
| DAX | GDAXI | cfd_index | H1,D1,H4 | index_eu | active |

## Notas
- **BTCUSD = blocked**: no existe en la cuenta demo de Darwinex usada para probar. No se reintenta hasta que Alexander confirme si su cuenta real sí lo tiene.
- `PETROLEO` (alias) usa `XTIUSD` como `symbol_mt5` real — confirmado, no `USOIL`.
- `DAX`/`GER40` (alias) usa `GDAXI` como `symbol_mt5` real, `status=active` — confirmado.

## Regla de uso
- `investigator` no propone hipótesis sobre símbolos con `status` distinto de `active` (ni `blocked` ni `pending`), ni sobre datos que este archivo no reconoce como disponibles (COT, order flow, profundidad de mercado), salvo que las declare explícitamente "bloqueada por datos".
- `protocol`/`engine` usan la columna `cost_key` para buscar el costo correspondiente en `docs/cost_model.md`.
- Reactivar `BTCUSD` o `DAX` implica cambiar su `status` a `active` aquí, con `symbol_mt5` confirmado, no antes.
