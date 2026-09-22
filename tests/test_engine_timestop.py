"""Politica de time-stop en la barra limite (entry_bar + max_holding).

La salida por tiempo se ejecuta al OPEN de esa barra. Solo los eventos que
ocurren en el open (gap a traves del stop o del target) la preceden, con los
mismos precios conservadores de cualquier otra barra. Los toques intrabar de esa
barra nunca aplican: la posicion ya se cerro al open. Aplicar el time-stop "solo
si no se toco stop/target intrabar" seria look-ahead (al open no se conoce el
rango posterior de la barra).
"""
from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from qaf.engine import simulate
from qaf.io import ROOT, read_json

ENTRY_BAR = 5
MAX_HOLDING = 3
LIMIT_BAR = ENTRY_BAR + MAX_HOLDING


@pytest.fixture
def instrument():
    c = deepcopy(read_json(ROOT / 'config/instruments.json')['XAUUSD'])
    c.update(spread_points=2, slippage_points_per_side=1, volume_min=.01, volume_step=.01)
    return c


def _spec(max_holding=MAX_HOLDING):
    return {'id': 'timestop-test', 'family': 'streak_reversal', 'symbol': 'XAUUSD', 'timeframe': 'D1',
            'parameters': {'atr_period': 2, 'sl_atr': 1.0, 'tp_atr': 1.0, 'max_holding': max_holding, 'streak': 2},
            'rationale': 'Prueba de politica de salida.', 'hypothesis_id': 'TEST-TIMESTOP', 'risk_fraction': 0.005,
            'initial_equity': 100000, 'direction': 'both'}


def _bars(limit_bar_ohlc):
    """Rango constante 2.0 -> ATR=2 al entrar; largo en el open de ENTRY_BAR=100,
    stop=98, target=102. Barras intermedias quietas (sin toques)."""
    rows = []
    for i in range(12):
        if i < ENTRY_BAR:
            rows.append((100.0, 101.0, 99.0, 100.0))
        elif i == LIMIT_BAR:
            rows.append(limit_bar_ohlc)
        else:
            rows.append((100.0, 100.5, 99.5, 100.0))
    o, h, l, c = zip(*rows)
    return pd.DataFrame({'time': pd.date_range('2021-01-04', periods=12, freq='D', tz='UTC'),
                         'open': o, 'high': h, 'low': l, 'close': c})


def _run(limit_bar_ohlc, instrument, max_holding=MAX_HOLDING):
    df = _bars(limit_bar_ohlc)
    signal = np.zeros(len(df), dtype=int)
    signal[ENTRY_BAR - 1] = 1
    result = simulate(df, _spec(max_holding), instrument, signals_override=signal)
    assert len(result['trades']) == 1
    trade = result['trades'][0]
    assert trade['entry_bar'] == ENTRY_BAR and trade['entry_price'] == 100.0
    assert trade['stop'] == pytest.approx(98.0) and trade['target'] == pytest.approx(102.0)
    return trade


def test_time_stop_without_intrabar_touch(instrument):
    trade = _run((100.0, 100.5, 99.5, 100.0), instrument)
    assert (trade['exit_bar'], trade['exit_reason'], trade['exit_price']) == (LIMIT_BAR, 'TIME', 100.0)


def test_intrabar_stop_on_limit_bar_is_preempted_by_time_at_open(instrument):
    trade = _run((100.0, 100.5, 97.0, 99.0), instrument)
    assert (trade['exit_bar'], trade['exit_reason'], trade['exit_price']) == (LIMIT_BAR, 'TIME', 100.0)


def test_same_intrabar_stop_is_a_stop_when_not_on_limit_bar(instrument):
    trade = _run((100.0, 100.5, 97.0, 99.0), instrument, max_holding=20)
    assert (trade['exit_bar'], trade['exit_reason'], trade['exit_price']) == (LIMIT_BAR, 'STOP', 98.0)


def test_intrabar_target_on_limit_bar_is_preempted_by_time_at_open(instrument):
    trade = _run((100.0, 103.0, 99.5, 101.0), instrument)
    assert (trade['exit_bar'], trade['exit_reason'], trade['exit_price']) == (LIMIT_BAR, 'TIME', 100.0)


def test_stop_and_target_same_limit_bar_exit_at_open(instrument):
    trade = _run((100.0, 103.0, 97.0, 100.0), instrument)
    assert (trade['exit_bar'], trade['exit_reason'], trade['exit_price']) == (LIMIT_BAR, 'TIME', 100.0)


def test_gap_through_stop_on_limit_bar_keeps_stop_gap(instrument):
    trade = _run((97.0, 97.5, 96.5, 97.0), instrument)
    assert (trade['exit_bar'], trade['exit_reason'], trade['exit_price']) == (LIMIT_BAR, 'STOP_GAP', 97.0)


def test_gap_through_target_on_limit_bar_stays_conservative(instrument):
    # Antes: TIME al open (103, precio mas favorable). Ahora: mismo precio
    # conservador (target 102) que un gap de target en cualquier otra barra.
    trade = _run((103.0, 103.5, 102.5, 103.0), instrument)
    assert (trade['exit_bar'], trade['exit_reason'], trade['exit_price']) == (LIMIT_BAR, 'TARGET_GAP_CONSERVATIVE', 102.0)
