from copy import deepcopy
import json
import numpy as np
import pandas as pd
import pytest
from qaf.costs import points_cash,execution_cost,financing
from qaf.engine import simulate,resolve_exit
from qaf.data import inspect_frame
from qaf.signals import generate
from qaf.metrics import summarize,block_bootstrap
from qaf.registry import Registry
from qaf.io import ROOT,read_json
from qaf.runner import run_daily


@pytest.fixture
def instrument():
    c=deepcopy(read_json(ROOT/'config/instruments.json')['XAUUSD'])
    c.update(spread_points=2,slippage_points_per_side=1,swap_long=-2,swap_short=1,volume_min=.01,volume_step=.01)
    return c


@pytest.fixture
def bars():
    rng=np.random.default_rng(42)
    close=2000+np.cumsum(rng.normal(0,8,360))
    opening=np.r_[close[0],close[:-1]]
    return pd.DataFrame({'time':pd.date_range('2020-01-01',periods=360,freq='D',tz='UTC'),'open':opening,'high':np.maximum(opening,close)+3,'low':np.minimum(opening,close)-3,'close':close})


@pytest.fixture
def spec():
    return {
        'id': 'test-xauusd-d1',
        'family': 'streak_reversal',
        'family_id': 'streak_reversal',
        'symbol': 'XAUUSD',
        'timeframe': 'D1',
        'parameters': {'atr_period': 14, 'sl_atr': 1.5, 'tp_atr': 3.0, 'max_holding': 5, 'streak': 3},
        'rationale': 'Hipótesis de prueba controlada.',
        'hypothesis_id': 'TEST-001',
        'risk_fraction': 0.005,
        'initial_equity': 100000,
        'direction': 'both',
        'version': 1,
    }


def test_spread_units():
    c={'point':.01,'tick_size':.05,'tick_value':5}
    assert points_cash(55,c)==pytest.approx(55)
    assert points_cash(55,c,.1)==pytest.approx(5.5)


def test_snapshot_units():
    c=read_json(ROOT/'config/instruments.json')
    assert points_cash(55,c['XAUUSD'])==55
    assert points_cash(9,c['NAS100'])==9
    assert points_cash(4,c['EURUSD'])==4


def test_roundtrip_percent_uses_both_prices(instrument):
    instrument['commission_per_side']=.000025
    first=execution_cost(2000,1,instrument)[2]
    last=execution_cost(2100,1,instrument)[2]
    assert first+last==pytest.approx(10.25)


@pytest.mark.parametrize('direction,opening,high,low,stop,target,expected',[(1,90,92,89,98.5,110,90),(-1,110,112,109,101.5,90,110),(1,100,115,95,98,110,98),(-1,100,105,85,102,90,102)])
def test_gaps_and_ties(direction,opening,high,low,stop,target,expected):
    assert resolve_exit(direction,opening,high,low,stop,target)[0]==expected


def test_rollover_intraday_and_energy(instrument):
    start=pd.Timestamp('2026-09-23 20:00',tz='UTC')
    assert financing(start,start+pd.Timedelta(minutes=30),1,1,instrument)==0
    assert financing(start,start+pd.Timedelta(hours=2),1,1,instrument)==-6
    instrument['swap_schedule']='daily_equal'
    assert financing(start,start+pd.Timedelta(hours=2),1,1,instrument)==-2


def test_gate_nonfinite_and_duplicates(bars):
    bad=bars.copy();bad.loc[3,'high']=np.inf
    assert inspect_frame(bad,'D1')['status']=='FAIL'
    bad=bars.copy();bad.loc[3,'time']=bad.loc[2,'time']
    assert inspect_frame(bad,'D1')['status']=='FAIL'


def test_causal_signals(bars):
    s = {
        'family': 'streak_reversal',
        'parameters': {'streak': 3},
        'direction': 'both',
    }
    assert np.array_equal(generate(bars,s)[:200],generate(bars.iloc[:200],s))


def test_ledger_marking_and_stress(bars,spec,instrument):
    result=simulate(bars,spec,instrument)
    assert len(result['equity'])==len(bars)
    assert result['trades']
    assert result['equity'][-1]['equity']==pytest.approx(result['initial_equity']+sum(t['net_pnl'] for t in result['trades']))
    assert any(abs(r['floating_pnl'])>0 for r in result['equity'])
    assert all(t['slippage_cost']>0 for t in result['trades'])
    assert all(t['lots']/.01==pytest.approx(round(t['lots']/.01)) for t in result['trades'])
    assert 0<=summarize(result)['max_drawdown_fraction']
    # Doubling a cost at fixed price/size must never improve that execution cost.
    assert sum(execution_cost(2000,1,instrument,2))>sum(execution_cost(2000,1,instrument,1))


def test_no_trades_is_inconclusive(bars,spec,instrument):
    r=simulate(bars,spec,instrument,signals_override=np.zeros(len(bars)))
    assert summarize(r)['profit_factor'] is None
    assert block_bootstrap(r['trades'])['status']=='INCONCLUSIVE'


def test_registry_budget_idempotency(tmp_path):
    r=Registry(tmp_path/'registry.sqlite')
    assert r.reserve('a','2026-09-22','test','{}',1,2)=='RESERVED'
    assert r.reserve('a','2026-09-22','test','{}',1,2)=='DUPLICATE'
    assert r.reserve('b','2026-09-22','test','{}',1,2)=='BUDGET'
    assert r.reserve('b','2026-09-23','test','{}',1,2)=='RESERVED'
    assert r.reserve('c','2026-09-24','test','{}',1,2)=='BUDGET'
    r.close()


def test_end_to_end_without_oos(tmp_path,bars,instrument,spec):
    (tmp_path/'config').mkdir()
    policy=read_json(ROOT/'config/runner.json');policy.update(daily_max_trials=1,bootstrap_iterations=50)
    (tmp_path/'config/runner.json').write_text(json.dumps(policy))
    (tmp_path/'config/strategies').mkdir()
    instrument.update(status='research',timeframes=['D1'])
    (tmp_path/'config/instruments.json').write_text(json.dumps({'XAUUSD':instrument}))
    (tmp_path/'config/strategies/test.json').write_text(json.dumps(spec))
    (tmp_path/'docs/hypotheses').mkdir(parents=True)
    (tmp_path/'docs/hypotheses/_registry.md').write_text('| # | slug |\n|---|---|\n| TEST-001 | test-xauusd-d1 |\n')
    path=tmp_path/'data/clean/XAUUSD/D1';path.mkdir(parents=True)
    bars.to_parquet(path/'IS.parquet')
    (path/'OOS.parquet').write_bytes(b'POISON: this is not a parquet file')
    summary,folder=run_daily(tmp_path,day='2026-09-22')
    assert summary['executed']==1
    assert summary['runs'][0]['decision']!='TECHNICAL_ERROR'
    assert (folder/'report.html').exists()
    summary2,_=run_daily(tmp_path,day='2026-09-22')
    assert summary2['executed']==0
    assert (path/'OOS.parquet').read_bytes().startswith(b'POISON')


def test_invalid_spec_is_isolated_not_fatal(tmp_path,bars,instrument,spec):
    (tmp_path/'config').mkdir()
    policy=read_json(ROOT/'config/runner.json');policy.update(daily_max_trials=5,bootstrap_iterations=50)
    (tmp_path/'config/runner.json').write_text(json.dumps(policy))
    (tmp_path/'config/strategies').mkdir()
    instrument.update(status='research',timeframes=['D1'])
    (tmp_path/'config/instruments.json').write_text(json.dumps({'XAUUSD':instrument}))
    (tmp_path/'docs/hypotheses').mkdir(parents=True)
    (tmp_path/'docs/hypotheses/_registry.md').write_text('| # | slug |\n|---|---|\n| TEST-001 | test-xauusd-d1 |\n')
    (tmp_path/'config/strategies/good.json').write_text(json.dumps(spec))
    # Segunda spec con hypothesis_id que no existe en el registro: no debe tumbar el lote.
    bad=deepcopy(spec);bad['id']='bad-spec';bad['hypothesis_id']='999-no-existe'
    (tmp_path/'config/strategies/bad.json').write_text(json.dumps(bad))
    path=tmp_path/'data/clean/XAUUSD/D1';path.mkdir(parents=True)
    bars.to_parquet(path/'IS.parquet')
    summary,folder=run_daily(tmp_path,day='2026-09-22')
    assert summary['executed']==1
    assert any('INVALID_SPEC' in u['reason'] for u in summary['unavailable'])
    assert (folder/'report.html').exists()
