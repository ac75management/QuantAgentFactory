# Pipeline de datos — QuantAgentFactory (Darwinex MT5)

La extracción es manual, de solo lectura y ocasional: no forma parte de `qaf.cli run`. Conectarse a la cuenta, aunque sea demo, requiere confirmación explícita de Alexander en el chat (CLAUDE.md regla 1). Los símbolos salen de `config/instruments.json` (`status: research` con `symbol_mt5`).

## Requisitos

`.venv\Scripts\python.exe -m pip install MetaTrader5` (dependencia opcional, declarada en `pyproject.toml` como extra `mt5`). El terminal Darwinex MT5 debe estar abierto y con sesión iniciada.

## Pasos

1. **Exportar OHLC** de los timeframes declarados de cada símbolo:
   ```
   python scripts/extract_darwinex_ohlc.py --connect-mt5
   ```
   Escribe un lote nuevo en `data/raw/darwinex/<fecha-hora>/`: un `<ALIAS>_<TF>.parquet` por serie, más `extraction.json`. Sin `--connect-mt5` no se conecta.

2. **Importar y partir 70/30 IS/OOS** ese lote:
   ```
   python scripts/build_clean_data.py --raw-dir data/raw/darwinex/<fecha-hora>
   ```
   Escribe `data/clean/<ALIAS>/<TF>/{IS,OOS}.parquet` y la entrada en `data/clean/manifest.json`, y sella la partición: sha256 de ambos archivos, esquema y rango temporal. Una partición existente nunca se sobreescribe. El corte IS/OOS se fija la primera vez que se importa un símbolo y se reutiliza para sus demás timeframes. Por eso EURUSD y USDJPY no tienen H1: su historial H1 empieza después del corte (`INSUFFICIENT_BEFORE_FIXED_CUTOFF`). No elimina duplicados ni interpola huecos: Gate 0 los reporta.

3. **Capturar costos actuales** (opcional; solo si se van a actualizar):
   ```
   python scripts/extract_darwinex_costs.py --connect-mt5
   ```
   Escribe `docs/cost_snapshots/<fecha-hora>.json`. No modifica `config/instruments.json`: los campos verificados se copian a mano (ver `docs/cost_model.md`, "Cómo actualizar").

4. **Gate 0**. Corre dentro de `qaf.cli run` (`qaf/data.py::inspect_frame`) y queda en `result.json` de cada corrida con estado PASS, RESERVE o FAIL. Para revisar todas las series sin correr estrategias:
   ```
   python scripts/run_gate0.py
   ```
   Escribe `reports/factory/quality.json`.

Particiones sin sello (anteriores al sellado): `python -m qaf.partition seal`.

## Qué no hace

- No corre AED ni backtests: eso es `qaf.cli run`, invocado por `engine`.
- No descarga comisiones: MT5 no las expone en `symbol_info()`. Su procedencia está en `docs/cost_model.md`.
- No abre OOS. `qaf.data.load_is` solo lee IS; de OOS se verifican el hash y el rango temporal, sin leer precios.
