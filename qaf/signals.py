import numpy as np
import pandas as pd
from zoneinfo import ZoneInfo


def atr(df, period):
    previous = df.close.shift()
    tr = pd.concat([df.high - df.low, (df.high - previous).abs(), (df.low - previous).abs()], axis=1).max(axis=1).to_numpy()
    result = np.full(len(df), np.nan)
    if len(df) > period:
        result[period] = tr[1:period + 1].mean()
        for i in range(period + 1, len(df)):
            result[i] = (result[i - 1] * (period - 1) + tr[i]) / period
    return result


def kama(df, er_len, fast_len, slow_len):
    """Kaufman Adaptive Moving Average. Adaptive smoothing based on efficiency ratio."""
    closes = df.close.to_numpy(dtype=float)
    changes = np.abs(np.diff(closes, prepend=np.nan))
    volatility = np.full(len(df), np.nan)

    for i in range(er_len, len(df)):
        abs_change = np.sum(changes[i - er_len + 1:i + 1])
        net_change = np.abs(closes[i] - closes[i - er_len])
        if abs_change == 0:
            volatility[i] = 0
        else:
            volatility[i] = net_change / abs_change

    fast_sc = 2.0 / (fast_len + 1)
    slow_sc = 2.0 / (slow_len + 1)
    ama = np.full(len(df), np.nan)

    if er_len < len(df):
        ama[er_len] = closes[er_len]
        for i in range(er_len + 1, len(df)):
            if np.isfinite(volatility[i]):
                smooth = volatility[i] * (fast_sc - slow_sc) + slow_sc
                ama[i] = ama[i - 1] + smooth * (closes[i] - ama[i - 1])
            else:
                ama[i] = ama[i - 1]

    return ama


def rsi(df, period):
    """Wilder RSI. Causal: result[i] depends only on bars <= i."""
    delta = df.close.diff().to_numpy()
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = np.full(len(df), np.nan)
    avg_loss = np.full(len(df), np.nan)
    if len(df) > period:
        avg_gain[period] = gain[1:period + 1].mean()
        avg_loss[period] = loss[1:period + 1].mean()
        for i in range(period + 1, len(df)):
            avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gain[i]) / period
            avg_loss[i] = (avg_loss[i - 1] * (period - 1) + loss[i]) / period
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = avg_gain / avg_loss
        result = 100 - 100 / (1 + rs)
    result[(avg_loss == 0) & (avg_gain == 0)] = 50.0
    result[(avg_loss == 0) & (avg_gain > 0)] = 100.0
    return result


def _local_minutes(df, timezone):
    """Convertir tiempo a hora local; timestamps ingenuos fallan cerrado."""
    times = pd.to_datetime(df["time"])
    if times.dt.tz is None:
        raise ValueError("sma_band_session requiere timestamps con zona horaria")
    try:
        local = times.dt.tz_convert(ZoneInfo(timezone))
    except Exception as error:
        raise ValueError(f"No se pudo convertir la zona horaria de sesión: {timezone}") from error
    return local.dt.hour.to_numpy() * 60 + local.dt.minute.to_numpy()


def _clock_minutes(value):
    hour, minute = (int(part) for part in value.split(":"))
    return hour * 60 + minute


def _is_entry_business_day(value):
    """True one weekday before month-end; depends only on the timestamp."""
    current = pd.Timestamp(value)
    month_end = current + pd.offsets.BMonthEnd(0)
    entry_day = month_end - pd.offsets.BDay(1)
    return current.date() == entry_day.date()


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
    elif family == "oscillator_reversion":
        r = rsi(df, p["rsi_period"])
        trend = df.close.rolling(p["trend_filter_sma"]).mean().to_numpy()
        closes = df.close.to_numpy()
        previous = np.roll(r, 1)
        previous[0] = np.nan
        lower = p["entry_threshold"]
        upper = 100 - lower
        # One event per excursion. Remaining below/above the threshold does not
        # create a fresh entry after an unrelated exit.
        signal[(previous >= lower) & (r < lower) & (closes > trend)] = 1
        signal[(previous <= upper) & (r > upper) & (closes < trend)] = -1
    elif family == "sma_band_session":
        local_minutes = _local_minutes(df, p["session_timezone"])
        start = _clock_minutes(p["session_start"])
        end = _clock_minutes(p["session_end"])
        sma = df.close.rolling(p["sma_period"]).mean().to_numpy()
        closes = df.close.to_numpy(dtype=float)
        previous_direction = 0
        threshold = sma * (1.0 + p["band_fraction"])
        for i in range(len(df)):
            if not (start <= local_minutes[i] <= end) or not np.isfinite(threshold[i]):
                continue
            direction = 1 if closes[i] < threshold[i] else -1
            if direction != previous_direction:
                signal[i] = direction
            previous_direction = direction
    elif family == "ma_band_breakout":
        moving_average = df.close.rolling(p["ma_period"]).mean().to_numpy()
        closes = df.close.to_numpy(dtype=float)
        upper = moving_average * (1.0 + p["band_fraction"])
        lower = moving_average * (1.0 - p["band_fraction"])
        for i in range(1, len(df)):
            if not all(np.isfinite(value) for value in (upper[i - 1], lower[i - 1], upper[i], lower[i])):
                continue
            if closes[i] > upper[i] and closes[i - 1] <= upper[i - 1]:
                signal[i] = 1
            elif closes[i] < lower[i] and closes[i - 1] >= lower[i - 1]:
                signal[i] = -1
    elif family == "calendar_window":
        if spec["timeframe"] != "D1":
            raise ValueError("calendar_window requiere barras D1")
        times = pd.to_datetime(df["time"])
        for i, timestamp in enumerate(times):
            if _is_entry_business_day(timestamp):
                signal[i] = 1
    elif family == "volatility_based":
        atr_vals = atr(df, p["atr_period"])
        opens = df.open.to_numpy()
        closes = df.close.to_numpy(dtype=float)
        for i in range(1, len(df)):
            if not np.isfinite(atr_vals[i - 1]):
                continue
            level = atr_vals[i - 1] * p["atr_multiple"]
            if closes[i] > opens[i - 1] + level:
                signal[i] = 1
            elif closes[i] < opens[i - 1] - level:
                signal[i] = -1
    elif family == "kama_turn":
        ama_vals = kama(df, p["ER_Length"], p["FastMA_Length"], p["SlowMA_Length"])
        ama_changes = np.diff(ama_vals, prepend=np.nan)
        ama_change_vol = np.full(len(df), np.nan)
        for i in range(p["ER_Length"], len(df)):
            vol_slice = ama_changes[max(0, i - p["ER_Length"] + 1):i + 1]
            ama_change_vol[i] = np.std(vol_slice)

        filter_threshold = p.get("filter_std_multiplier", 0.01)
        previous_direction = 0

        for i in range(1, len(df)):
            if not np.isfinite(ama_vals[i - 1]) or not np.isfinite(ama_vals[i]):
                continue
            if not np.isfinite(ama_change_vol[i]):
                continue

            threshold = filter_threshold * ama_change_vol[i]
            direction = 1 if ama_vals[i] > ama_vals[i - 1] else -1

            if np.abs(ama_vals[i] - ama_vals[i - 1]) > threshold and direction != previous_direction:
                signal[i] = direction
                previous_direction = direction
    if spec.get("direction") == "long":
        signal[signal < 0] = 0
    if spec.get("direction") == "short":
        signal[signal > 0] = 0
    return signal
