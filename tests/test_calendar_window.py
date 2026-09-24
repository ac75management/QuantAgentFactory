import pandas as pd
import pytest

from qaf.contracts import validate_spec
from qaf.signals import generate


def _spec(**overrides):
    spec = {
        "id": "nas100-d1-turn-of-month-flow",
        "family": "calendar_window",
        "symbol": "NAS100",
        "timeframe": "D1",
        "parameters": {"atr_period": 14, "sl_atr": 1.5, "tp_atr": 2.5, "max_holding": 4},
        "rationale": "Flujo institucional alrededor del cambio de mes.",
        "hypothesis_id": "002",
        "risk_fraction": 0.005,
        "initial_equity": 100000,
        "direction": "long",
        "version": 1,
    }
    spec.update(overrides)
    return spec


def _bars(dates):
    return pd.DataFrame({
        "time": pd.to_datetime(dates, utc=True),
        "open": 100.0,
        "high": 101.0,
        "low": 99.0,
        "close": 100.0,
    })


def test_contract_accepts_frozen_d1_long_spec():
    assert validate_spec(_spec())["family"] == "calendar_window"


@pytest.mark.parametrize(("field", "value", "message"), [
    ("timeframe", "H4", "timeframe D1"),
    ("direction", "both", "direction long"),
])
def test_contract_rejects_wrong_calendar_shape(field, value, message):
    with pytest.raises(ValueError, match=message):
        validate_spec(_spec(**{field: value}))


def test_signal_marks_weekday_before_last_weekday_without_future_prices():
    bars = _bars(["2024-01-29", "2024-01-30", "2024-01-31", "2024-02-01"])
    assert generate(bars, _spec()).tolist() == [0, 1, 0, 0]


def test_friday_signal_when_month_end_is_monday():
    bars = _bars(["2024-09-26", "2024-09-27", "2024-09-30", "2024-10-01"])
    assert generate(bars, _spec()).tolist() == [0, 1, 0, 0]


def test_signal_prefix_is_unchanged_when_future_rows_change():
    prefix = _bars(["2024-01-29", "2024-01-30", "2024-01-31"])
    first = generate(prefix, _spec())
    extended = pd.concat([prefix, _bars(["2024-02-01", "2024-02-02"])], ignore_index=True)
    second = generate(extended, _spec())[: len(prefix)]
    assert first.tolist() == second.tolist()


def test_signal_does_not_infer_month_end_from_missing_future_bars():
    bars = _bars(["2024-01-25", "2024-01-26"])
    assert generate(bars, _spec()).tolist() == [0, 0]
