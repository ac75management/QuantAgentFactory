import numpy as np
import pandas as pd


def atr(df, period):
    previous = df.close.shift()
    tr = pd.concat([df.high - df.low, (df.high - previous).abs(), (df.low - previous).abs()], axis=1).max(axis=1).to_numpy()
    result = np.full(len(df), np.nan)
    if len(df) > period:
        result[period] = tr[1:period + 1].mean()
        for i in range(period + 1, len(df)):
            result[i] = (result[i - 1] * (period - 1) + tr[i]) / period
    return result


def generate(df, spec):
    """All signal[i] values depend only on bars <= i; fill occurs on i+1."""
    p, family = spec["parameters"], spec["family"]
    signal = np.zeros(len(df), dtype=int)
    if family == "streak_reversal":
        direction = np.sign(df.close.diff().fillna(0).to_numpy())
        count = 0
        for i in range(1, len(df)):
            count = (count + 1 if direction[i] == direction[i-1] else 1) if direction[i] else 0
            if count == p["streak"]:
                signal[i] = -int(direction[i])
    elif family == "trend_cross":
        fast = df.close.rolling(p["fast"]).mean()
        slow = df.close.rolling(p["slow"]).mean()
        side = np.sign(fast - slow)
        valid = side.notna() & side.shift().notna() & (side != side.shift())
        signal[valid] = side[valid].astype(int)
    elif family == "channel_breakout":
        upper = df.high.rolling(p["lookback"]).max().shift()
        lower = df.low.rolling(p["lookback"]).min().shift()
        signal[df.close > upper] = 1
        signal[df.close < lower] = -1
    if spec.get("direction") == "long":
        signal[signal < 0] = 0
    if spec.get("direction") == "short":
        signal[signal > 0] = 0
    return signal
