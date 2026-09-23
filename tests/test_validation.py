from copy import deepcopy

import numpy as np
import pandas as pd

from qaf.io import ROOT, read_json
from qaf.validation import parameter_sensitivity


def test_sensitivity_leaves_session_fields_structural():
    n = 80
    close = 1.1 + np.linspace(0, 0.01, n)
    df = pd.DataFrame({
        "time": pd.date_range("2024-01-02", periods=n, freq="h", tz="UTC"),
        "open": close,
        "high": close + 0.001,
        "low": close - 0.001,
        "close": close,
    })
    spec = read_json(ROOT / "docs/specs/eurusd-h1-intraday-reversal-currency-markets-alpha.json")
    instrument = deepcopy(read_json(ROOT / "config/instruments.json")["EURUSD"])
    policy = {
        "seed": 7,
        "sensitivity_mc_iterations": 200,
        "sensitivity_mc_range": 0.2,
        "sensitivity_min_valid": 1,
        "sensitivity_max_original_percentile": 0.8,
        "sensitivity_min_positive_share": 0.5,
    }
    result = parameter_sensitivity(df, spec, instrument, 0.0, policy)
    assert set(result["structural_parameters"]) == {"session_timezone", "session_start", "session_end", "exit_time"}
    assert "sma_period" in result["numeric_parameters"]
    assert result["monte_carlo_iterations"] == 200
