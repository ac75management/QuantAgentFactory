import json
from qaf.experiment_registry import append_trial, count_trials


def _record(run_id="r1"):
    return {"run_id": run_id, "created_at": "2026-01-01T00:00:00+00:00",
            "spec": {"hypothesis_id": "001", "family": "trend_cross", "symbol": "EURUSD", "timeframe": "H1"},
            "provenance": {"spec_sha256": "s", "cost_sha256": "c"},
            "quality": {"status": "PASS"}, "metrics": {"n_trades": 2, "net_pnl": -1.0, "return_fraction": -0.01, "profit_factor": .9, "max_drawdown_fraction": .2},
            "policy": {"seed": 7}, "diagnostics": {"permutation_test": {"p_value_one_sided": .5}}, "gates": []}


def test_append_and_count_are_deterministic(tmp_path):
    append_trial(tmp_path, _record())
    assert count_trials(tmp_path) == {"total": 1, "by_hypothesis": {"001": 1}, "by_family": {"trend_cross": 1}}
    assert json.loads((tmp_path / "data/trials_registry.jsonl").read_text())["run_id"] == "r1"


def test_duplicate_run_rejected(tmp_path):
    append_trial(tmp_path, _record())
    try:
        append_trial(tmp_path, _record())
    except ValueError as error:
        assert "duplicado" in str(error)
    else:
        raise AssertionError("se aceptó un run_id duplicado")
