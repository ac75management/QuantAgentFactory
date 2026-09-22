import numpy as np
import pandas as pd


def summarize(result):
    t = result["trades"]
    pnl = np.array([x["net_pnl"] for x in t], dtype=float)
    equity = np.array([result["initial_equity"]] + [x["equity"] for x in result["equity"]])
    peak = np.maximum.accumulate(equity)
    dd = np.divide(peak-equity, peak, out=np.zeros_like(equity), where=peak>0)
    paid = sum(x["spread_cost"] + x["slippage_cost"] + x["commission_cost"] + max(0, -x["financing_cashflow"]) for x in t)
    gains, losses = float(pnl[pnl>0].sum()), float(-pnl[pnl<0].sum())
    underwater = longest = 0
    for value in dd:
        underwater = underwater + 1 if value > 0 else 0
        longest = max(longest, underwater)
    return {"n_trades": len(t), "initial_equity": result["initial_equity"], "final_equity": float(equity[-1]), "net_pnl": float(pnl.sum()), "return_fraction": float(equity[-1]/equity[0]-1), "expectancy_net": float(pnl.mean()) if len(t) else None, "median_trade": float(np.median(pnl)) if len(t) else None, "win_rate": float((pnl>0).mean()) if len(t) else None, "profit_factor": gains/losses if losses else None, "profit_factor_note": "Sin perdidas: PF indefinido" if len(t) and not losses else None, "max_drawdown_fraction": float(dd.max()), "drawdown_duration_bars": longest, "paid_costs": paid, "friction_ratio": float(pnl.sum()/paid) if paid else None, "gross_pnl": sum(x["gross_pnl"] for x in t), "spread_cost": sum(x["spread_cost"] for x in t), "slippage_cost": sum(x["slippage_cost"] for x in t), "commission_cost": sum(x["commission_cost"] for x in t), "financing_cashflow": sum(x["financing_cashflow"] for x in t), "dividend_cashflow": sum(x["dividend_cashflow"] for x in t), "worst_trade": float(pnl.min()) if len(t) else None, "end_of_sample_exits": sum(x["exit_reason"] == "END_OF_SAMPLE" for x in t), "exposure_bar_fraction": float(np.mean([x["exposed"] for x in result["equity"]])) if result["equity"] else 0}


def block_bootstrap(trades, seed=20260922, iterations=2000, block_size=5):
    """Diagnostic moving-block bootstrap of trade R, NOT a permutation proof of edge."""
    values = np.array([x["return_r"] for x in trades], dtype=float)
    n = len(values)
    if n < max(20, 2*block_size):
        return {"status": "INCONCLUSIVE", "reason": "Muestra insuficiente para bootstrap", "n": n}
    rng = np.random.default_rng(seed)
    block_size = min(block_size, n)
    starts = rng.integers(0, n-block_size+1, (iterations, int(np.ceil(n/block_size))))
    indexes = (starts[:,:,None] + np.arange(block_size)).reshape(iterations,-1)[:,:n]
    means = values[indexes].mean(axis=1)
    centered = means - values.mean()
    # One-sided centered bootstrap under a zero-mean null; assumptions disclosed.
    p = (int((centered >= values.mean()).sum()) + 1)/(iterations+1)
    return {"status": "DIAGNOSTIC", "n": n, "iterations": iterations, "block_size": block_size, "mean_r": float(values.mean()), "mean_r_ci95": [float(x) for x in np.quantile(means,[.025,.975])], "p_centered_bootstrap_one_sided": p, "method": "Moving blocks sobre R; requiere estabilidad/dependencia local. No test de permutacion ni garantia de edge."}


def monthly_returns(result):
    if not result["equity"]:
        return []
    df = pd.DataFrame(result["equity"])
    df["month"] = pd.to_datetime(df.time).dt.strftime("%Y-%m")
    ends = df.groupby("month", sort=True).equity.last()
    previous = result["initial_equity"]
    out = []
    for month, value in ends.items():
        out.append({"month": month, "return_fraction": float(value/previous-1) if previous > 0 else None})
        previous = value
    return out
