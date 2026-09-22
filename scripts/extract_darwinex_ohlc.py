"""
Extrae OHLC D1 y H4 desde el terminal MT5 de Darwinex para las filas
status=active de docs/universe.md.

Requiere:
- Terminal MT5 de Darwinex abierto y logueado en ESTA MISMA maquina.
- pip install MetaTrader5 pandas pyarrow

Uso:
    python scripts/extract_darwinex_ohlc.py

Salida:
    data/raw/darwinex/<ALIAS>_<TF>.parquet -- <ALIAS> es la columna `alias` de
    docs/universe.md (PETROLEO, DAX, US30, SP500, ...), NUNCA el symbol_mt5.
    El symbol_mt5 (XTIUSD, GDAXI, WS30, ...) se usa solo para hablar con MT5.

No corre Gate 0 ni ningun chequeo de calidad -- eso lo hace el agente engine
sobre data/clean/, despues de scripts/build_clean_data.py.
"""

import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import MetaTrader5 as mt5
except ImportError:
    print("FALTA la libreria MetaTrader5. Instala con: pip install MetaTrader5")
    sys.exit(1)

try:
    import pandas as pd
except ImportError:
    print("FALTA pandas/pyarrow. Instala con: pip install pandas pyarrow")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
UNIVERSE_PATH = ROOT / "docs" / "universe.md"
RAW_DIR = ROOT / "data" / "raw" / "darwinex"

TIMEFRAMES = {"D1": mt5.TIMEFRAME_D1, "H4": mt5.TIMEFRAME_H4}
BAR_COUNT = 100_000  # MT5 devuelve lo que el broker tenga disponible, nunca mas

UNIVERSE_ROW_RE = re.compile(
    r"^\|\s*(?P<alias>[^|]+?)\s*\|\s*(?P<symbol_mt5>[^|]+?)\s*\|\s*(?P<type>[^|]+?)\s*\|"
    r"\s*(?P<tfs>[^|]+?)\s*\|\s*(?P<cost_key>[^|]+?)\s*\|\s*(?P<status>[^|]+?)\s*\|\s*$"
)


def read_active_symbols():
    """Parsea la tabla fija de docs/universe.md y devuelve las filas status=active."""
    if not UNIVERSE_PATH.exists():
        print(f"No existe {UNIVERSE_PATH}")
        return []
    text = UNIVERSE_PATH.read_text(encoding="utf-8")
    rows = []
    for line in text.splitlines():
        m = UNIVERSE_ROW_RE.match(line.strip())
        if not m:
            continue
        d = m.groupdict()
        alias = d["alias"].strip()
        if alias.lower() == "alias" or set(alias) <= {"-"}:
            continue
        if d["status"].strip().lower() == "active":
            rows.append({k: v.strip() for k, v in d.items()})
    return rows


def extract_symbol(entry):
    alias = entry["alias"]
    name = entry["symbol_mt5"]

    if not mt5.symbol_select(name, True):
        print(f"FAIL {alias}: no se pudo seleccionar '{name}' en Market Watch (symbol_mt5 de docs/universe.md)")
        return False

    ok_any = False
    for tf_name, tf_const in TIMEFRAMES.items():
        rates = mt5.copy_rates_from(name, tf_const, datetime.now(), BAR_COUNT)
        if rates is None or len(rates) == 0:
            print(f"FAIL {alias} [{tf_name}]: sin datos devueltos por MT5 (symbol_mt5='{name}')")
            continue
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        out_path = RAW_DIR / f"{alias}_{tf_name}.parquet"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out_path, index=False)
        print(f"OK   {alias} [{tf_name}]: {len(df)} barras -> {out_path} (symbol_mt5='{name}')")
        ok_any = True
    return ok_any


def main():
    if not mt5.initialize(timeout=10_000):
        print(f"FAIL: no se pudo conectar al terminal MT5 en 10s (¿esta abierto y logueado?). Error: {mt5.last_error()}")
        sys.exit(1)

    account = mt5.account_info()
    print(f"Conectado a MT5. Cuenta: {account.login if account else '?'} ({account.server if account else '?'})")

    active_rows = read_active_symbols()
    if not active_rows:
        print(f"No hay filas status=active en {UNIVERSE_PATH}")
        mt5.shutdown()
        sys.exit(1)
    print(f"{len(active_rows)} simbolo(s) activo(s) en docs/universe.md.\n")

    results = {}
    for entry in active_rows:
        results[entry["alias"]] = extract_symbol(entry)

    mt5.shutdown()

    print("\n--- Resumen ---")
    for alias, ok in results.items():
        print(f"{'OK' if ok else 'FAIL'}  {alias}")

    failed = [a for a, ok in results.items() if not ok]
    if failed:
        print(f"\n{len(failed)} simbolo(s) sin datos: {', '.join(failed)}")
        print("Revisa symbol_mt5 en docs/universe.md para esos alias -- este script ya no tiene lista propia que editar.")
    sys.exit(0 if not failed else 2)


if __name__ == "__main__":
    main()
