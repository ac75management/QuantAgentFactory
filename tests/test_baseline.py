"""qaf.baseline: comprar y mantener con el mismo ledger de costos que
qaf.engine.simulate y el mismo capital (1x), usado por la puerta obligatoria
beats_baseline de qaf.validation.screening_gates (CLAUDE.md regla 19)."""
from copy import deepcopy
import math

import numpy as np
import pandas as pd
import pytest

from qaf.baseline import capital_matched_lots, simulate_baseline
from qaf.costs import execution_cost, financing, margin_cash_per_lot, price_cash
from qaf.io import ROOT, read_json
from qaf.metrics import summarize
from qaf.validation import screening_gates, validate_policy


@pytest.fixture
def instrument():
    c = deepcopy(read_json(ROOT / 'config/instruments.json')['XAUUSD'])
    c.update(spread_points=2, slippage_points_per_side=1, swap_long=-2, swap_short=1, volume_min=.01, volume_step=.01)
    return c


@pytest.fixture
def bars():
    rng = np.random.default_rng(7)
    close = 2000 + np.cumsum(rng.normal(0, 8, 90))
    opening = np.r_[close[0], close[:-1]]
    return pd.DataFrame({'time': pd.date_range('2020-01-01', periods=90, freq='D', tz='UTC'), 'open': opening, 'high': np.maximum(opening, close) + 3, 'low': np.minimum(opening, close) - 3, 'close': close})


def _policy():
    return validate_policy({'min_trades': 1, 'min_profit_factor': 1.3, 'max_drawdown_fraction': 0.5, 'min_friction_ratio': 3.0, 'bootstrap_iterations': 200, 'seed': 1, 'campaign_max_trials': 10,
                            'sensitivity_mc_iterations': 200, 'sensitivity_mc_range': 0.2, 'sensitivity_min_valid': 100,
                            'sensitivity_max_original_percentile': 0.8, 'sensitivity_min_positive_share': 0.5})


def _diagnostics(stress_pnl=100.0, ci=(0.1, 0.3)):
    return {'cost_stress_2x': {'net_pnl': stress_pnl}, 'bootstrap': {'status': 'DIAGNOSTIC', 'n': 40, 'iterations': 200, 'mean_r_ci95': list(ci)},
            'permutation_test': {'status': 'EXECUTED', 'p_value_one_sided': 0.01}, 'parameter_sensitivity': {'status': 'EXECUTED', 'original_percentile': 0.5, 'positive_share': 0.9}}


def test_default_sizing_invests_same_capital_1x(instrument, bars):
    result = simulate_baseline(bars, instrument, initial_equity=100000)
    notional_per_lot = margin_cash_per_lot(float(bars.open.iloc[0]), instrument)
    expected = math.floor(100000 / notional_per_lot / .01 + 1e-9) * .01
    sizing = result['sizing']
    assert sizing['method'] == 'capital_matched_1x'
    assert sizing['lots'] == pytest.approx(expected)
    assert 1 - .01 * notional_per_lot / 100000 <= sizing['notional_to_capital'] <= 1


def test_capital_matched_lots_is_comparable_across_contracts():
    instruments = read_json(ROOT / 'config/instruments.json')
    # Mismo capital -> mismo nocional aproximado, aunque 1 lote valga muy distinto por contrato.
    for symbol, price in (('XAUUSD', 2000.0), ('US30', 30000.0), ('EURUSD', 1.1), ('USDJPY', 150.0)):
        c = instruments[symbol]
        lots = capital_matched_lots(price, c, 100000)
        assert lots * margin_cash_per_lot(price, c) <= 100000 + 1e-6
        assert (lots + c['volume_step']) * margin_cash_per_lot(price, c) > 100000


def test_capital_too_small_for_volume_min_is_explicit_error(instrument):
    with pytest.raises(ValueError, match='volume_min'):
        capital_matched_lots(2000.0, instrument, 100)


def test_baseline_reconciles_and_matches_summarize(instrument, bars):
    result = simulate_baseline(bars, instrument, lots=1.0, initial_equity=100000)
    metrics = summarize(result)
    assert metrics['n_trades'] == 1
    assert math.isclose(100000 + metrics['net_pnl'], result['equity'][-1]['balance'], abs_tol=1e-6)
    assert result['trades'][0]['exit_reason'] == 'END_OF_SAMPLE'


def test_baseline_gross_pnl_is_tick_size_correct(instrument, bars):
    result = simulate_baseline(bars, instrument, lots=1.0)
    trade = result['trades'][0]
    expected_gross = (float(bars.close.iloc[-1]) - float(bars.open.iloc[0])) / instrument['tick_size'] * instrument['tick_value']
    assert trade['gross_pnl'] == pytest.approx(expected_gross)


def test_baseline_independent_recomputation(instrument, bars):
    """Recalcula con las primitivas de costs.py directamente, sin pasar por qaf.baseline."""
    times = bars.time.tolist()
    entry = float(bars.open.iloc[0])
    e_spread, e_slip, e_comm = execution_cost(entry, 1.0, instrument)
    fin = sum(financing(times[i - 1], times[i], 1, 1.0, instrument) for i in range(1, len(times)))
    exit_price = float(bars.close.iloc[-1])
    x_spread, x_slip, x_comm = execution_cost(exit_price, 1.0, instrument)
    gross = price_cash(exit_price - entry, instrument, 1.0)
    expected_net = gross + fin - (e_spread + x_spread) - (e_slip + x_slip) - (e_comm + x_comm)
    result = simulate_baseline(bars, instrument, lots=1.0)
    assert result['trades'][0]['net_pnl'] == pytest.approx(expected_net)


def test_baseline_short_flips_direction_and_swap_leg(instrument, bars):
    long_result = simulate_baseline(bars, instrument, direction=1, lots=1.0)
    short_result = simulate_baseline(bars, instrument, direction=-1, lots=1.0)
    assert short_result['trades'][0]['gross_pnl'] == pytest.approx(-long_result['trades'][0]['gross_pnl'])
    # swap_long=-2, swap_short=1: signo y magnitud distintos.
    assert short_result['trades'][0]['financing_cashflow'] != pytest.approx(-long_result['trades'][0]['financing_cashflow'])


def test_baseline_liquidates_when_insolvent_at_open(instrument, bars):
    instrument['swap_long'] = -40000
    result = simulate_baseline(bars, instrument, initial_equity=100000)
    trade = result['trades'][0]
    assert trade['exit_reason'] == 'INSOLVENT_OPEN'
    assert trade['exit_bar'] < len(bars) - 1
    after = result['equity'][trade['exit_bar']:]
    assert all(row['exposed'] == 0 for row in after[1:])
    assert len({row['balance'] for row in after}) == 1
    assert math.isclose(100000 + trade['net_pnl'], result['equity'][-1]['balance'], abs_tol=1e-6)


def test_baseline_rejects_invalid_inputs(instrument, bars):
    with pytest.raises(ValueError):
        simulate_baseline(bars, instrument, direction=0)
    with pytest.raises(ValueError):
        simulate_baseline(bars, instrument, lots=0)
    with pytest.raises(ValueError):
        simulate_baseline(bars, instrument, lots=-1)
    with pytest.raises(ValueError):
        simulate_baseline(bars.iloc[:1], instrument)
    with pytest.raises(ValueError):
        simulate_baseline(bars, instrument, initial_equity=0)


def test_gate_passes_only_when_strategy_beats_baseline():
    ok = {'n_trades': 40, 'net_pnl': 1000.0, 'profit_factor': 2.0, 'max_drawdown_fraction': 0.1, 'friction_ratio': 5.0}
    decision, gates = screening_gates(ok, _diagnostics(), {'status': 'PASS'}, [], _policy(), {'net_pnl': 500.0})
    assert next(g for g in gates if g['gate'] == 'beats_baseline')['status'] == 'PASS'
    assert decision == 'READY_FOR_FROZEN_VALIDATION'

    below = {**ok, 'net_pnl': 300.0}  # positiva, pero bajo el baseline de 500
    decision, gates = screening_gates(below, _diagnostics(), {'status': 'PASS'}, [], _policy(), {'net_pnl': 500.0})
    assert next(g for g in gates if g['gate'] == 'beats_baseline')['status'] == 'FAIL'
    assert decision == 'DISCARDED_IS'


def test_gate_rejects_negative_strategy_even_if_above_negative_baseline():
    metrics = {'n_trades': 40, 'net_pnl': -1000.0, 'profit_factor': 0.9, 'max_drawdown_fraction': 0.1, 'friction_ratio': 5.0}
    decision, gates = screening_gates(metrics, _diagnostics(-1500.0, (-0.2, -0.05)), {'status': 'PASS'}, [], _policy(), {'net_pnl': -5000.0})
    assert next(g for g in gates if g['gate'] == 'beats_baseline')['status'] == 'FAIL'
    assert decision == 'DISCARDED_IS'


def test_missing_baseline_fails_closed_instead_of_disappearing():
    metrics = {'n_trades': 40, 'net_pnl': 1000.0, 'profit_factor': 2.0, 'max_drawdown_fraction': 0.1, 'friction_ratio': 5.0}
    decision, gates = screening_gates(metrics, _diagnostics(), {'status': 'PASS'}, [], _policy())
    gate = next(g for g in gates if g['gate'] == 'beats_baseline')
    assert gate['status'] == 'FAIL' and gate['observed'] == 'NOT_COMPUTED'
    assert decision == 'DISCARDED_IS'
