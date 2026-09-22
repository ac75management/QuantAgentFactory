from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json
import numpy as np
import pandas as pd
import pytest
from qaf.costs import points_cash,execution_cost,financing,margin_cash_per_lot
from qaf.engine import simulate,resolve_exit
from qaf.data import inspect_frame
from qaf.signals import generate,rsi
from qaf.metrics import summarize,block_bootstrap
from qaf.registry import Registry
from qaf.io import ROOT,read_json
from qaf.runner import run_daily
from qaf.data import load_is
from qaf.validation import screening_gates
from qaf.contracts import validate_instrument


def write_manifest(tmp_path,symbol,timeframe,cutoff_after='2030-01-01T00:00:00+00:00',rows_is=360,rows_oos=30):
    manifest_path=tmp_path/'data/clean/manifest.json'
    manifest_path.parent.mkdir(parents=True,exist_ok=True)
    manifest={'symbols':[{'symbol':symbol,'timeframe':timeframe,'is_oos_cutoff_date':cutoff_after,'rows_is':rows_is,'rows_oos':rows_oos}]}
    manifest_path.write_text(json.dumps(manifest))


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


def test_rsi_bounds_and_causal(bars):
    r=rsi(bars,2)
    finite=r[np.isfinite(r)]
    assert ((finite>=0)&(finite<=100)).all()
    assert np.array_equal(rsi(bars,2)[:200],rsi(bars.iloc[:200],2)[:200],equal_nan=True)


def test_rsi_zero_loss_and_flat_cases():
    def frame(values):
        return pd.DataFrame({'close':values})
    assert rsi(frame([1,2,3,4,5]),2)[-1] == 100
    assert rsi(frame([5,4,3,2,1]),2)[-1] == 0
    assert rsi(frame([3,3,3,3,3]),2)[-1] == 50


def test_oscillator_reversion_causal(bars):
    s={'family':'oscillator_reversion','parameters':{'rsi_period':2,'entry_threshold':10,'trend_filter_sma':50},'direction':'both'}
    assert np.array_equal(generate(bars,s)[:250],generate(bars.iloc[:250],s))


def test_oscillator_reversion_end_to_end(bars,instrument):
    osc_spec={
        'id':'test-oscillator','family':'oscillator_reversion','symbol':'XAUUSD','timeframe':'D1',
        'parameters':{'atr_period':14,'sl_atr':1.5,'tp_atr':3.0,'max_holding':5,'rsi_period':2,'entry_threshold':10,'trend_filter_sma':50},
        'rationale':'RSI(2) con filtro de tendencia SMA50.','hypothesis_id':'TEST-001','risk_fraction':0.005,
        'initial_equity':100000,'direction':'both','version':1,
    }
    result=simulate(bars,osc_spec,instrument)
    assert result['trades']
    assert result['equity'][-1]['equity']==pytest.approx(result['initial_equity']+sum(t['net_pnl'] for t in result['trades']))


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
    write_manifest(tmp_path,'XAUUSD','D1')
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
    bars.tail(30).to_parquet(path/'OOS.parquet')
    write_manifest(tmp_path,'XAUUSD','D1')
    summary,folder=run_daily(tmp_path,day='2026-09-22')
    assert summary['executed']==1
    assert any('INVALID_SPEC' in u['reason'] for u in summary['unavailable'])
    assert (folder/'report.html').exists()


def test_load_is_requires_manifest_and_oos(tmp_path,bars):
    path=tmp_path/'data/clean/XAUUSD/D1';path.mkdir(parents=True)
    bars.to_parquet(path/'IS.parquet')
    with pytest.raises(FileNotFoundError,match='OOS'):
        load_is('XAUUSD','D1',tmp_path)
    bars.tail(30).to_parquet(path/'OOS.parquet')
    with pytest.raises(FileNotFoundError,match='manifest'):
        load_is('XAUUSD','D1',tmp_path)
    write_manifest(tmp_path,'XAUUSD','D1')
    df,info=load_is('XAUUSD','D1',tmp_path)
    assert len(df)==len(bars)


def test_frequency_check_detects_timeframe_mismatch():
    n=100
    df=pd.DataFrame({'time':pd.date_range('2024-01-01',periods=n,freq='2h',tz='UTC'),'open':100.0,'high':101.0,'low':99.0,'close':100.5})
    checks={c['check']:c for c in inspect_frame(df,'H4')['checks']}
    assert checks['frequency']['status']=='FAIL'
    assert checks['frequency']['detail']['median_nominal_minutes']==pytest.approx(120.0)


@pytest.mark.parametrize('minutes,timeframe',[(65,'H1'),(260,'H4'),(1560,'D1')])
def test_frequency_rejects_nearby_wrong_cadence(minutes,timeframe):
    n=100
    df=pd.DataFrame({'time':pd.date_range('2024-01-01',periods=n,freq=f'{minutes}min',tz='UTC'),'open':100.0,'high':101.0,'low':99.0,'close':100.5})
    checks={c['check']:c for c in inspect_frame(df,timeframe)['checks']}
    assert checks['frequency']['status']=='FAIL'


def test_gates_reject_impossible_metrics():
    policy=read_json(ROOT/'config/runner.json')
    metrics={'net_pnl':float('inf'),'profit_factor':float('inf'),'max_drawdown_fraction':-1,'friction_ratio':float('inf'),'n_trades':999}
    diagnostics={'bootstrap':{'mean_r_ci95':[1,-1]},'cost_stress_2x':{'net_pnl':float('inf')}}
    decision,gates=screening_gates(metrics,diagnostics,{'status':'PASS'},[],policy)
    assert decision=='DISCARDED_IS'
    assert all(g['status']=='FAIL' for g in gates if g['gate']!='minimum_trades')


def test_gates_blocked_on_failed_quality():
    policy=read_json(ROOT/'config/runner.json')
    metrics={'net_pnl':1,'profit_factor':2,'max_drawdown_fraction':0.05,'friction_ratio':5,'n_trades':999}
    diagnostics={'bootstrap':{'mean_r_ci95':[0.1,0.2]},'cost_stress_2x':{'net_pnl':1}}
    decision,gates=screening_gates(metrics,diagnostics,{'status':'FAIL'},[],policy)
    assert decision=='BLOCKED_DATA'
    assert gates==[]


def test_margin_uses_same_conversion_as_pnl():
    instruments=read_json(ROOT/'config/instruments.json')
    assert margin_cash_per_lot(90,instruments['USDJPY'])==100000
    assert margin_cash_per_lot(160,instruments['USDJPY'])==100000
    assert margin_cash_per_lot(1.2,instruments['EURUSD'])==120000
    assert margin_cash_per_lot(2000,instruments['XAUUSD'])==200000
    assert margin_cash_per_lot(18000,instruments['DAX'])==pytest.approx(18000*10*1.14712)


def test_registry_recovers_stale_running(tmp_path):
    r=Registry(tmp_path/'registry.sqlite')
    assert r.reserve('a','2026-09-22','test','{}',5,5,stale_after_seconds=3600)=='RESERVED'
    # Recien reservado: todavia no es candidato a recuperacion.
    assert r.reserve('a','2026-09-22','test','{}',5,5,stale_after_seconds=3600)=='DUPLICATE'
    # Simula un proceso caido: la reserva quedo RUNNING hace mas de una hora.
    old=(datetime.now(timezone.utc)-timedelta(hours=2)).isoformat()
    r.db.execute('UPDATE trials SET reserved_at=? WHERE run_id=?',(old,'a'))
    assert r.reserve('a','2026-09-22','test','{}',5,5,stale_after_seconds=3600)=='RESERVED'
    r.close()


def test_registry_stale_worker_cannot_overwrite_replacement(tmp_path):
    path=tmp_path/'registry.sqlite'
    old_worker=Registry(path)
    new_worker=Registry(path)
    assert old_worker.reserve('a','2026-09-22','test','{"attempt":"old"}',5,5)=='RESERVED'
    old=(datetime.now(timezone.utc)-timedelta(hours=2)).isoformat()
    old_worker.db.execute('UPDATE trials SET reserved_at=? WHERE run_id=?',(old,'a'))
    assert new_worker.reserve('a','2026-09-22','test','{"attempt":"new"}',5,5)=='RESERVED'
    with pytest.raises(RuntimeError,match='Lease perdido'):
        old_worker.finish('a','DONE','old-result')
    row=new_worker.rows()[0]
    assert row['status']=='RUNNING' and row['spec_json']=='{"attempt":"new"}'
    new_worker.finish('a','DONE','new-result')
    old_worker.close();new_worker.close()


def test_contract_rejects_critical_ambiguities(instrument):
    validate_instrument(instrument)
    for change in ({'volume_step':20},{'timeframes':['D1','D1']},{'costs_verified':'false'},{'as_of':'not-a-date'},{'margin_calc_mode':'forex_base_account'}):
        bad=deepcopy(instrument);bad.update(change)
        with pytest.raises(ValueError):
            validate_instrument(bad)


def test_gates_reject_fractional_count_and_incomplete_bootstrap():
    policy=read_json(ROOT/'config/runner.json')
    metrics={'net_pnl':1,'profit_factor':2,'max_drawdown_fraction':0.05,'friction_ratio':5,'n_trades':30.5}
    diagnostics={'bootstrap':{'status':'INCONCLUSIVE','n':1,'mean_r_ci95':[0.1,0.2]},'cost_stress_2x':{'net_pnl':1}}
    decision,gates=screening_gates(metrics,diagnostics,{'status':'PASS'},[],policy)
    assert decision=='INCONCLUSIVE'
    assert next(g for g in gates if g['gate']=='bootstrap_lower_bound')['status']=='FAIL'
