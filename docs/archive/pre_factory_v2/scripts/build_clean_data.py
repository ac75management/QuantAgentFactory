"""
Limpia y normaliza los OHLC crudos de data/raw/darwinex/, y genera el corte
fisico 70/30 In-Sample/Out-of-Sample que exige CLAUDE.md (reglas 4 y 13).

NO corre el Gate 0 de calidad de datos (.claude/skills/data-quality-check) —
eso lo hace el agente engine sobre data/clean/. Este script solo normaliza
formato y corta fechas. No elimina duplicados ni rellena huecos.

Uso:
    python scripts/build_clean_data.py

Entrada:
    data/raw/darwinex/<SYMBOL>_<TF>.parquet

Salida:
    data/clean/<SYMBOL>/<TF>/IS.parquet
    data/clean/<SYMBOL>/<TF>/OOS.parquet
    data/clean/manifest.json
"""

import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("FALTA pandas/pyarrow. Instala con: pip install pandas pyarrow")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "darwinex"
CLEAN_DIR = ROOT / "data" / "clean"
MANIFEST_PATH = CLEAN_DIR / "manifest.json"

FILENAME_RE = re.compile(r"^(?P<symbol>.+)_(?P<tf>D1|H4)\.parquet$")

IS_FRACTION = 0.70  # CLAUDE.md reglas 4 y 13 — no cambiar aqui sin cambiar la regla


def file_hash(path):
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()[:16]


def normalize(df):
    df = df.copy()
    # columnas tipicas de MT5: time, open, high, low, close, tick_volume, spread, real_volume
    if "volume" not in df.columns:
        if "tick_volume" in df.columns:
            df["volume"] = df["tick_volume"]
        elif "real_volume" in df.columns:
            df["volume"] = df["real_volume"]
        else:
            df["volume"] = pd.NA

    if pd.api.types.is_numeric_dtype(df["time"]):
        # epoch en segundos crudo (ej. si el parquet no paso por extract_darwinex_ohlc.py,
        # que ya lo deja como datetime) -- MT5 siempre reporta time en segundos, no ms/ns.
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    else:
        df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df[["time", "open", "high", "low", "close", "volume"]]
    # No eliminar duplicados aqui: Gate 0 debe poder observarlos y rechazarlos
    # o documentarlos con evidencia reproducible.
    df = df.sort_values("time").reset_index(drop=True)
    return df


def split_is_oos(df, fraction=IS_FRACTION):
    cut = int(len(df) * fraction)
    is_df = df.iloc[:cut].reset_index(drop=True)
    oos_df = df.iloc[cut:].reset_index(drop=True)
    return is_df, oos_df


def process_file(raw_path, manifest_entries):
    match = FILENAME_RE.match(raw_path.name)
    if not match:
        print(f"SKIP {raw_path.name}: nombre no sigue el patron <SYMBOL>_<TF>.parquet")
        return
    symbol, tf = match.group("symbol"), match.group("tf")

    raw_hash = file_hash(raw_path)
    df = pd.read_parquet(raw_path)
    n_before = len(df)
    df = normalize(df)
    n_after = len(df)
    duplicate_timestamps = int(df["time"].duplicated().sum()) if "time" in df else 0

    if len(df) < 10:
        print(f"FAIL {symbol} [{tf}]: menos de 10 barras tras limpiar, no se genera split")
        return

    is_df, oos_df = split_is_oos(df)

    out_dir = CLEAN_DIR / symbol / tf
    out_dir.mkdir(parents=True, exist_ok=True)
    is_path = out_dir / "IS.parquet"
    oos_path = out_dir / "OOS.parquet"
    is_df.to_parquet(is_path, index=False)
    oos_df.to_parquet(oos_path, index=False)

    print(
        f"OK   {symbol} [{tf}]: {n_after} barras normalizadas "
        f"({duplicate_timestamps} timestamps duplicados conservados para Gate 0) "
        f"-> IS={len(is_df)} filas, OOS={len(oos_df)} filas"
    )

    manifest_entries.append({
        "symbol": symbol,
        "timeframe": tf,
        "raw_file": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
        "raw_sha256_16": raw_hash,
        "rows_raw": n_before,
        "rows_clean": n_after,
        "rows_dropped_duplicates_or_invalid": 0,
        "duplicate_timestamps_observed": duplicate_timestamps,
        "rows_is": len(is_df),
        "rows_oos": len(oos_df),
        "date_min": str(df["time"].min()) if n_after else None,
        "date_max": str(df["time"].max()) if n_after else None,
        "is_oos_cutoff_date": str(oos_df["time"].iloc[0]) if len(oos_df) else None,
        "is_fraction": IS_FRACTION,
        "clean_is_path": str(is_path.relative_to(ROOT)).replace("\\", "/"),
        "clean_oos_path": str(oos_path.relative_to(ROOT)).replace("\\", "/"),
    })


def main():
    if not RAW_DIR.exists():
        print(f"No existe {RAW_DIR}. Corre primero scripts/extract_darwinex_ohlc.py")
        sys.exit(1)

    raw_files = sorted(RAW_DIR.glob("*.parquet"))
    if not raw_files:
        print(f"No hay archivos .parquet en {RAW_DIR}. Corre primero scripts/extract_darwinex_ohlc.py")
        sys.exit(1)

    manifest_entries = []
    for raw_path in raw_files:
        process_file(raw_path, manifest_entries)

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated_from": "scripts/build_clean_data.py",
        "is_fraction": IS_FRACTION,
        "note": "NO interpola gaps. NO corre Gate 0 (calidad de datos) -- eso lo hace engine sobre estos archivos.",
        "symbols": manifest_entries,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nManifiesto escrito en {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
