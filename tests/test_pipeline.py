"""qaf.pipeline: fase y siguiente agente permitido, derivados solo de artefactos."""
import json

import pytest

from qaf.io import ROOT, canonical, digest
from qaf.pipeline import check_turn, pipeline_state
from qaf.registry import Registry

SPEC = {'id': 'demo-xauusd-d1', 'family': 'streak_reversal', 'symbol': 'XAUUSD', 'timeframe': 'D1',
        'parameters': {'atr_period': 14, 'sl_atr': 1.5, 'tp_atr': 3.0, 'max_holding': 5, 'streak': 3},
        'rationale': 'Prueba.', 'hypothesis_id': '010', 'risk_fraction': 0.005, 'initial_equity': 100000, 'direction': 'both', 'version': 1}


def _repo(tmp_path, status='pending', doc=True, spec=False, spec_md=True, registered=False):
    (tmp_path / 'config/strategies').mkdir(parents=True)
    (tmp_path / 'config/hypotheses.json').write_text(json.dumps({'version': 1, 'hypotheses': [{'id': '010', 'slug': 'demo', 'status': status}]}))
    (tmp_path / 'docs/hypotheses').mkdir(parents=True)
    (tmp_path / 'docs/specs').mkdir(parents=True)
    if doc:
        (tmp_path / 'docs/hypotheses/demo.md').write_text('# demo')
    if spec:
        (tmp_path / 'docs/specs/demo.json').write_text(json.dumps(SPEC))
        if spec_md:
            (tmp_path / 'docs/specs/demo.md').write_text('# demo spec')
    if registered:
        (tmp_path / f'config/strategies/{digest(SPEC)[:24]}.json').write_text(json.dumps(SPEC))
    return tmp_path


def _row(root):
    return pipeline_state(root)['hypotheses'][0]


def _trial(root, status):
    registry = Registry(root / 'state/research.sqlite3')
    try:
        registry.reserve('run-1', '2026-09-22', 'test', canonical(SPEC), 5, 5)
        if status != 'RUNNING':
            registry.finish('run-1', status, 'result.json')
    finally:
        registry.close()


@pytest.mark.parametrize('kwargs,stage,actor', [
    ({'doc': False}, 'NEEDS_HYPOTHESIS_DOC', 'investigator'),
    ({}, 'NEEDS_SPEC', 'protocol'),
    ({'spec': True}, 'NEEDS_REGISTRATION', 'engine'),
    ({'spec': True, 'registered': True}, 'NEEDS_IS_RUN', 'engine'),
])
def test_stage_progression_before_any_run(tmp_path, kwargs, stage, actor):
    row = _row(_repo(tmp_path, **kwargs))
    assert (row['stage'], row['next_actor']) == (stage, actor)


def test_running_trial_means_wait(tmp_path):
    root = _repo(tmp_path, spec=True, registered=True)
    _trial(root, 'RUNNING')
    row = _row(root)
    assert (row['stage'], row['next_actor']) == ('RUNNING', None)


def test_finished_run_goes_to_validator_until_status_changes(tmp_path):
    root = _repo(tmp_path, spec=True, registered=True)
    _trial(root, 'DISCARDED_IS')
    row = _row(root)
    assert (row['stage'], row['next_actor']) == ('NEEDS_VALIDATOR_REVIEW', 'validator')
    assert 'DISCARDED_IS' in row['next_action']


def test_technical_error_returns_to_engine_not_validator(tmp_path):
    root = _repo(tmp_path, spec=True, registered=True)
    _trial(root, 'TECHNICAL_ERROR')
    row = _row(root)
    assert (row['stage'], row['next_actor']) == ('NEEDS_IS_RUN', 'engine')
    assert 'TECHNICAL_ERROR' in row['next_action']


def test_running_task_blocks_every_agent(tmp_path):
    root = _repo(tmp_path)
    registry = Registry(root / 'state/research.sqlite3')
    try:
        registry.start_task('protocol:010', None, '010', 'contract', 'protocol')
    finally:
        registry.close()
    assert _row(root)['stage'] == 'RUNNING'
    assert check_turn('010', 'protocol', root)[0] is False


@pytest.mark.parametrize('status,stage,actor', [
    ('discarded_is', 'CLOSED', None),
    ('rejected_by_user', 'CLOSED', None),
    ('blocked_architecture', 'BLOCKED', 'alexander'),
    ('inconclusive', 'NEEDS_DECISION', 'alexander'),
    ('ready_for_frozen_validation', 'FROZEN_VALIDATION_BLOCKED', 'validator'),
    ('approved', 'APPROVED', 'alexander'),
    ('maybe', 'INCONSISTENT', 'alexander'),
])
def test_terminal_and_unknown_statuses(tmp_path, status, stage, actor):
    row = _row(_repo(tmp_path, status=status))
    assert (row['stage'], row['next_actor']) == (stage, actor)


def test_ready_for_frozen_validation_is_not_validated(tmp_path):
    action = _row(_repo(tmp_path, status='ready_for_frozen_validation'))['next_action']
    assert 'no validada' in action and 'holdout' in action


def test_registration_without_protocol_contract_freezes_the_hypothesis(tmp_path):
    root = _repo(tmp_path)
    (root / f'config/strategies/{digest(SPEC)[:24]}.json').write_text(json.dumps(SPEC))
    state = pipeline_state(root)
    assert state['violations'][0]['severity'] == 'error'
    assert 'protocol saltado' in state['violations'][0]['issue']
    assert (state['hypotheses'][0]['stage'], state['hypotheses'][0]['next_actor']) == ('INCONSISTENT', 'alexander')


def test_spec_edited_after_registration_is_detected(tmp_path):
    root = _repo(tmp_path, spec=True, registered=True)
    edited = {**SPEC, 'parameters': {**SPEC['parameters'], 'streak': 4}}
    (root / 'docs/specs/demo.json').write_text(json.dumps(edited))
    assert _row(root)['stage'] == 'INCONSISTENT'


def test_contract_without_narrative_is_a_violation(tmp_path):
    root = _repo(tmp_path, spec=True, spec_md=False)
    assert any('sin narrativa' in v['issue'] for v in pipeline_state(root)['violations'])
    assert _row(root)['stage'] == 'INCONSISTENT'


def test_closed_hypothesis_history_is_only_a_warning(tmp_path):
    root = _repo(tmp_path, status='discarded_is')
    (root / f'config/strategies/{digest(SPEC)[:24]}.json').write_text(json.dumps(SPEC))
    state = pipeline_state(root)
    assert [v['severity'] for v in state['violations']] == ['warning']
    assert state['hypotheses'][0]['stage'] == 'CLOSED'


def test_check_turn_allows_only_the_next_actor(tmp_path):
    root = _repo(tmp_path)
    assert check_turn('010', 'protocol', root)[0] is True
    for actor in ('investigator', 'engine', 'validator'):
        allowed, message = check_turn('010', actor, root)
        assert allowed is False and 'le toca a protocol' in message
    assert check_turn('999', 'protocol', root)[0] is False
    with pytest.raises(ValueError):
        check_turn('010', 'optimizer', root)


def test_repository_pipeline_has_no_blocking_violations():
    state = pipeline_state(ROOT)
    assert [v for v in state['violations'] if v['severity'] == 'error'] == []
    assert all(row['stage'] != 'INCONSISTENT' for row in state['hypotheses'])
