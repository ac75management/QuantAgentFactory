from datetime import datetime
from zoneinfo import ZoneInfo
import traceback
from pathlib import Path
import json
from .io import ROOT, read_json, write_json, digest, canonical, code_hash, load_registered_hypothesis_ids, load_hypotheses
from .contracts import validate_spec, validate_instrument
from .data import load_is, inspect_frame
from .engine import simulate
from .baseline import simulate_baseline
from .metrics import summarize
from .validation import diagnose, screening_gates
from .reporting import render_run, render_daily
from .registry import Registry


def execute(spec,df,data_info,c,policy,run_id,created,output_root):
    validate_spec(spec);validate_instrument(c)
    quality=inspect_frame(df,spec['timeframe'],{'symbol':spec['symbol'],**c})
    reserves=list(c.get('reserves',[]))
    if not c.get('costs_verified'):
        reserves.append('Costos exploratorios no habilitados para aprobación final')
    reserves.append('Motor de costos constantes: escenario vigente aplicado al IS histórico; no habilita validación final')
    if data_info.get('partition_integrity',{}).get('status')!='SEALED':
        reserves.append('Partición IS/OOS sin sellar (python -m qaf.partition seal): integridad de OOS no verificable; no habilita validación final')
    provenance={'dataset':data_info,'code_sha256':code_hash(),'spec_sha256':digest(spec),'cost_sha256':digest(c),'policy_sha256':digest(policy),'seed':policy['seed'],'partition':'IS','environment':'requirements-lock.txt','ledger_equation':'net = gross + financing + dividends - spread - slippage - commission'}
    record={'run_id':run_id,'created_at':created,'spec':spec,'cost_scenario':c,'policy':policy,'quality':quality,'reserves':reserves,'provenance':provenance,'decision':'BLOCKED_DATA','gates':[]}
    result=None
    if quality['status']!='FAIL':
        result=simulate(df,spec,c)
        metrics=summarize(result)
        diagnostics=diagnose(df,spec,c,result,policy)
        # Comprar y mantener del mismo simbolo/timeframe/ventana IS/costos y el mismo
        # capital invertido 1x (CLAUDE.md regla 19; exposicion documentada en qaf/baseline.py).
        baseline_result=simulate_baseline(df,c,direction=1,initial_equity=spec.get('initial_equity',100000))
        baseline_metrics=summarize(baseline_result)
        decision,gates=screening_gates(metrics,diagnostics,quality,reserves,policy,baseline_metrics)
        record.update(metrics=metrics,diagnostics=diagnostics,decision=decision,gates=gates,skipped=result['skipped'],baseline={**baseline_metrics,'sizing':baseline_result['sizing']})
    folder=Path(output_root)/'runs'/run_id
    render_run(folder,record,result)
    return record,folder


def run_daily(root=ROOT,limit=None,day=None):
    root=Path(root)
    policy=read_json(root/'config/runner.json')
    universe=read_json(root/'config/instruments.json')
    budget=policy['daily_max_trials'] if limit is None else min(limit,policy['daily_max_trials'])
    if budget<1:raise ValueError('Presupuesto invalido')
    now=datetime.now(ZoneInfo('America/Guayaquil'))
    day=day or now.date().isoformat()
    report_root=root/'reports/factory'
    registry=Registry(root/'state/research.sqlite3')
    unavailable=[];datasets={}
    try:
        for symbol,c in universe.items():
            if c.get('status')!='research':
                unavailable.append({'symbol':symbol,'timeframe':'—','reason':c.get('blocked_reason','Pendiente de contrato/datos')});continue
            for tf in c['timeframes']:
                try:
                    df,info=load_is(symbol,tf,root)
                    datasets[(symbol,tf)]=(df,info)
                except (FileNotFoundError, ValueError, KeyError) as error:
                    unavailable.append({'symbol':symbol,'timeframe':tf,'reason':str(error)})
        registered_hypotheses=load_registered_hypothesis_ids(root)
        hypothesis_catalog=load_hypotheses(root)
        custom=[]
        for path in sorted((root/'config/strategies').glob('*.json')):
            try:
                spec=validate_spec(read_json(path))
                if spec["hypothesis_id"].startswith("UNREGISTERED-"):
                    raise ValueError("No se permite registrar una estrategia sin hipótesis del registro")
                if spec["hypothesis_id"] not in registered_hypotheses:
                    raise ValueError(f"hypothesis_id {spec['hypothesis_id']!r} no existe en config/hypotheses.json")
            except (ValueError,TypeError,KeyError) as error:
                # Un contrato invalido no debe tumbar el lote completo: se aisla y el resto sigue.
                unavailable.append({'symbol':'—','timeframe':'—','reason':f'INVALID_SPEC {path.name}: {error}'})
                continue
            key=(spec['symbol'],spec['timeframe'])
            hypothesis=(hypothesis_catalog or {}).get(spec['hypothesis_id']) if hypothesis_catalog is not None else None
            if hypothesis is not None and hypothesis.get('status') not in {'pending','ready'}:
                unavailable.append({'symbol':spec['symbol'],'timeframe':spec['timeframe'],'reason':f"HIPOTESIS_{str(hypothesis.get('status')).upper()}: no se repite automáticamente"})
            elif key in datasets:
                custom.append((spec,universe[spec['symbol']]))
            else:
                unavailable.append({'symbol':spec['symbol'],'timeframe':spec['timeframe'],'reason':'Estrategia registrada pendiente de datos/contrato'})
        # Solo se ejecutan estrategias registradas explícitamente. No hay
        # generación automática de familias ni variantes.
        jobs=custom
        runs=[];duplicates=0;state='COMPLETED'
        code=code_hash()
        for spec,c in jobs:
            if len(runs)>=budget:break
            df,info=datasets[(spec['symbol'],spec['timeframe'])]
            run_id=digest({'spec':spec,'data':info,'costs':c,'policy':policy,'code':code})[:24]
            reserved=registry.reserve(run_id,day,policy['campaign_id'],canonical(spec),policy['daily_max_trials'],policy['campaign_max_trials'])
            if reserved=='DUPLICATE':duplicates+=1;continue
            if reserved=='BUDGET':state='BUDGET_REACHED';break
            task_id=f'is:{run_id}'
            registry.start_task(task_id,run_id,spec['hypothesis_id'],'is_backtest','engine',json.dumps([str((root/'config/strategies').relative_to(root))],ensure_ascii=False))
            print(f'RUN {run_id} {spec["symbol"]}/{spec["timeframe"]} {spec["family"]}',flush=True)
            folder=report_root/'runs'/run_id
            try:
                record,folder=execute(spec,df,info,c,policy,run_id,now.isoformat(),report_root)
                registry.finish(run_id,record['decision'],folder/'result.json')
                task_status='completed' if record['decision'] not in {'BLOCKED_DATA','TECHNICAL_ERROR'} else ('blocked' if record['decision']=='BLOCKED_DATA' else 'failed')
                registry.finish_task(task_id,task_status,record['decision'],None,json.dumps([str((folder/'result.json').relative_to(root)),str((folder/'report.html').relative_to(root))],ensure_ascii=False))
                row={'run_id':run_id,'symbol':spec['symbol'],'timeframe':spec['timeframe'],'family':spec['family'],'decision':record['decision'],**record.get('metrics',{})}
            except Exception as error:
                record={'run_id':run_id,'created_at':now.isoformat(),'spec':spec,'decision':'TECHNICAL_ERROR','reserves':[str(error)],'provenance':{'dataset':info,'code_sha256':code}}
                render_run(folder,record)
                (folder/'error.txt').write_text(traceback.format_exc(),encoding='utf-8')
                try:
                    registry.finish(run_id,'TECHNICAL_ERROR',folder/'result.json',str(error))
                except RuntimeError as lease_error:
                    # Un worker recuperado no puede modificar el registro de su reemplazo.
                    record['reserves'].append(str(lease_error))
                registry.finish_task(task_id,'failed','TECHNICAL_ERROR',str(error),json.dumps([str((folder/'error.txt').relative_to(root))],ensure_ascii=False))
                row={'run_id':run_id,'symbol':spec['symbol'],'timeframe':spec['timeframe'],'family':spec['family'],'decision':'TECHNICAL_ERROR'}
            runs.append(row)
            print(f'  {row["decision"]}',flush=True)
        summary={'day':day,'created_at':now.isoformat(),'status':state,'executed':len(runs),'duplicates_skipped':duplicates,'budget':budget,'runs':runs,'unavailable':unavailable,'campaign':policy['campaign_id'],'all_registered_trials':len(registry.rows())}
        # Preserve each invocation; never overwrite the previous daily run on a retry.
        folder=report_root/'daily'/f'{day}-{now.strftime("%H%M%S%f")}'
        render_daily(folder,summary)
        write_json(folder/"registry_snapshot.json",registry.rows())
        write_json(report_root/'latest.json',{'report':str((folder/'report.html').relative_to(root)),**summary})
        return summary,folder
    finally:registry.close()
