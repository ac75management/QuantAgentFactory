#!/usr/bin/env python3
"""Extrae spread histórico real de parquets MT5."""

import pandas as pd
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_CLEAN = ROOT / "data/clean"
DATA_SPREADS = ROOT / "data/spreads"
CONFIG = ROOT / "config/instruments.json"

DATA_SPREADS.mkdir(exist_ok=True)

INSTRUMENTS = [
    ("EURUSD", ["H1", "H4", "D1"]),
    ("GBPUSD", ["H1", "H4", "D1"]),
    ("DAX", ["H1", "H4", "D1"]),
]

extracted = {}

for symbol, timeframes in INSTRUMENTS:
    for tf in timeframes:
        parquet_path = DATA_CLEAN / symbol / tf / "IS.parquet"
        if not parquet_path.exists():
            continue

        df = pd.read_parquet(parquet_path)

        if "spread" not in df.columns:
            continue

        csv_name = f"{symbol}_{tf}_spread.csv"
        csv_path = DATA_SPREADS / csv_name

        # Crear CSV simple: timestamp + spread
        output = pd.DataFrame({
            "timestamp": df["time"] if "time" in df.columns else range(len(df)),
            "spread": df["spread"]
        })
        output.to_csv(csv_path, index=False)

        spread_stats = {
            "min": float(df["spread"].min()),
            "max": float(df["spread"].max()),
            "mean": float(df["spread"].mean()),
            "std": float(df["spread"].std()),
        }

        extracted[f"{symbol}/{tf}"] = {
            "rows": len(df),
            **spread_stats,
            "csv": csv_name,
        }

        print(f"✓ {symbol}/{tf}: {len(df)} barras, spread {spread_stats['min']:.0f}-{spread_stats['max']:.0f} (avg {spread_stats['mean']:.1f})")

# Actualizar config
with open(CONFIG) as f:
    config = json.load(f)

for key, data in extracted.items():
    symbol = key.split("/")[0]
    if symbol in config:
        config[symbol]["spread_csv"] = f"data/spreads/{data['csv']}"
        config[symbol]["spread_method"] = "per_bar"
        config[symbol]["spread_source"] = "MT5 histórico real"
        print(f"  → {symbol}: configurado con spread histórico")

with open(CONFIG, "w") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

print(f"\n✓ {len(extracted)} instrumentos extraídos")
print(f"✓ config/instruments.json actualizado")
