import pandas as pd
import pytest

from qaf.contracts import validate_spec
from qaf.signals import generate


def _spec(**overrides):
    parameters = {"atr_period": 14, "sl_atr": 1.5, "tp_atr": 3.0, "max_holding": 30, "ma_period": 3, "band_fraction": 0.1}
    parameters.update(overrides)
    return {"id": "ma-band-test", "family": "ma_band_breakout", "symbol": "EURUSD", "timeframe": "H4", "parameters": parameters, "rationale": "prueba", "hypothesis_id": "008", "risk_fraction": 0.005, "direction": "both"}


def _bars(closes):
    return pd.DataFrame({"open": closes, "high": [value + 0.1 for value in closes], "low": [value - 0.1 for value in closes], "close": closes})


def test_contract_accepts_h4_symmetric_ma_band_breakout():
    assert validate_spec(_spec())["family"] == "ma_band_breakout"


@pytest.mark.parametrize("key,value", [("ma_period", 1), ("band_fraction", 0), ("band_fraction", 0.201)])
def test_contract_rejects_invalid_ma_band_parameters(key, value):
    with pytest.raises(ValueError):
        validate_spec(_spec(**{key: value}))


def test_signal_emits_only_on_symmetric_band_crossings():
    signal = generate(_bars([10, 10, 10, 14, 15, 13, 8, 7]), _spec())
    assert signal.tolist() == [0, 0, 0, 1, 0, 0, -1, 0]


def test_signal_is_causal_when_future_bars_change():
    prefix = [10, 10, 10, 14, 15]
    first = generate(_bars(prefix + [9, 8]), _spec())[: len(prefix)]
    second = generate(_bars(prefix + [30, 40]), _spec())[: len(prefix)]
    assert first.tolist() == second.tolist()


def test_direction_filter_is_applied_after_crossing():
    long_only = _spec()
    long_only["direction"] = "long"
    assert generate(_bars([10, 10, 10, 14, 10, 8]), long_only).tolist()[-1] == 0
