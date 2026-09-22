"""qaf.aed.permutation_test (hallazgo C1: confirmar la señal cruda antes de aceptar
el backtest costeado) y su puerta en qaf.validation.screening_gates."""
import math

import numpy as np
import pandas as pd
import pytest

from qaf.aed import permutation_test
from qaf.validation import screening_gates, validate_policy


def _policy(seed=11, iterations=300):
    return validate_policy({'min_trades': 1, 'min_profit_factor': 1.3, 'max_drawdown_fraction': 0.5, 'min_friction_ratio': 3.0, 'bootstrap_iterations': iterations, 'seed': seed, 'campaign_max_trials': 10,
                            'sensitivity_mc_iterations': 200, 'sensitivity_mc_range': 0.2, 'sensitivity_min_valid': 100,
                            'sensitivity_max_original_percentile': 0.8, 'sensitivity_min_positive_share': 0.5})


def _ohlc(closes):
    closes = np.asarray(closes, dtype=float)
    opens = np.r_[closes[0], closes[:-1]]
    highs = np.maximum(opens, closes) + 0.05
    lows = np.minimum(opens, closes) - 0.05
    times = pd.date_range('2000-01-01', periods=len(closes), freq='D', tz='UTC')
    return pd.DataFrame({'time': times, 'open': opens, 'high': highs, 'low': lows, 'close': closes})


def _random_walk(seed, n=900):
    return _ohlc(100 * np.exp(np.cumsum(np.random.default_rng(seed).normal(0, 0.01, n))))


def _breakout_spec():
    return {'family': 'channel_breakout', 'direction': 'both', 'parameters': {'lookback': 5, 'atr_period': 5, 'max_holding': 3, 'sl_atr': 1.5, 'tp_atr': 3.0}}


def _rigged_dataset(cycles=40, flat_len=180, base=100.0, jump=6.0, drift=1.2, buffer_len=6, decay_len=6, noise=0.0, seed=3):
    """Cada ruptura sobre la base plana va seguida de 3 barras de subida (= max_holding)
    y una meseta que deja resolver el horizonte completo incluso de la última señal que
    la regla re-dispara durante la subida. El tramo plano largo hace el efecto disperso:
    en una serie periódica corta muchas rotaciones circulares serían igual de predictivas."""
    rng = np.random.default_rng(seed)
    closes = []
    for _ in range(cycles):
        for _ in range(flat_len):
            closes.append(base + rng.normal(0, noise))
        cur = base + jump
        closes.append(cur)
        for _ in range(3):
            cur += drift
            closes.append(cur)
        peak = cur
        for _ in range(buffer_len):
            closes.append(peak + rng.normal(0, noise))
        for _ in range(decay_len):
            cur -= (peak - base) / decay_len
            closes.append(cur)
    return _ohlc(closes)


def _passing_inputs(permutation):
    """Métricas y diagnósticos que pasan todas las puertas salvo la que se prueba."""
    metrics = {'n_trades': 40, 'net_pnl': 1000.0, 'profit_factor': 2.0, 'max_drawdown_fraction': 0.1, 'friction_ratio': 5.0}
    diagnostics = {
        'cost_stress_2x': {'net_pnl': 100.0},
        'bootstrap': {'status': 'DIAGNOSTIC', 'n': 40, 'iterations': 300, 'mean_r_ci95': [0.1, 0.3]},
        'parameter_sensitivity': {'status': 'EXECUTED', 'original_percentile': 0.5, 'positive_share': 0.9},
    }
    if permutation is not None:
        diagnostics['permutation_test'] = permutation
    return metrics, diagnostics, {'net_pnl': 0.0}


def _gate(permutation):
    metrics, diagnostics, baseline = _passing_inputs(permutation)
    decision, gates = screening_gates(metrics, diagnostics, {'status': 'PASS'}, [], _policy(), baseline)
    return decision, next(g for g in gates if g['gate'] == 'aed_pattern_confirmed')


def test_detects_a_real_repeated_effect():
    result = permutation_test(_rigged_dataset(), _breakout_spec(), _policy())
    assert result['status'] == 'EXECUTED'
    assert result['n_signals'] >= 20
    assert result['observed_mean_directional_return'] > 0
    assert result['p_value_one_sided'] < 0.05


def test_random_walk_false_positive_rate_is_near_nominal():
    """Calibración: bajo H0 (random walk) la tasa de rechazo a alpha=5% debe ser
    cercana a 5%. El diseño previo (barras sueltas al azar) rechazaba ~8.5%."""
    pvalues = []
    for seed in range(60):
        result = permutation_test(_random_walk(1000 + seed), _breakout_spec(), _policy(iterations=200))
        assert result['status'] == 'EXECUTED'
        pvalues.append(result['p_value_one_sided'])
    rejections = sum(p < 0.05 for p in pvalues)
    assert rejections <= 8  # Binomial(60, 0.05): P(X>=9) < 0.01
    assert 0.3 < float(np.median(pvalues)) < 0.7


def test_inconclusive_below_min_signals():
    df = _ohlc(100 + np.cumsum(np.random.default_rng(1).normal(0, 0.2, 40)))
    result = permutation_test(df, _breakout_spec(), _policy(), min_signals=20)
    assert result['status'] == 'INCONCLUSIVE'
    assert result['n_signals'] < 20


def test_reproducible_with_same_seed():
    df = _random_walk(7)
    first = permutation_test(df, _breakout_spec(), _policy(seed=5))
    second = permutation_test(df, _breakout_spec(), _policy(seed=5))
    assert first == second
    assert first['seed'] == 5


def test_preserves_signal_count_and_directions():
    df = _random_walk(9)
    result = permutation_test(df, _breakout_spec(), _policy())
    assert result['n_long'] + result['n_short'] == result['n_signals']
    assert 0 < result['p_value_one_sided'] <= 1


def test_gate_passes_when_pattern_confirmed():
    decision, gate = _gate({'status': 'EXECUTED', 'p_value_one_sided': 0.01, 'n_signals': 40})
    assert gate['status'] == 'PASS'
    assert decision == 'READY_FOR_FROZEN_VALIDATION'


def test_gate_fails_when_pattern_not_confirmed():
    decision, gate = _gate({'status': 'EXECUTED', 'p_value_one_sided': 0.83, 'n_signals': 40})
    assert gate['status'] == 'FAIL'
    assert decision == 'DISCARDED_IS'


@pytest.mark.parametrize('p_value', [None, math.nan, math.inf, -0.1, 0.0, 1.5, 'x'])
def test_gate_fails_on_invalid_p_value(p_value):
    decision, gate = _gate({'status': 'EXECUTED', 'p_value_one_sided': p_value, 'n_signals': 40})
    assert gate['status'] == 'FAIL'
    assert decision == 'DISCARDED_IS'


def test_inconclusive_aed_makes_decision_inconclusive_not_silent():
    decision, gate = _gate({'status': 'INCONCLUSIVE', 'n_signals': 3, 'reason': 'pocas señales'})
    assert gate['status'] == 'INCONCLUSIVE'
    assert decision == 'INCONCLUSIVE'


@pytest.mark.parametrize('permutation', [None, {'status': 'NOT_EXECUTED'}, {}])
def test_missing_aed_fails_closed(permutation):
    decision, gate = _gate(permutation)
    assert gate['status'] == 'FAIL' and gate['observed'] == 'NOT_EXECUTED'
    assert decision == 'DISCARDED_IS'
