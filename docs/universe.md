# Universo de símbolos — QuantAgentFactory

Bróker de datos: **Darwinex, vía MT5**, solo lectura. La fuente autoritativa es `config/instruments.json`: contrato, costos, timeframes y estado de cada símbolo. La tabla de abajo es un espejo generado; no se edita a mano. Tras cambiar `config/instruments.json`, regenerarla con `python -m qaf.consistency --write-universe`. El preflight falla si difieren.

- `research`: se puede formular una hipótesis y ejecutarla en IS.
- `pending`: vehículo registrado para una expansión futura (ETF, acciones, futuros, cripto). No se propone hipótesis sobre él.

<!-- qaf:universe:start -->
| alias | symbol_mt5 | clase | timeframes | status |
|---|---|---|---|---|
| XAUUSD | XAUUSD | commodity_cfd | H1, H4, D1 | research |
| XAGUSD | XAGUSD | commodity_cfd | H1, H4, D1 | research |
| US30 | WS30 | index_cfd | H1, H4, D1 | research |
| NAS100 | NDX | index_cfd | H1, H4, D1 | research |
| SP500 | SP500 | index_cfd | H1, H4, D1 | research |
| USDJPY | USDJPY | fx | H1, H4, D1 | research |
| EURUSD | EURUSD | fx | H1, H4, D1 | research |
| GBPUSD | GBPUSD | fx | H1, H4, D1 | research |
| PETROLEO | XTIUSD | commodity_cfd | H1, H4, D1 | research |
| DAX | GDAXI | index_cfd | H1, H4, D1 | research |
| BTCUSD | — | crypto_cfd | H1, H4, D1 | pending |
| ETHUSD | — | crypto | H1, H4, D1 | pending |
| SPY | — | etf | H1, H4, D1 | pending |
| QQQ | — | etf | H1, H4, D1 | pending |
| IWM | — | etf | H1, H4, D1 | pending |
| TLT | — | etf | H1, H4, D1 | pending |
| GLD | — | etf | H1, H4, D1 | pending |
| AAPL | — | equity | H1, H4, D1 | pending |
| MSFT | — | equity | H1, H4, D1 | pending |
| ES | — | future | H1, H4, D1 | pending |
| NQ | — | future | H1, H4, D1 | pending |
| GC | — | future | H1, H4, D1 | pending |
| CL | — | future | H1, H4, D1 | pending |
<!-- qaf:universe:end -->

## Notas de mapeo

- `PETROLEO` usa `XTIUSD` como símbolo MT5 real, no `USOIL`.
- `DAX` usa `GDAXI`.
- `BTCUSD` no existe en la cuenta demo de Darwinex usada para extraer; sigue `pending` hasta que Alexander confirme la cuenta real.
- Qué particiones IS/OOS existen de verdad: `data/clean/manifest.json` (local, no versionado). EURUSD y USDJPY no tienen H1 importado: su corte IS/OOS se fijó con el historial D1/H4 y el H1 de MT5 empieza después del corte (decisión pendiente en `PROJECT_STATE.md`).
- Datos que el bróker no ofrece (COT, order flow, profundidad de mercado, volumen centralizado real) no están disponibles. Una hipótesis que los necesite se declara bloqueada por datos. `tick_volume` es actividad de ticks, no volumen ejecutado.
