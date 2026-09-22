"""
Backtest In-Sample de la hipotesis #002 (nas100-d1-turn-of-month-flow) contra
docs/specs/nas100-d1-turn-of-month-flow.md, corrido directamente en el hilo
principal (no via subagente `engine`) porque el subagente `engine` bloqueo
correctamente al no poder verificar consentimiento humano relayado -- ver
reports/nas100-d1-turn-of-month-flow/data_quality.md y el hilo de chat
2026-09-22 para el contexto de esa decision.

Reglas implementadas exactamente como en la spec, seccion por seccion:
- Seccion 2: entrada LONG incondicional en close(LTD-1), fill en open(LTD)
- Seccion 3: salida por tiempo en open(LTD+4), SL=-1.5*ATR14 / TP=+2.5*ATR14
  como valvulas, chequeadas desde LTD hasta LTD+3 inclusive, empate=SL primero
- Seccion 4: fill siempre en la barra siguiente, spread aplicado 1x al entrar
- Seccion 6: costos con tick_value/tick_size=10 USD/punto/lote, swap con
  triple viernes (swap_rollover3days=5)
- Seccion 7: sizing 0.5% equity/operacion, compounding simple, sin martingala
- Seccion 9: split IS/OOS ya fisico, este script SOLO abre IS.parquet

No toca OOS.parquet en ningun punto.
"""
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from costs import (
    commission_roundturn_per_lot,
    price_pnl_per_lot,
    spread_cost_per_lot,
    swap_cost_per_lot,
)

ROOT = Path(__file__).resolve().parent.parent
IS_PATH = ROOT / "data" / "clean" / "NAS100" / "D1" / "IS.parquet"
OUT_DIR = ROOT / "reports" / "nas100-d1-turn-of-month-flow"
SEED = 20260922

# --- Costos confirmados / aproximados, docs/cost_model.md + spec seccion 6 ---
TICK_VALUE = 1.0
TICK_SIZE = 0.1
USD_PER_POINT_PER_LOT = TICK_VALUE / TICK_SIZE  # 10.0
SPREAD_POINTS = 9.0          # foto puntual LIVE, aproximacion documentada
SLIPPAGE_POINTS = 2.0        # estimacion conservadora documentada
COMMISSION_PER_SIDE = 2.75   # USD/contrato, CONFIRMED
SWAP_LONG = -45.73           # USD/noche/lote, CONFIRMED
FRIDAY_WEEKDAY = 4           # swap_rollover3days=5 (viernes) para indices

SPREAD_COST_USD = spread_cost_per_lot(SPREAD_POINTS, TICK_SIZE, TICK_VALUE)
SLIPPAGE_COST_USD = spread_cost_per_lot(SLIPPAGE_POINTS, TICK_SIZE, TICK_VALUE)
COMMISSION_COST_USD = commission_roundturn_per_lot(COMMISSION_PER_SIDE)
COST_ROUNDTURN_USD = SPREAD_COST_USD + SLIPPAGE_COST_USD + COMMISSION_COST_USD  # 115.50

ATR_PERIOD = 14
SL_MULT = 1.5
TP_MULT = 2.5
RISK_PCT = 0.005
INITIAL_EQUITY = 100_000.0
MIN_TRADES_OOS_GATE = 30  # referencia (gate real se aplica en OOS, no aqui)


def wilder_atr(df, period=14):
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.copy()
    atr.iloc[:period] = np.nan
    first_valid = tr.iloc[1:period + 1].mean()  # SMA de los primeros `period` TR reales (excluye bar 0 sin prev_close)
    atr.iloc[period] = first_valid
    for i in range(period + 1, len(tr)):
        atr.iloc[i] = (atr.iloc[i - 1] * (period - 1) + tr.iloc[i]) / period
    return atr


def find_ltd_bars(df):
    month_key = df["time"].dt.year * 12 + df["time"].dt.month
    is_ltd = month_key != month_key.shift(-1)
    is_ltd.iloc[-1] = False  # borde del IS, sin ciclo completo -- ya excluido por Gate 0
    return df.index[is_ltd].tolist()


def swap_cost_for_cycle(times, entry_idx, exit_idx):
    """Suma swap_long por cada noche entre entry_idx y exit_idx (bar index),
    x3 si la barra de origen de la noche es viernes."""
    triple_indices = []
    nights = []
    for offset, j in enumerate(range(entry_idx, exit_idx)):
        origin_weekday = times.iloc[j].weekday()
        mult = 3 if origin_weekday == FRIDAY_WEEKDAY else 1
        if mult == 3:
            triple_indices.append(offset)
        nights.append((str(times.iloc[j].date()), mult))
    total = swap_cost_per_lot(len(nights), SWAP_LONG, triple_indices)
    return total, nights


def run_backtest(df):
    atr = wilder_atr(df, ATR_PERIOD)
    ltd_bars = find_ltd_bars(df)

    trades = []
    equity = INITIAL_EQUITY
    equity_curve = [(str(df.loc[0, "time"].date()), equity)]
    skipped_no_atr = 0
    skipped_out_of_range = 0

    for ltd_idx in ltd_bars:
        signal_idx = ltd_idx - 1  # LTD - 1
        entry_idx = ltd_idx       # LTD, fill al open
        exit_time_idx = ltd_idx + 4  # LTD + 4

        if signal_idx < 0 or exit_time_idx >= len(df):
            skipped_out_of_range += 1
            continue

        atr_val = atr.iloc[signal_idx]
        if pd.isna(atr_val):
            skipped_no_atr += 1
            continue

        entry_price = df.loc[entry_idx, "open"]
        sl_price = entry_price - SL_MULT * atr_val
        tp_price = entry_price + TP_MULT * atr_val

        exit_idx = None
        exit_price = None
        exit_reason = None
        for k in range(entry_idx, entry_idx + 4):  # LTD .. LTD+3 inclusive
            low_k = df.loc[k, "low"]
            high_k = df.loc[k, "high"]
            sl_hit = low_k <= sl_price
            tp_hit = high_k >= tp_price
            if sl_hit:  # empate -> SL primero
                exit_idx, exit_price, exit_reason = k, sl_price, "SL"
                break
            if tp_hit:
                exit_idx, exit_price, exit_reason = k, tp_price, "TP"
                break

        if exit_idx is None:
            exit_idx = exit_time_idx
            exit_price = df.loc[exit_time_idx, "open"]
            exit_reason = "TIME"

        # sizing sobre el equity vigente en el momento de la entrada
        sl_distance_points = SL_MULT * atr_val
        risk_usd = equity * RISK_PCT
        lots = risk_usd / (sl_distance_points * USD_PER_POINT_PER_LOT)

        gross_pnl_per_lot = price_pnl_per_lot(
            entry_price, exit_price, TICK_SIZE, TICK_VALUE
        )
        swap_total_per_lot, nights = swap_cost_for_cycle(df["time"], entry_idx, exit_idx)

        gross_pnl = gross_pnl_per_lot * lots
        swap_total = swap_total_per_lot * lots
        cost_roundturn = COST_ROUNDTURN_USD * lots
        net_pnl = gross_pnl + swap_total - cost_roundturn

        equity += net_pnl

        trades.append({
            "ltd_date": str(df.loc[ltd_idx, "time"].date()),
            "signal_date": str(df.loc[signal_idx, "time"].date()),
            "entry_date": str(df.loc[entry_idx, "time"].date()),
            "exit_date": str(df.loc[exit_idx, "time"].date()),
            "exit_reason": exit_reason,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "atr14": atr_val,
            "sl_price": sl_price,
            "tp_price": tp_price,
            "lots": lots,
            "nights_held": len(nights),
            "friday_nights": sum(1 for _, m in nights if m == 3),
            "gross_pnl": gross_pnl,
            "swap_total": swap_total,
            "cost_roundturn": cost_roundturn,
            "net_pnl": net_pnl,
            "equity_after": equity,
        })
        equity_curve.append((str(df.loc[exit_idx, "time"].date()), equity))

    return pd.DataFrame(trades), pd.DataFrame(equity_curve, columns=["date", "equity"]), {
        "n_ltd_bars": len(ltd_bars),
        "skipped_no_atr": skipped_no_atr,
        "skipped_out_of_range": skipped_out_of_range,
    }


def aed_statistical_test(df):
    """Prueba estadistica concreta (regla engine.md paso 4): el retorno del
    ciclo LTD->LTD+4 (open a open) vs. una muestra aleatoria de ventanas de 4
    barras del resto del año, t-test de dos muestras."""
    rng = np.random.default_rng(SEED)
    ltd_bars = find_ltd_bars(df)

    cycle_returns = []
    for ltd_idx in ltd_bars:
        end_idx = ltd_idx + 4
        if end_idx >= len(df):
            continue
        r = (df.loc[end_idx, "open"] - df.loc[ltd_idx, "open"]) / df.loc[ltd_idx, "open"]
        cycle_returns.append(r)
    cycle_returns = np.array(cycle_returns)

    max_start = len(df) - 5
    n_random = 2000
    random_starts = rng.integers(0, max_start, size=n_random)
    random_returns = np.array([
        (df.loc[s + 4, "open"] - df.loc[s, "open"]) / df.loc[s, "open"]
        for s in random_starts
    ])

    t_stat, p_value = stats.ttest_ind(cycle_returns, random_returns, equal_var=False)
    return {
        "n_cycles": len(cycle_returns),
        "mean_cycle_return": float(np.mean(cycle_returns)),
        "std_cycle_return": float(np.std(cycle_returns, ddof=1)),
        "n_random_windows": n_random,
        "mean_random_return": float(np.mean(random_returns)),
        "std_random_return": float(np.std(random_returns, ddof=1)),
        "t_stat": float(t_stat),
        "p_value": float(p_value),
    }


def deterioration_split(trades_df):
    """Regla 11.9 de la spec: desempeno segmentado en 2 mitades cronologicas."""
    n = len(trades_df)
    half = n // 2
    first, second = trades_df.iloc[:half], trades_df.iloc[half:]
    out = {}
    for label, part in [("primera_mitad", first), ("segunda_mitad", second)]:
        wins = (part["net_pnl"] > 0).sum()
        out[label] = {
            "n_trades": len(part),
            "date_from": part["ltd_date"].iloc[0] if len(part) else None,
            "date_to": part["ltd_date"].iloc[-1] if len(part) else None,
            "win_rate": float(wins / len(part)) if len(part) else None,
            "net_pnl_sum": float(part["net_pnl"].sum()) if len(part) else None,
            "gross_profit": float(part.loc[part["net_pnl"] > 0, "net_pnl"].sum()) if len(part) else None,
            "gross_loss": float(part.loc[part["net_pnl"] < 0, "net_pnl"].sum()) if len(part) else None,
        }
    return out


def max_drawdown(equity_curve):
    eq = equity_curve["equity"].values
    running_max = np.maximum.accumulate(eq)
    dd = (eq - running_max) / running_max
    return float(dd.min())


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(IS_PATH).sort_values("time").reset_index(drop=True)
    file_hash = hashlib.sha256(IS_PATH.read_bytes()).hexdigest()

    aed = aed_statistical_test(df)
    trades_df, equity_curve, meta = run_backtest(df)
    trades_df.to_csv(OUT_DIR / "trades.csv", index=False)
    equity_curve.to_csv(OUT_DIR / "equity_curve.csv", index=False)

    n_trades = len(trades_df)
    wins = trades_df[trades_df["net_pnl"] > 0]
    losses = trades_df[trades_df["net_pnl"] <= 0]
    gross_profit = wins["net_pnl"].sum()
    gross_loss = losses["net_pnl"].sum()
    profit_factor = (gross_profit / abs(gross_loss)) if gross_loss != 0 else float("inf")
    win_rate = len(wins) / n_trades if n_trades else 0.0
    expectancy_net = trades_df["net_pnl"].mean() if n_trades else 0.0
    avg_lots = trades_df["lots"].mean() if n_trades else 0.0
    expectancy_net_per_lot = (trades_df["net_pnl"] / trades_df["lots"]).mean() if n_trades else 0.0
    avg_cost_per_lot = (trades_df["cost_roundturn"] - trades_df["swap_total"]).sum() / trades_df["lots"].sum() if n_trades else 0.0
    avg_full_cost_per_lot = ((trades_df["cost_roundturn"] - trades_df["swap_total"]).abs() + trades_df["swap_total"].abs()).sum() / trades_df["lots"].sum() if n_trades else 0.0
    friction_ratio = expectancy_net_per_lot / avg_full_cost_per_lot if avg_full_cost_per_lot else float("nan")
    dd = max_drawdown(equity_curve)
    deterioration = deterioration_split(trades_df)

    summary = {
        "seed": SEED,
        "is_path": str(IS_PATH.relative_to(ROOT)),
        "is_sha256": file_hash,
        "n_bars_is": len(df),
        "date_from": str(df.loc[0, "time"].date()),
        "date_to": str(df.loc[len(df) - 1, "time"].date()),
        "n_ltd_bars_detected": meta["n_ltd_bars"],
        "skipped_out_of_range": meta["skipped_out_of_range"],
        "skipped_no_atr": meta["skipped_no_atr"],
        "n_trades": n_trades,
        "win_rate": win_rate,
        "gross_profit": float(gross_profit),
        "gross_loss": float(gross_loss),
        "profit_factor": float(profit_factor),
        "expectancy_net_per_trade_usd": float(expectancy_net),
        "expectancy_net_per_lot_usd": float(expectancy_net_per_lot),
        "avg_lots_per_trade": float(avg_lots),
        "avg_full_cost_per_lot_usd": float(avg_full_cost_per_lot),
        "friction_ratio": float(friction_ratio),
        "friction_ratio_gate_min": 3.0,
        "max_drawdown_pct": dd,
        "final_equity": float(equity_curve["equity"].iloc[-1]),
        "initial_equity": INITIAL_EQUITY,
        "aed": aed,
        "deterioration": deterioration,
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
