from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from qaf.engine import simulate
from qaf.io import ROOT, read_json
from qaf.signals import generate


def _spec(max_holding=20):
    return {
        "id": "session-test",
        "family": "sma_band_session",
        "symbol": "EURUSD",
        "timeframe": "H1",
        "parameters": {
            "atr_period": 2,
            "sl_atr": 1.5,
            "tp_atr": 3.0,
            "max_holding": max_holding,
            "sma_period": 2,
            "band_fraction": 0.001,
            "session_timezone": "America/New_York",
            "session_start": "10:00",
            "session_end": "15:00",
            "exit_time": "15:01",
        },
        "rationale": "Prueba causal de precio contra SMA con sesión local.",
        "hypothesis_id": "TEST-SESSION",
        "risk_fraction": 0.005,
        "initial_equity": 100000,
        "direction": "both",
        "version": 1,
    }


def _bars(values, start="2024-01-02 13:00:00+00:00"):
    close = np.asarray(values, dtype=float)
    opening = np.r_[close[0], close[:-1]]
    return pd.DataFrame({
        "time": pd.date_range(start, periods=len(close), freq="h", tz="UTC"),
        "open": opening,
        "high": np.maximum(opening, close) + 0.002,
        "low": np.minimum(opening, close) - 0.002,
        "close": close,
    })


def test_sma_band_session_emits_only_in_new_york_window_and_on_change():
    # 13:00 UTC = 08:00 NY in winter; 15:00 UTC = 10:00 NY.
    df = _bars([1.1000, 1.1000, 1.1000, 1.1000, 1.1000, 1.1050, 1.1000, 1.1000])
    spec = _spec()
    signal = generate(df, spec)
    assert signal[0] == 0 and signal[1] == 0  # 08:00/09:00 NY, excluded
    assert signal[2] in (1, -1)  # 10:00 NY, first eligible SMA(2) event
    assert signal[3] == 0  # unchanged direction does not repeat
    assert signal[4] == 0
    assert signal[5] in (1, -1) and signal[5] != signal[2]
    assert signal[6] in (1, -1) and signal[6] != signal[5]


def test_sma_band_session_is_causal_and_handles_dst():
    # On 2024-03-11, 14:00 UTC is 10:00 NY after the DST switch.
    df = _bars([1.0, 1.0, 1.0, 1.0, 1.0, 1.01, 1.0], start="2024-03-11 13:00:00+00:00")
    spec = _spec()
    full = generate(df, spec)
    prefix = generate(df.iloc[:6], spec)
    assert np.array_equal(full[:6], prefix)
    assert full[0] == 0  # 09:00 NY, excluded
    assert full[1] in (1, -1)  # 10:00 NY, included despite DST offset


def test_sma_band_session_requires_aware_timestamps():
    df = _bars([1.0, 1.0, 1.0]).assign(time=lambda x: x.time.dt.tz_localize(None))
    with pytest.raises(ValueError, match="timestamps con zona horaria"):
        generate(df, _spec())


def test_engine_exits_at_first_hour_after_session_expiry():
    df = _bars([1.1000] * 12)
    spec = _spec()
    instrument = deepcopy(read_json(ROOT / "config/instruments.json")["EURUSD"])
    signal = np.zeros(len(df), dtype=int)
    signal[3] = 1  # signal at 16:00 UTC / 11:00 NY; fills at 17:00 UTC / 12:00 NY
    result = simulate(df, spec, instrument, signals_override=signal)
    assert len(result["trades"]) == 1
    trade = result["trades"][0]
    assert trade["entry_time"].startswith("2024-01-02 17:00")
    assert trade["exit_time"].startswith("2024-01-02 21:00")  # 16:00 NY, first H1 open after 15:01
    assert trade["exit_reason"] == "SESSION_EXIT"


def test_engine_does_not_fill_signal_after_session_expiry():
    df = _bars([1.1000] * 12)
    spec = _spec()
    instrument = deepcopy(read_json(ROOT / "config/instruments.json")["EURUSD"])
    signal = np.zeros(len(df), dtype=int)
    signal[7] = 1  # 20:00 UTC / 15:00 NY; next open is 16:00 NY, expired
    result = simulate(df, spec, instrument, signals_override=signal)
    assert result["trades"] == []
    assert result["skipped"]["session_expired"] == 1
