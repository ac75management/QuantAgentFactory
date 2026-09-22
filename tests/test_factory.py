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
from qaf.io import ROOT,read_json,load_registered_hypothesis_ids
from qaf.runner import run_daily
from qaf.data import load_is
from qaf.validation import screening_gates,validate_policy
from qaf.contracts import validate_instrument
from qaf.dashboard import render_dashboard,create_intake
from qaf.catalog import validate_candidate,assess_candidate,add_candidate,review_candidate,promote_candidate


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


def test_sensitivity_policy_is_explicit_and_fail_closed():
    policy=read_json(ROOT/'config/runner.json')
    assert validate_policy(policy) is policy
    for key in ('sensitivity_mc_iterations','sensitivity_mc_range','sensitivity_min_valid',
                'sensitivity_max_original_percentile','sensitivity_min_positive_share'):
        broken={k:v for k,v in policy.items() if k!=key}
        with pytest.raises(ValueError):
            validate_policy(broken)


def test_sensitivity_policy_rejects_incoherent_sample_requirement():
    policy=read_json(ROOT/'config/runner.json')
    policy['sensitivity_min_valid']=policy['sensitivity_mc_iterations']+1
    with pytest.raises(ValueError,match='no puede superar'):
        validate_policy(policy)


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


def test_registry_records_real_task_events(tmp_path):
    r=Registry(tmp_path/'registry.sqlite')
    r.start_task('is:abc','abc','004','is_backtest','engine','["spec.json"]')
    assert r.tasks()[0]['status']=='running'
    r.finish_task('is:abc','completed','DISCARDED_IS',None,'["result.json"]')
    assert r.tasks()[0]['status']=='completed'
    assert [e['event_type'] for e in reversed(r.events())]==['started','completed']
    r.close()


def test_dashboard_renders_repository_state(tmp_path):
    (tmp_path/'config/strategies').mkdir(parents=True)
    strategy={'id':'demo','hypothesis_id':'004','symbol':'US30','timeframe':'D1','family':'trend_cross'}
    (tmp_path/'config/strategies/demo.json').write_text(json.dumps(strategy))
    page=render_dashboard(tmp_path)
    assert 'Centro de Control' in page
    assert 'demo' in page and 'US30' in page
    assert 'Catálogo de ideas' in page


def test_dashboard_intake_creates_truthful_queued_task(tmp_path,instrument):
    (tmp_path/'config').mkdir()
    instrument.update(status='research',timeframes=['D1'])
    (tmp_path/'config/instruments.json').write_text(json.dumps({'XAUUSD':instrument}))
    intake_id=create_intake(tmp_path,{'idea':'Probar ruptura documentada con filtro de tendencia limpio.','symbol':'XAUUSD','timeframe':'D1','source':'Fuente de prueba'})
    payload=json.loads((tmp_path/'state/intakes'/f'{intake_id}.json').read_text())
    registry=Registry(tmp_path/'state/research.sqlite3')
    try:task=registry.tasks()[0]
    finally:registry.close()
    assert payload['status']=='queued_research'
    assert task['status']=='queued' and task['stage']=='evidence_review'


def test_structured_hypothesis_registry_is_authoritative(tmp_path):
    (tmp_path/'config').mkdir()
    payload={'version':1,'hypotheses':[{'id':'004','status':'pending'}]}
    (tmp_path/'config/hypotheses.json').write_text(json.dumps(payload))
    (tmp_path/'docs/hypotheses').mkdir(parents=True)
    (tmp_path/'docs/hypotheses/_registry.md').write_text('| # |\n|---|\n| 999 |\n')
    assert load_registered_hypothesis_ids(tmp_path)=={'004'}


def test_daily_skips_hypotheses_not_pending(tmp_path,bars,instrument,spec):
    (tmp_path/'config/strategies').mkdir(parents=True)
    policy=read_json(ROOT/'config/runner.json');policy.update(daily_max_trials=1,bootstrap_iterations=50)
    (tmp_path/'config/runner.json').write_text(json.dumps(policy))
    instrument.update(status='research',timeframes=['D1'])
    (tmp_path/'config/instruments.json').write_text(json.dumps({'XAUUSD':instrument}))
    (tmp_path/'config/strategies/test.json').write_text(json.dumps(spec))
    (tmp_path/'config/hypotheses.json').write_text(json.dumps({'version':1,'hypotheses':[{'id':'TEST-001','status':'discarded_is'}]}))
    path=tmp_path/'data/clean/XAUUSD/D1';path.mkdir(parents=True)
    bars.to_parquet(path/'IS.parquet');bars.tail(30).to_parquet(path/'OOS.parquet')
    write_manifest(tmp_path,'XAUUSD','D1')
    summary,_=run_daily(tmp_path,day='2026-09-22')
    assert summary['executed']==0
    assert any('HIPOTESIS_DISCARDED_IS' in row['reason'] for row in summary['unavailable'])


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


def test_catalog_triage_separates_external_idea_from_validation(instrument):
    candidate={
        'name':'Documented daily trend','source_name':'Quantpedia',
        'source_url':'https://quantpedia.com/example','primary_source_url':'https://doi.org/10.1/example',
        'publication_date':'2020-01-01','access_level':'public',
        'original_asset_classes':['commodity_cfd'],'instruments':['XAUUSD'],
        'original_timeframes':['D1'],'data_requirements':['OHLC'],
        'rules_summary':'A sufficiently explicit preliminary description of entry, exit, holding period and portfolio construction rules.',
        'code_available':False,'content_type':'strategy',
    }
    result=assess_candidate(candidate,{'XAUUSD':instrument})
    assert result['verdict']=='eligible_for_evidence_review'
    assert result['research_lane']=='mt5_now'
    assert 'validated' not in result and 'profitable' not in result


def test_catalog_requires_traceable_source():
    candidate={'name':'Idea','source_name':'Quantpedia','source_url':'not-a-url','original_asset_classes':['fx'],'original_timeframes':['D1'],'rules_summary':'x'}
    with pytest.raises(ValueError,match='source_url'):
        validate_candidate(candidate)


def test_catalog_add_queues_evidence_review(tmp_path,instrument):
    (tmp_path/'config').mkdir()
    (tmp_path/'config/instruments.json').write_text(json.dumps({'XAUUSD':instrument}))
    candidate={
        'name':'Candidate','source_name':'Quantpedia','source_url':'https://quantpedia.com/example',
        'primary_source_url':None,'access_level':'public','original_asset_classes':['commodity_cfd'],
        'instruments':['XAUUSD'],'original_timeframes':['D1'],'data_requirements':['OHLC'],
        'rules_summary':'This description is deliberately long enough to be reviewed but is not treated as an executable specification.',
        'code_available':False,'content_type':'strategy',
    }
    record,path=add_candidate(candidate,tmp_path)
    registry=Registry(tmp_path/'state/research.sqlite3')
    try: task=registry.tasks()[0]
    finally: registry.close()
    assert path.exists() and record['status']=='captured'
    assert task['stage']=='evidence_review' and task['status']=='queued'


def test_catalog_routes_methodology_without_calling_it_strategy(instrument):
    candidate={
        'name':'Transaction-cost review','source_name':'Alpha Architect',
        'source_url':'https://alphaarchitect.com/example','primary_source_url':'https://doi.org/10.1/costs',
        'access_level':'public','content_type':'methodology','original_asset_classes':['equity'],
        'original_timeframes':['D1'],'data_requirements':['OHLC'],
        'rules_summary':'A methodological review of capacity, turnover and implementation costs rather than an executable trading rule.',
        'code_available':False,
    }
    result=assess_candidate(candidate,{'XAUUSD':instrument})
    assert result['research_lane']=='methodology'


def test_catalog_distinguishes_original_market_from_qaf_target(instrument):
    candidate={
        'name':'Futures rule adapted to CFD','source_name':'Primary book',
        'source_url':'https://example.com/book','primary_source_url':None,
        'access_level':'subscription','content_type':'strategy','original_asset_classes':['future'],
        'instruments':['GC'],'original_timeframes':['D1'],'proposed_targets':[{'symbol':'XAUUSD','timeframe':'D1'}],
        'data_requirements':['OHLC'],'rules_summary':'A documented futures rule proposed for explicit adaptation to a CFD, pending evidence review and cost analysis.',
        'code_available':False,
    }
    result=assess_candidate(candidate,{'XAUUSD':instrument})
    assert result['research_lane']=='mt5_now'
    assert any('objetivo explícito' in reason for reason in result['reasons'])


def _catalog_candidate():
    return {
        'candidate_id':'IDEA-TEST0001','name':'Documented daily trend',
        'source_name':'Quantpedia','source_url':'https://quantpedia.com/example',
        'primary_source_url':'https://doi.org/10.1/example','publication_date':'2020-01-01',
        'access_level':'public','original_asset_classes':['commodity_cfd'],
        'instruments':['XAUUSD'],'original_timeframes':['D1'],'data_requirements':['OHLC'],
        'rules_summary':'A sufficiently explicit preliminary description of entry, exit, holding period and portfolio construction rules.',
        'code_available':False,'content_type':'strategy',
    }


def _eligible_review(candidate_id='IDEA-TEST0001'):
    return {
        'candidate_id':candidate_id,'decision':'eligible','reviewer':'investigator',
        'reason_code':'SOURCE_AND_RULES_VERIFIED',
        'decision_reason':'La fuente primaria y el mecanismo permiten formular una hipótesis falsable sin afirmar rentabilidad.',
        'primary_source_url':'https://doi.org/10.1/example',
        'primary_source_title':'A documented daily trend rule',
        'primary_source_authors':['A. Researcher','B. Researcher'],
        'source_rule_id':'daily-trend-rule',
        'evidence_summary':'El trabajo documenta una regla tendencial y separa el periodo de formación del periodo de tenencia.',
        'mechanism':'La persistencia de precios puede aparecer cuando participantes lentos incorporan información de forma gradual.',
        'original_market':'Futuros de materias primas','original_vehicle':'Futuros continuos',
        'original_instruments':['GC','CL'],'original_timeframes':['D1'],
        'original_rules':['Calcular la señal solo con cierres completados.','Entrar en la sesión posterior a la señal.'],
        'implementation_type':'adaptation','target_symbol':'XAUUSD','target_timeframe':'D1',
        'adaptation_notes':'Se prueba el mecanismo en un CFD individual y se modelan sus costos y rollover propios.',
        'adaptation_dimensions':['instrument','vehicle','costs'],
        'ambiguities':['La fuente no fija el tratamiento de festivos para el CFD.'],
        'data_requirements':['OHLC D1 con sesiones verificadas.'],
        'cost_assumptions':['Spread, slippage, comisión y swap del contrato XAUUSD.'],
        'limitations':['La evidencia original usa una cartera de futuros y no demuestra resultados en XAUUSD CFD.'],
    }


def _catalog_root(tmp_path,instrument):
    (tmp_path/'config').mkdir()
    (tmp_path/'config/instruments.json').write_text(json.dumps({'XAUUSD':instrument}))
    (tmp_path/'config/hypotheses.json').write_text(json.dumps({'version':1,'hypotheses':[{'id':'006','slug':'legacy','status':'discarded_is'}]}))
    (tmp_path/'docs/hypotheses').mkdir(parents=True)
    (tmp_path/'docs/hypotheses/_registry.md').write_text('# Registro\n\n| # | slug | fecha | fuente/autor | activo/timeframe | estado |\n|---|---|---|---|---|---|\n')


def test_catalog_review_requires_complete_evidence(tmp_path,instrument):
    _catalog_root(tmp_path,instrument)
    record,_=add_candidate(_catalog_candidate(),tmp_path)
    review=_eligible_review(record['candidate_id']);review.pop('limitations')
    with pytest.raises(ValueError,match='limitations'):
        review_candidate(record['candidate_id'],review,tmp_path)
    stored=read_json(tmp_path/'state/catalog'/f"{record['candidate_id']}.json")
    assert stored['status']=='captured' and 'review' not in stored


def test_catalog_review_and_promotion_are_controlled_and_idempotent(tmp_path,instrument):
    _catalog_root(tmp_path,instrument)
    record,_=add_candidate(_catalog_candidate(),tmp_path)
    reviewed,_=review_candidate(record['candidate_id'],_eligible_review(record['candidate_id']),tmp_path)
    assert reviewed['status']=='eligible'
    hypothesis,_=promote_candidate(record['candidate_id'],tmp_path)
    repeated,_=promote_candidate(record['candidate_id'],tmp_path)
    payload=read_json(tmp_path/'config/hypotheses.json')
    registry=Registry(tmp_path/'state/research.sqlite3')
    try: tasks=registry.tasks()
    finally: registry.close()
    assert hypothesis['id']=='007' and repeated['id']=='007'
    assert hypothesis['source_rule_id']=='daily-trend-rule'
    assert hypothesis['adaptation_dimensions']==['costs','instrument','vehicle']
    assert sum(row.get('candidate_id')==record['candidate_id'] for row in payload['hypotheses'])==1
    assert (tmp_path/'docs/hypotheses'/f"{hypothesis['slug']}.md").exists()
    assert sum(task['task_id']=='protocol:007' for task in tasks)==1
    assert next(task for task in tasks if task['task_id'].startswith('catalog:'))['status']=='completed'


def test_catalog_duplicate_evidence_and_noneligible_are_blocked(tmp_path,instrument):
    _catalog_root(tmp_path,instrument)
    first,_=add_candidate(_catalog_candidate(),tmp_path)
    review_candidate(first['candidate_id'],_eligible_review(first['candidate_id']),tmp_path)
    promote_candidate(first['candidate_id'],tmp_path)
    second_candidate=_catalog_candidate();second_candidate['candidate_id']='IDEA-TEST0002';second_candidate['name']='Same mechanism with another label'
    second,_=add_candidate(second_candidate,tmp_path)
    review_candidate(second['candidate_id'],_eligible_review(second['candidate_id']),tmp_path)
    with pytest.raises(ValueError,match='ya originó'):
        promote_candidate(second['candidate_id'],tmp_path)
    third_candidate=_catalog_candidate();third_candidate['candidate_id']='IDEA-TEST0003';third_candidate['name']='Blocked candidate'
    third,_=add_candidate(third_candidate,tmp_path)
    review_candidate(third['candidate_id'],{
        'decision':'needs_data','reviewer':'investigator','reason_code':'MISSING_SESSION_DATA',
        'decision_reason':'Faltan datos de sesión suficientes para reproducir las reglas.'
    },tmp_path)
    with pytest.raises(ValueError,match='eligible'):
        promote_candidate(third['candidate_id'],tmp_path)


def test_catalog_rejects_path_ids_and_undeclared_adaptation(tmp_path,instrument):
    _catalog_root(tmp_path,instrument)
    with pytest.raises(ValueError,match='candidate_id'):
        review_candidate('../config/hypotheses',{},tmp_path)
    record,_=add_candidate(_catalog_candidate(),tmp_path)
    review=_eligible_review(record['candidate_id'])
    review['original_timeframes']=['H4']
    with pytest.raises(ValueError,match='frecuencia'):
        review_candidate(record['candidate_id'],review,tmp_path)
