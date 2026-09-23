"""Coherencia de estados de hipótesis (qaf.consistency) y bloqueo explícito de OOS (qaf.holdout)."""
import json
import sqlite3

import pytest

from qaf.consistency import STATUS_MARKERS, check_hypothesis_registry
from qaf.holdout import PREREQUISITES, ROADMAP, FinalValidationBlocked, freeze, validate_final
from qaf.io import ROOT

HEADER = '| # | slug | fecha | fuente/autor | activo/timeframe | estado |\n|---|---|---|---|---|---|\n'


def _write(tmp_path, hypotheses, markdown_rows):
    (tmp_path / 'config').mkdir(exist_ok=True)
    (tmp_path / 'config/hypotheses.json').write_text(json.dumps({'version': 1, 'hypotheses': hypotheses}))
    (tmp_path / 'docs/hypotheses').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'docs/hypotheses/_registry.md').write_text('# Registro\n\n' + HEADER + ''.join(markdown_rows), encoding='utf-8')


def test_repository_registry_is_consistent():
    errors = [i for i in check_hypothesis_registry(ROOT) if i['severity'] == 'error']
    assert errors == []


def test_consistent_registry_has_no_issues(tmp_path):
    _write(tmp_path, [{'id': '001', 'status': 'discarded_is'}, {'id': '002', 'status': 'pending'}],
           ['| 001 | a | 2026-09-22 | x | XAUUSD / D1 | **DISCARDED_IS** — perdió antes de costos |\n',
            '| 002 | b | 2026-09-22 | x | DAX / H4 | pendiente |\n'])
    assert check_hypothesis_registry(tmp_path) == []


def test_detects_unknown_status_and_mirror_drift(tmp_path):
    _write(tmp_path, [{'id': '001', 'status': 'maybe'}, {'id': '002', 'status': 'discarded_is'}, {'id': '003', 'status': 'pending'}],
           ['| 001 | a | d | x | y | pendiente |\n', '| 002 | b | d | x | y | pendiente |\n', '| 004 | c | d | x | y | pendiente |\n'])
    issues = {(i['hypothesis_id'], i['severity']): i['issue'] for i in check_hypothesis_registry(tmp_path)}
    assert 'vocabulario' in issues[('001', 'error')]
    assert 'no refleja' in issues[('002', 'error')]
    assert 'no en docs/hypotheses/_registry.md' in issues[('003', 'error')]
    assert 'no en config/hypotheses.json' in issues[('004', 'error')]


def test_warns_when_runnable_hypothesis_already_discarded_in_sqlite(tmp_path):
    _write(tmp_path, [{'id': '001', 'status': 'pending'}], ['| 001 | a | d | x | y | pendiente |\n'])
    (tmp_path / 'state').mkdir()
    db = sqlite3.connect(tmp_path / 'state/research.sqlite3')
    db.execute('CREATE TABLE tasks (task_id TEXT, hypothesis_id TEXT, stage TEXT, status TEXT, reason_code TEXT)')
    db.execute("INSERT INTO tasks VALUES ('is:x','001','is_backtest','completed','DISCARDED_IS')")
    db.commit()
    db.close()
    issues = check_hypothesis_registry(tmp_path)
    assert [i['severity'] for i in issues] == ['warning']
    assert 'DISCARDED_IS' in issues[0]['issue']


def test_vocabulary_covers_pipeline_states():
    for status in ('pending', 'ready', 'discarded_is', 'invalid_por_datos', 'ready_for_frozen_validation', 'rejected_oos', 'approved'):
        assert status in STATUS_MARKERS


@pytest.mark.parametrize('call', [lambda: freeze('run'), lambda: validate_final('freeze')])
def test_final_validation_fails_closed_with_explicit_prerequisites(call):
    with pytest.raises(FinalValidationBlocked) as error:
        call()
    assert isinstance(error.value, NotImplementedError)
    message = str(error.value)
    assert ROADMAP in message and 'OOS no abierto' in message
    assert all(item in message for item in PREREQUISITES)
    assert (ROOT / ROADMAP).exists()


def test_universe_mirror_is_generated_from_instruments_and_drift_fails(tmp_path):
    from qaf.consistency import UNIVERSE_END, UNIVERSE_START, check_universe_mirror, write_universe_mirror
    (tmp_path / 'config').mkdir()
    (tmp_path / 'docs').mkdir()
    contract = {'XAUUSD': {'symbol_mt5': 'XAUUSD', 'asset_class': 'commodity_cfd', 'timeframes': ['H4', 'D1'], 'status': 'research'}}
    (tmp_path / 'config/instruments.json').write_text(json.dumps(contract), encoding='utf-8')
    (tmp_path / 'docs/universe.md').write_text(f'# Universo\n{UNIVERSE_START}\n{UNIVERSE_END}\nnotas humanas\n', encoding='utf-8')
    assert check_universe_mirror(tmp_path)

    write_universe_mirror(tmp_path)
    text = (tmp_path / 'docs/universe.md').read_text(encoding='utf-8')
    assert check_universe_mirror(tmp_path) == []
    assert '| XAUUSD | XAUUSD | commodity_cfd | H4, D1 | research |' in text and 'notas humanas' in text

    contract['XAUUSD']['timeframes'].append('H1')
    (tmp_path / 'config/instruments.json').write_text(json.dumps(contract), encoding='utf-8')
    assert 'regenerar' in check_universe_mirror(tmp_path)[0]['issue']


def test_universe_mirror_without_markers_is_an_error(tmp_path):
    from qaf.consistency import check_universe_mirror
    (tmp_path / 'docs').mkdir()
    (tmp_path / 'docs/universe.md').write_text('| XAUUSD | editado a mano |\n', encoding='utf-8')
    assert check_universe_mirror(tmp_path)[0]['severity'] == 'error'
