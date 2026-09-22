"""
Dry-run minimo, parametrizado: comprar y mantener <ALIAS> D1 sobre la ventana
IS completa, con costos leidos de docs/cost_model.md y docs/universe.md (no
hardcodeados por simbolo -- mismo principio de coherencia de nombres que el
resto del pipeline).

NO es el backtest de nivel `engine` (ese corre Gate 0 formal, AED,
reproducibilidad con semilla, via el agente `engine` sobre una spec en
docs/specs/). Es una cifra rapida de referencia, misma logica de costos en
cada simbolo: spread (1x, entrada) + comision roundturn (2x, plana o % del
valor de orden segun docs/cost_model.md) + swap acumulado (docs/cost_model.md,
seccion LIVE).

Uso:
    python scripts/dryrun_bh.py --alias SP500
    python scripts/dryrun_bh.py --alias SP500 EURUSD XAUUSD
"""
import argparse
import re
import sys
from pathlib import Path

import pandas as pd

from costs import (
    price_pnl_per_lot,
    spread_cost_per_lot,
    swap_cost_per_lot,
)

ROOT = Path(__file__).resolve().parent.parent
UNIVERSE_PATH = ROOT / "docs" / "universe.md"
COST_MODEL_PATH = ROOT / "docs" / "cost_model.md"
CLEAN_DIR = ROOT / "data" / "clean"


def parse_table(text, header_prefix):
    """Filas (dict columna->celda) de la primera tabla markdown cuyo encabezado
    empiece con header_prefix. Generico -- no asume numero de columnas."""
    lines = text.splitlines()
    rows = []
    in_table = False
    header_cells = None
    for line in lines:
        stripped = line.strip()
        if not in_table and stripped.startswith(header_prefix):
            in_table = True
            header_cells = [c.strip() for c in stripped.strip("|").split("|")]
            continue
        if in_table:
            if not stripped.startswith("|"):
                if rows:
                    break
                continue
            if set(stripped.replace("|", "").strip()) <= {"-", " "}:
                continue  # fila separadora ---|---
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            rows.append(dict(zip(header_cells, cells)))
    return rows


def load_universe_row(alias):
    text = UNIVERSE_PATH.read_text(encoding="utf-8")
    for row in parse_table(text, "| alias | symbol_mt5 | type |"):
        if row.get("alias") == alias:
            return row
    return None


def load_live_row(alias):
    text = COST_MODEL_PATH.read_text(encoding="utf-8")
    for row in parse_table(text, "| alias | symbol_mt5 | spread_points |"):
        if row.get("alias") == alias:
            return row
    return None


def load_symbol_commission(alias):
    text = COST_MODEL_PATH.read_text(encoding="utf-8")
    for row in parse_table(text, "| alias | symbol_mt5 | commission_per_side |"):
        if row.get("alias") == alias:
            return row
    return None


def load_costkey_commission(cost_key):
    text = COST_MODEL_PATH.read_text(encoding="utf-8")
    for row in parse_table(text, "| cost_key | spread_typical_points |"):
        if row.get("cost_key") == cost_key:
            return row
    return None


def extract_number(raw):
    m = re.search(r"[\d.]+", raw)
    return float(m.group()) if m else None


def resolve_commission_roundturn(alias, cost_key, entry_price, contract_size):
    """Devuelve (costo_roundturn_en_moneda_cuenta, descripcion, status)."""
    row = load_symbol_commission(alias)
    source = f"docs/cost_model.md, tabla 'Por símbolo', alias={alias}"
    if row is None:
        row = load_costkey_commission(cost_key)
        source = f"docs/cost_model.md, tabla 'Por cost_key', cost_key={cost_key}"
    if row is None:
        return None, "sin fila de comision encontrada", "DESCONOCIDO"

    raw_value = row.get("commission_per_side", "")
    unit = row.get("commission_unit", "")
    status = row.get("status", "DESCONOCIDO")
    pct = extract_number(raw_value)

    if "%" in raw_value or "%" in unit:
        notional = entry_price * contract_size
        per_side = pct / 100 * notional
        desc = f"{pct}% del valor de orden ({notional:,.2f}) -- {source} (status={status})"
    else:
        per_side = pct
        desc = f"{pct} {unit} por lado -- {source} (status={status}, sin conversion de divisa)"

    return per_side * 2, desc, status


def run_dryrun(alias):
    universe_row = load_universe_row(alias)
    if universe_row is None:
        print(f"FAIL {alias}: no esta en docs/universe.md")
        return None
    cost_key = universe_row["cost_key"]

    live_row = load_live_row(alias)
    if live_row is None:
        print(f"FAIL {alias}: sin fila en la seccion LIVE de docs/cost_model.md (¿corriste extract_darwinex_costs.py?)")
        return None

    is_path = CLEAN_DIR / alias / "D1" / "IS.parquet"
    if not is_path.exists():
        print(f"FAIL {alias}: no existe {is_path}")
        return None

    df = pd.read_parquet(is_path).sort_values("time").reset_index(drop=True)
    entry_price = df.loc[0, "open"]
    exit_price = df.loc[len(df) - 1, "close"]
    n_bars = len(df)
    n_nights = n_bars - 1

    tick_value = float(live_row["tick_value"])
    tick_size = float(live_row["tick_size"])
    contract_size = float(live_row["contract_size"])
    spread_points = float(live_row["spread_points"])
    swap_long = float(live_row["swap_long"])

    # P&L = (precio_salida - precio_entrada) / tick_size * tick_value -- NUNCA asumir
    # tick_size=1: SP500=0.1, EURUSD=0.00001, XAUUSD=0.01, ... (ver docs/cost_model.md LIVE)
    gross_pnl = price_pnl_per_lot(entry_price, exit_price, tick_size, tick_value)
    spread_cost = spread_cost_per_lot(spread_points, tick_size, tick_value)
    commission_cost, commission_desc, commission_status = resolve_commission_roundturn(
        alias, cost_key, entry_price, contract_size
    )
    swap_total = swap_cost_per_lot(n_nights, swap_long)
    net_pnl = gross_pnl + swap_total - spread_cost - commission_cost

    result = {
        "alias": alias,
        "bars": n_bars,
        "date_from": str(df.loc[0, "time"]),
        "date_to": str(df.loc[len(df) - 1, "time"]),
        "gross_pnl": gross_pnl,
        "spread_cost": spread_cost,
        "commission_cost": commission_cost,
        "commission_desc": commission_desc,
        "swap_total": swap_total,
        "net_pnl": net_pnl,
    }

    print(f"--- {alias} (D1, IS: {result['date_from']} -> {result['date_to']}, {n_bars} barras) ---")
    print(f"  P&L bruto:            {gross_pnl:,.2f}")
    print(f"  - spread (1x):        -{spread_cost:,.2f}")
    print(f"  - comision (2x):      -{commission_cost:,.2f}  ({commission_desc})")
    print(f"  - swap acumulado:     {swap_total:,.2f}  ({n_nights} noches x {swap_long})")
    print(f"  P&L neto:             {net_pnl:,.2f}")
    print()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--alias", nargs="+", required=True, help="Alias(es) de docs/universe.md, ej. SP500 EURUSD XAUUSD")
    args = parser.parse_args()

    results = []
    for alias in args.alias:
        r = run_dryrun(alias)
        if r:
            results.append(r)

    if len(results) > 1:
        print("=== Comparativa ===")
        print(f"{'alias':10s} {'barras':>7s} {'bruto':>14s} {'spread+com':>12s} {'swap':>14s} {'neto':>14s}")
        for r in results:
            spread_com = r["spread_cost"] + r["commission_cost"]
            print(
                f"{r['alias']:10s} {r['bars']:7d} {r['gross_pnl']:14,.2f} {spread_com:12,.2f} "
                f"{r['swap_total']:14,.2f} {r['net_pnl']:14,.2f}"
            )

    if not results:
        sys.exit(1)


if __name__ == "__main__":
    main()
