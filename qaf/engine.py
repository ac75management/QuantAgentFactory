import math
import numpy as np
import pandas as pd
from .contracts import validate_spec, validate_instrument
from .costs import execution_cost, financing, margin_cash_per_lot, price_cash
from .signals import atr, generate


def resolve_exit(direction, opening, high, low, stop, target):
    """Existing market stop vs limit target. Open is processed before intrabar."""
    if direction == 1:
        if opening <= stop:
            return opening, "STOP_GAP"
        if opening >= target:
            return target, "TARGET_GAP_CONSERVATIVE"
        hit_stop, hit_target = low <= stop, high >= target
    else:
        if opening >= stop:
            return opening, "STOP_GAP"
        if opening <= target:
            return target, "TARGET_GAP_CONSERVATIVE"
        hit_stop, hit_target = high >= stop, low <= target
    if hit_stop:
        return stop, "STOP_TIE" if hit_target else "STOP"
    if hit_target:
        return target, "TARGET"
    return None, None


def simulate(df, spec, instrument, stress=1.0, start_bar=0, signals_override=None):
    validate_spec(spec)
    validate_instrument(instrument)
    if stress < 1:
        raise ValueError("Stress debe ser >=1")
    c, p = instrument, spec["parameters"]
    initial = float(spec.get("initial_equity", 100000))
    if initial <= 0 or not math.isfinite(initial):
        raise ValueError("Capital inicial invalido")
    signal = generate(df, spec) if signals_override is None else np.asarray(signals_override)
    a = atr(df, p["atr_period"])
    balance, position = initial, None
    trades, curve = [], []
    skipped = {"volume_or_margin": 0, "warmup": 0, "nonpositive_equity": 0}
    times = df.time.tolist()
    o, h, l, closes = (df[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close"))
    for i in range(start_bar, len(df)):
        exposed_this_bar = position is not None
        if position is not None and i > position["entry_bar"]:
            cashflow = financing(times[i-1], times[i], position["direction"], position["lots"], c, stress)
            balance += cashflow
            position["financing_cashflow"] += cashflow
        # A position open at the prior close prevents a new signal, even if it exits now.
        if position is None and i > start_bar and signal[i-1] and balance > 0:
            if not np.isfinite(a[i-1]) or a[i-1] <= 0:
                skipped["warmup"] += 1
            elif i < len(df)-1:
                direction = int(signal[i-1])
                stop_distance = p["sl_atr"] * a[i-1]
                risk_cash = balance * spec.get("risk_fraction", 0.005)
                roundtrip_estimate = 2 * sum(execution_cost(o[i], 1, c, stress))
                lots = risk_cash / (price_cash(stop_distance, c) + roundtrip_estimate)
                margin_lots = balance * c["max_leverage"] / margin_cash_per_lot(o[i], c)
                lots = min(lots, margin_lots, c["volume_max"])
                lots = math.floor((lots + 1e-12) / c["volume_step"]) * c["volume_step"]
                if lots < c["volume_min"]:
                    skipped["volume_or_margin"] += 1
                else:
                    spread, slip, commission = execution_cost(o[i], lots, c, stress)
                    position = {"entry_bar": i, "entry_time": str(times[i]), "entry_price": o[i], "direction": direction, "lots": lots, "stop": o[i] - direction * stop_distance, "target": o[i] + direction * p["tp_atr"] * a[i-1], "spread_cost": spread, "slippage_cost": slip, "commission_cost": commission, "financing_cashflow": 0.0, "dividend_cashflow": 0.0, "risk_cash": risk_cash}
                    balance -= spread + slip + commission
                    exposed_this_bar = True
        if position is not None:
            pos = position
            exit_price, reason = resolve_exit(pos["direction"], o[i], h[i], l[i], pos["stop"], pos["target"])
            if i - pos["entry_bar"] >= p["max_holding"]:
                # Time-stop fills at this bar's open. Only open-time events (a gap through
                # stop or target, at the same conservative prices used on any other bar)
                # precede it; intrabar touches would happen after the position is closed.
                # Deciding at the open based on later intrabar prices would be look-ahead.
                if reason not in ("STOP_GAP", "TARGET_GAP_CONSERVATIVE"):
                    exit_price, reason = o[i], "TIME"
            if balance + price_cash(pos["direction"] * (o[i] - pos["entry_price"]), c, pos["lots"]) <= 0:
                exit_price, reason = o[i], "INSOLVENT_OPEN"
            if exit_price is None and i == len(df)-1:
                exit_price, reason = closes[i], "END_OF_SAMPLE"
            if exit_price is not None:
                spread, slip, commission = execution_cost(exit_price, pos["lots"], c, stress)
                gross = price_cash(pos["direction"] * (exit_price - pos["entry_price"]), c, pos["lots"])
                balance += gross - spread - slip - commission
                for key, amount in (("spread_cost", spread), ("slippage_cost", slip), ("commission_cost", commission)):
                    pos[key] += amount
                net = gross + pos["financing_cashflow"] + pos["dividend_cashflow"] - pos["spread_cost"] - pos["slippage_cost"] - pos["commission_cost"]
                pos.update({"exit_bar": i, "exit_time": str(times[i]), "exit_price": exit_price, "exit_reason": reason, "gross_pnl": gross, "net_pnl": net, "return_r": net / pos["risk_cash"], "balance_after": balance})
                trades.append(pos)
                position = None
        floating = 0.0 if position is None else price_cash(position["direction"] * (closes[i] - position["entry_price"]), c, position["lots"])
        # Expected liquidation costs belong in marked equity while position is open.
        liquidation = 0.0 if position is None else sum(execution_cost(closes[i], position["lots"], c, stress))
        curve.append({"time": str(times[i]), "balance": balance, "floating_pnl": floating, "equity": balance + floating - liquidation, "exposed": int(exposed_this_bar)})
        if balance <= 0 and position is None:
            skipped["nonpositive_equity"] += 1
    result = {"trades": trades, "equity": curve, "initial_equity": initial, "skipped": skipped}
    if curve and not math.isclose(initial + sum(t["net_pnl"] for t in trades), curve[-1]["balance"], abs_tol=1e-6):
        raise ArithmeticError("El ledger no reconcilia con el balance final")
    return result
