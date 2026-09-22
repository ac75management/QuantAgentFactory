"""
Motor (engine) para hipotesis #001: reversion XAUUSD D1 tras racha de 3 dias.
Spec: docs/specs/xauusd-d1-mean-reversion-streak-extension.md

Corrido directo en este hilo (no via el subagente `engine`) porque el paso de
Gate 0 con veredicto APTO_CON_RESERVAS exige "confirmacion explicita de
Alexander en el chat" -- y esa confirmacion no puede llegarle a un subagente
relayada por otro agente (bloqueo de seguridad de mas alto nivel, ver
PROJECT_STATE.md, nota operativa 2026-09-22; mismo patron ya usado por la
sesion de VS Code para la hipotesis #002). Sigue el flujo de
.claude/agents/engine.md paso a paso: Gate 0 -> costos -> AED -> backtest IS
-> reporte. No toca OOS. Cero ejecucion en vivo.

Uso:
    python scripts/backtest_xauusd_mean_reversion.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from costs import (
    commission_percentage_roundturn,
    price_pnl_per_lot,
    spread_cost_per_lot,
    swap_cost_per_lot,
)

ROOT = Path(__file__).resolve().parent.parent
IS_PATH = ROOT / "data" / "clean" / "XAUUSD" / "D1" / "IS.parquet"
REPORT_DIR = ROOT / "reports" / "xauusd-d1-mean-reversion-streak-extension"

SEED = 20260922
np.random.seed(SEED)

# docs/cost_model.md -- CONFIRMED 2026-09-22 (comision + dia de swap triple),
# spread/slippage siguen siendo la reserva de Gate 0 (foto puntual / sin publicar)
SPREAD_POINTS = 55
TICK_VALUE = 1.0
TICK_SIZE = 0.01
CONTRACT_SIZE = 100.0
COMMISSION_PCT = 0.0025 / 100.0  # 0.0025% del valor de orden, por lado
SWAP_LONG = -62.6
SWAP_SHORT = 35.4
TRIPLE_WEEKDAY = 2  # miercoles (Monday=0 en date.weekday())

ATR_PERIOD = 14
SL_MULT = 1.5
TP_MULT = 3.0
TIME_STOP_SESSIONS = 5
RISK_PCT = 0.01
INITIAL_EQUITY = 100_000.0
MIN_OPS_GATE = 30


def compute_atr(df, period=ATR_PERIOD):
    high, low, close = df["high"].values, df["low"].values, df["close"].values
    n = len(df)
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    atr = np.full(n, np.nan)
    if n > period:
        atr[period] = tr[1 : period + 1].mean()
        for i in range(period + 1, n):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr


def compute_streaks(df):
    close = df["close"].values
    n = len(df)
    direction = np.zeros(n, dtype=int)
    for i in range(1, n):
        if close[i] > close[i - 1]:
            direction[i] = 1
        elif close[i] < close[i - 1]:
            direction[i] = -1
    streak_len = np.zeros(n, dtype=int)
    for i in range(1, n):
        if direction[i] == 0:
            streak_len[i] = 0
        elif direction[i] == direction[i - 1]:
            streak_len[i] = streak_len[i - 1] + 1
        else:
            streak_len[i] = 1
    return direction, streak_len


def run_aed(df, direction, streak_len, horizon=5):
    close = df["close"].values
    n = len(df)
    signal_idx = [i for i in range(n) if streak_len[i] == 3 and i + horizon < n]
    reversion_returns = []
    for t in signal_idx:
        fwd = close[t + horizon] - close[t]
        reversion_returns.append(-fwd if direction[t] == 1 else fwd)
    reversion_returns = np.array(reversion_returns)

    rng = np.random.default_rng(SEED)
    random_idx = rng.integers(0, n - horizon, size=2000)
    random_fwd = np.abs(close[random_idx + horizon] - close[random_idx])

    t_stat, p_value = stats.ttest_ind(reversion_returns, random_fwd, equal_var=False)
    return {
        "n_signals_aed": len(signal_idx),
        "mean_reversion_return": float(reversion_returns.mean()) if len(reversion_returns) else None,
        "mean_random_abs_return": float(random_fwd.mean()),
        "t_stat": float(t_stat),
        "p_value": float(p_value),
    }


def backtest(df, direction, streak_len, atr):
    n = len(df)
    open_, high, low, close = df["open"].values, df["high"].values, df["low"].values, df["close"].values
    times = df["time"].values

    equity = INITIAL_EQUITY
    equity_curve = [{"bar": 0, "time": str(df.loc[0, "time"]), "equity": equity}]
    trades = []
    next_free_bar = 0

    for t in range(n):
        if streak_len[t] != 3:
            continue
        if t < next_free_bar:
            continue  # posicion abierta -- se descarta la senal (regla 4 de la spec)
        entry_bar = t + 1
        if entry_bar >= n or np.isnan(atr[t]):
            continue

        is_long = direction[t] == -1  # racha bajista -> LONG; racha alcista -> SHORT
        entry_price = open_[entry_bar]
        a = atr[t]
        if is_long:
            sl, tp = entry_price - SL_MULT * a, entry_price + TP_MULT * a
        else:
            sl, tp = entry_price + SL_MULT * a, entry_price - TP_MULT * a

        sl_distance = abs(entry_price - sl)
        dollar_risk_per_lot = sl_distance / TICK_SIZE * TICK_VALUE
        lots = (equity * RISK_PCT) / dollar_risk_per_lot if dollar_risk_per_lot > 0 else 0.0

        exit_price, exit_reason, exit_bar = None, None, None
        for day_offset in range(TIME_STOP_SESSIONS):
            bar_idx = entry_bar + day_offset
            if bar_idx >= n:
                break
            if is_long:
                hit_sl, hit_tp = low[bar_idx] <= sl, high[bar_idx] >= tp
            else:
                hit_sl, hit_tp = high[bar_idx] >= sl, low[bar_idx] <= tp
            if hit_sl:
                exit_price, exit_reason, exit_bar = sl, ("SL_TP_TIEBREAK" if hit_tp else "SL"), bar_idx
                break
            if hit_tp:
                exit_price, exit_reason, exit_bar = tp, "TP", bar_idx
                break

        if exit_price is None:
            cand = entry_bar + TIME_STOP_SESSIONS
            if cand >= n:
                cand = n - 1
                exit_price, exit_reason = close[cand], "TIME_STOP_EOD"
            else:
                exit_price, exit_reason = open_[cand], "TIME_STOP"
            exit_bar = cand

        price_diff = (exit_price - entry_price) if is_long else (entry_price - exit_price)
        gross_pnl = price_pnl_per_lot(
            entry_price, exit_price, TICK_SIZE, TICK_VALUE
        )
        gross_pnl = gross_pnl * lots if is_long else -gross_pnl * lots

        spread_cost = spread_cost_per_lot(
            SPREAD_POINTS, TICK_SIZE, TICK_VALUE
        ) * lots
        notional_entry = entry_price * CONTRACT_SIZE * lots
        notional_exit = exit_price * CONTRACT_SIZE * lots
        commission_cost = commission_percentage_roundturn(
            notional_entry, notional_exit, COMMISSION_PCT
        )

        swap_rate = SWAP_LONG if is_long else SWAP_SHORT
        triple_night_indices = []
        nights = 0
        for offset, k in enumerate(range(entry_bar, exit_bar)):
            night_weekday = pd.Timestamp(times[k]).weekday()
            nights += 1
            if night_weekday == TRIPLE_WEEKDAY:
                triple_night_indices.append(offset)
        swap_total = swap_cost_per_lot(
            nights, swap_rate, triple_night_indices
        ) * lots

        net_pnl = gross_pnl + swap_total - spread_cost - commission_cost
        equity += net_pnl

        trades.append(
            {
                "signal_bar": t,
                "signal_time": str(df.loc[t, "time"]),
                "direction": "LONG" if is_long else "SHORT",
                "entry_bar": entry_bar,
                "entry_time": str(df.loc[entry_bar, "time"]),
                "entry_price": entry_price,
                "exit_bar": int(exit_bar),
                "exit_time": str(df.loc[exit_bar, "time"]),
                "exit_price": exit_price,
                "exit_reason": exit_reason,
                "lots": lots,
                "atr14_at_signal": a,
                "gross_pnl": gross_pnl,
                "spread_cost": spread_cost,
                "commission_cost": commission_cost,
                "swap_total": swap_total,
                "net_pnl": net_pnl,
                "equity_after": equity,
            }
        )
        equity_curve.append({"bar": int(exit_bar), "time": str(df.loc[exit_bar, "time"]), "equity": equity})
        next_free_bar = exit_bar + 1

    return trades, equity_curve


def summarize(trades, equity_curve):
    if not trades:
        return {"n_trades": 0}
    df_t = pd.DataFrame(trades)
    wins = df_t[df_t["net_pnl"] > 0]
    losses = df_t[df_t["net_pnl"] <= 0]
    gross_profit = wins["net_pnl"].sum()
    gross_loss = -losses["net_pnl"].sum()
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")

    eq = pd.DataFrame(equity_curve)["equity"].values
    running_max = np.maximum.accumulate(eq)
    drawdown = (eq - running_max) / running_max
    max_dd = drawdown.min()

    total_cost = (df_t["spread_cost"] + df_t["commission_cost"] - df_t["swap_total"].clip(upper=0)).sum()
    # friccion: costo total pagado (spread+comision+swap perdido) vs expectancy neta total
    cost_paid = df_t["spread_cost"].sum() + df_t["commission_cost"].sum() + (-df_t["swap_total"][df_t["swap_total"] < 0]).sum()
    net_total = df_t["net_pnl"].sum()
    friction_ratio = (net_total / cost_paid) if cost_paid > 0 else None

    half = len(df_t) // 2
    first_half_pnl = df_t.iloc[:half]["net_pnl"].sum() if half > 0 else None
    second_half_pnl = df_t.iloc[half:]["net_pnl"].sum() if half > 0 else None

    terciles = pd.qcut(df_t["atr14_at_signal"], 3, labels=["baja_vol", "media_vol", "alta_vol"])
    df_t["vol_tercil"] = terciles
    by_tercile = df_t.groupby("vol_tercil", observed=True)["net_pnl"].agg(["count", "sum", "mean"]).to_dict("index")

    return {
        "n_trades": len(df_t),
        "win_rate": float((df_t["net_pnl"] > 0).mean()),
        "profit_factor": float(profit_factor),
        "gross_profit": float(gross_profit),
        "gross_loss": float(gross_loss),
        "net_pnl_total": float(net_total),
        "final_equity": float(eq[-1]),
        "max_drawdown_pct": float(max_dd * 100),
        "cost_paid_total": float(cost_paid),
        "friction_ratio": float(friction_ratio) if friction_ratio is not None else None,
        "first_half_net_pnl": float(first_half_pnl) if first_half_pnl is not None else None,
        "second_half_net_pnl": float(second_half_pnl) if second_half_pnl is not None else None,
        "by_volatility_tercile": by_tercile,
    }


def main():
    df = pd.read_parquet(IS_PATH).sort_values("time").reset_index(drop=True)
    direction, streak_len = compute_streaks(df)
    atr = compute_atr(df)

    aed = run_aed(df, direction, streak_len)
    trades, equity_curve = backtest(df, direction, streak_len, atr)
    summary = summarize(trades, equity_curve)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(trades).to_csv(REPORT_DIR / "trades.csv", index=False)
    pd.DataFrame(equity_curve).to_csv(REPORT_DIR / "equity_curve.csv", index=False)
    with open(REPORT_DIR / "summary.json", "w", encoding="utf-8") as f:
        json.dump({"aed": aed, "backtest": summary, "seed": SEED}, f, indent=2, default=str, ensure_ascii=False)

    print("=== AED ===")
    print(json.dumps(aed, indent=2))
    print("\n=== Backtest IS ===")
    print(json.dumps({k: v for k, v in summary.items() if k != "by_volatility_tercile"}, indent=2))
    print("\nPor tercil de volatilidad (ATR14 al momento de la senal):")
    print(json.dumps(summary.get("by_volatility_tercile", {}), indent=2, default=str))


if __name__ == "__main__":
    main()
