#!/usr/bin/env python3
"""Verifica que config lee spread histórico correctamente."""

import pandas as pd
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent
os.chdir(ROOT)

# Cargar config
import json
with open("config/instruments.json") as f:
    config = json.load(f)

for symbol in ["EURUSD", "GBPUSD", "DAX"]:
    if symbol not in config:
        continue

    csv_path = config[symbol].get("spread_csv")
    print(f"\n{symbol}:")
    print(f"  Config: {csv_path}")
    print(f"  Method: {config[symbol].get('spread_method')}")

    if csv_path and os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        print(f"  ✓ CSV encontrado")
        print(f"    Filas: {len(df)}")
        print(f"    Columns: {df.columns.tolist()}")
        print(f"    Spread: min={df['spread'].min():.0f}, max={df['spread'].max():.0f}, mean={df['spread'].mean():.1f}")
    else:
        print(f"  ✗ No encontrado: {csv_path}")

print("\n✓ Verificación completa")
