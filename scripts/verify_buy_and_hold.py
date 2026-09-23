"""
Re-verificacion de comprar-y-mantener usando el motor de costos ya auditado
de `qaf` (qaf.costs / qaf.data) -- NO reimplementa la aritmetica de costos.
Reemplaza al comparador retirado (dryrun_bh.py, retirado; tag git archive/pre-factory-v2), cuyos resultados
el propio proyecto marco como "no comparables" tras la auditoria del motor.

Uso:
    .venv/Scripts/python.exe scripts/verify_buy_and_hold.py --alias SP500 EURUSD XAUUSD
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qaf.costs import execution_cost, financing, price_cash
from qaf.data import load_is
from qaf.io import ROOT, read_json


def run(alias, instruments):
    c = instruments[alias]
    df, info = load_is(alias, "D1")
    entry_price, exit_price = float(df.open.iloc[0]), float(df.close.iloc[-1])

    gross = price_cash(exit_price - entry_price, c, lots=1)

    spread_e, slip_e, comm_e = execution_cost(entry_price, 1, c)
    spread_x, slip_x, comm_x = execution_cost(exit_price, 1, c)
    spread, slip, commission = spread_e + spread_x, slip_e + slip_x, comm_e + comm_x

    fin = financing(df.time.iloc[0], df.time.iloc[-1], 1, 1, c)

    net = gross + fin - spread - slip - commission

    result = {
        "alias": alias,
        "bars": len(df),
        "date_from": str(df.time.iloc[0]),
        "date_to": str(df.time.iloc[-1]),
        "entry_price": entry_price,
        "exit_price": exit_price,
        "gross_pnl": gross,
        "spread_cost": spread,
        "slippage_cost": slip,
        "commission_cost": commission,
        "financing_cashflow": fin,
        "net_pnl": net,
        "costs_verified": bool(c.get("costs_verified")),
        "reserves": c.get("reserves", []),
    }
    print(f"--- {alias} (D1, IS: {result['date_from']} -> {result['date_to']}, {result['bars']} barras) ---")
    print(f"  P&L bruto:        {gross:,.2f}")
    print(f"  - spread:         -{spread:,.2f}")
    print(f"  - slippage:       -{slip:,.2f}")
    print(f"  - comision:       -{commission:,.2f}")
    print(f"  - financiacion:   {fin:,.2f}")
    print(f"  P&L neto:         {net:,.2f}")
    print(f"  costs_verified:   {result['costs_verified']}  (reserva: escenario de costos, no historico -- ver instruments.json)")
    print()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--alias", nargs="+", required=True)
    args = parser.parse_args()
    instruments = read_json(ROOT / "config/instruments.json")
    results = [run(a, instruments) for a in args.alias]
    if len(results) > 1:
        print("=== Comparativa (motor qaf, re-verificado) ===")
        print(f"{'alias':10s} {'barras':>7s} {'bruto':>14s} {'costos':>12s} {'financiacion':>14s} {'neto':>14s}")
        for r in results:
            costs = r["spread_cost"] + r["slippage_cost"] + r["commission_cost"]
            print(f"{r['alias']:10s} {r['bars']:7d} {r['gross_pnl']:14,.2f} {costs:12,.2f} {r['financing_cashflow']:14,.2f} {r['net_pnl']:14,.2f}")


if __name__ == "__main__":
    main()
