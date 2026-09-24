#!/usr/bin/env python3
"""Re-ejecuta 001–009 con spreads reales de MT5 (vs. config anterior)."""

import json
import os
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

# Setup paths
ROOT = Path(__file__).parent.parent
os.chdir(ROOT)

from qaf.io import read_json, write_json, code_hash, digest
from qaf.contracts import validate_spec
from qaf.data import load_is
from qaf.runner import execute

# Load config
config = read_json("config/instruments.json")
policy = read_json("config/runner.json")
hypotheses_catalog = read_json("config/hypotheses.json")

# Map hypothesis IDs to spec files
HYPOTHESIS_SPECS = {
    "001": "config/strategies/dd17fcc6e5927cb422460f9e.json",
    "002": "config/strategies/6bf8c50304e4a65a16b3e2a2.json",
    "003": "config/strategies/5b89c092897b6d5f13d5f732.json",
    "004": "config/strategies/00196adf527efa117f6bc53c.json",
    "005": "config/strategies/db651fa2706cdac64d0c2584.json",
    "006": "config/strategies/ef86590bc29b8758738f96d5.json",
    # 007: no spec (bloqueada por arquitectura)
    "008": "config/strategies/8b32522b34d23eea93fcaf4e.json",
    "009": "config/strategies/040d4ff1fce2ea074e0d7dff.json",
}

output_root = ROOT / "reports/factory"
output_root.mkdir(parents=True, exist_ok=True)

results = []
now = datetime.now(ZoneInfo("America/Guayaquil"))
created = now.isoformat()

print("=" * 70)
print("RE-EJECUCIÓN 001–009 CON SPREADS REALES MT5")
print("=" * 70)

for hyp_id in ["001", "002", "003", "004", "005", "006", "008", "009"]:
    print(f"\n{'='*70}")
    print(f"HIPÓTESIS {hyp_id}")
    print("=" * 70)

    # Load spec
    spec_path = HYPOTHESIS_SPECS.get(hyp_id)
    if not spec_path:
        print(f"✗ No spec found for {hyp_id}")
        continue

    try:
        spec = validate_spec(read_json(spec_path))
    except Exception as e:
        print(f"✗ Spec inválido: {e}")
        continue

    symbol = spec["symbol"]
    timeframe = spec["timeframe"]

    # Load data
    try:
        df, data_info = load_is(symbol, timeframe, ROOT)
        print(f"✓ Datos cargados: {symbol}/{timeframe} ({len(df)} barras)")
    except Exception as e:
        print(f"✗ Error cargando datos: {e}")
        continue

    # Validate instrument config
    if symbol not in config:
        print(f"✗ Símbolo {symbol} no en config")
        continue

    c = config[symbol]

    # Execute
    run_id = digest({"spec": spec, "data": data_info, "costs": c, "policy": policy, "code": code_hash()})[:24]
    print(f"  Run ID: {run_id}")
    print(f"  Spread config: {c.get('spread_points', 'N/A')} points")
    print(f"  Spread CSV: {c.get('spread_csv', 'N/A')}")
    print(f"  Slippage: {c.get('slippage_points_per_side', 'N/A')} points")

    try:
        record, folder = execute(spec, df, data_info, c, policy, run_id, created, str(output_root))
        results.append({
            "hypothesis_id": hyp_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "run_id": run_id,
            "status": record.get("decision", "UNKNOWN"),
            "metrics": record.get("metrics", {}),
            "reserves": record.get("reserves", []),
        })

        # Summary
        metrics = record.get("metrics", {})
        print(f"\n  Decision: {record.get('decision', 'UNKNOWN')}")
        print(f"  Net P&L: {metrics.get('net_pnl', 0):.2f}")
        print(f"  Return %: {metrics.get('return_pct', 0):.2f}%")
        print(f"  Profit Factor: {metrics.get('profit_factor', 0):.2f}")
        print(f"  Max DD %: {metrics.get('max_dd_pct', 0):.2f}%")
        print(f"  AED p-value: {record.get('diagnostics', {}).get('aed_p_value', 'N/A')}")
        print(f"  ✓ Ejecución completada: {folder}")

    except Exception as e:
        print(f"✗ Error ejecutando: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 70)
print("RESUMEN DE RE-EJECUCIONES")
print("=" * 70)

# Summary table
print(f"\n{'ID':<4} {'Symbol':<10} {'TF':<4} {'Decision':<20} {'Net P&L':<12} {'Return %':<12}")
print("-" * 70)

for r in results:
    metrics = r.get("metrics", {})
    print(f"{r['hypothesis_id']:<4} {r['symbol']:<10} {r['timeframe']:<4} {r['status']:<20} {metrics.get('net_pnl', 0):<12.2f} {metrics.get('return_pct', 0):<12.2f}%")

# Save summary
summary_path = output_root / "rerun_summary_realspread.json"
with open(summary_path, "w") as f:
    json.dump({"created_at": created, "results": results}, f, indent=2, ensure_ascii=False)

print(f"\n✓ Resumen guardado en {summary_path}")
print("\nPróximo: comparar con resultados anteriores")
