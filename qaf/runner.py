from datetime import datetime
from zoneinfo import ZoneInfo
import traceback
from pathlib import Path
from .io import ROOT, read_json, write_json, digest, canonical, code_hash, load_registered_hypothesis_ids
from .contracts import validate_spec, validate_instrument
from .data import load_is, inspect_frame
from .engine import simulate
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
    provenance={'dataset':data_info,'code_sha256':code_hash(),'spec_sha256':digest(spec),'cost_sha256':digest(c),'policy_sha256':digest(policy),'seed':policy['seed'],'partition':'IS','environment':'requirements-lock.txt','ledger_equation':'net = gross + financing + dividends - spread - slippage - commission'}
    record={'run_id':run_id,'created_at':created,'spec':spec,'cost_scenario':c,'policy':policy,'quality':quality,'reserves':reserves,'provenance':provenance,'decision':'BLOCKED_DATA','gates':[]}
    result=None
    if quality['status']!='FAIL':
        result=simulate(df,spec,c)
        metrics=summarize(result)
        diagnostics=diagnose(df,spec,c,result,policy)
        decision,gates=screening_gates(metrics,diagnostics,quality,reserves,policy)
        record.update(metrics=metrics,diagnostics=diagnostics,decision=decision,gates=gates,skipped=result['skipped'])
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
                except FileNotFoundError as error:
                    unavailable.append({'symbol':symbol,'timeframe':tf,'reason':str(error)})
        registered_hypotheses=load_registered_hypothesis_ids(root)
        custom=[]
        for path in sorted((root/'config/strategies').glob('*.json')):
            try:
                spec=validate_spec(read_json(path))
                if spec["hypothesis_id"].startswith("UNREGISTERED-"):
                    raise ValueError("No se permite registrar una estrategia sin hipótesis del registro")
                if spec["hypothesis_id"] not in registered_hypotheses:
                    raise ValueError(f"hypothesis_id {spec['hypothesis_id']!r} no existe en docs/hypotheses/_registry.md")
            except (ValueError,TypeError,KeyError) as error:
                # Un contrato invalido no debe tumbar el lote completo: se aisla y el resto sigue.
                unavailable.append({'symbol':'—','timeframe':'—','reason':f'INVALID_SPEC {path.name}: {error}'})
                continue
            key=(spec['symbol'],spec['timeframe'])
            if key in datasets:
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
            print(f'RUN {run_id} {spec["symbol"]}/{spec["timeframe"]} {spec["family"]}',flush=True)
            folder=report_root/'runs'/run_id
            try:
                record,folder=execute(spec,df,info,c,policy,run_id,now.isoformat(),report_root)
                registry.finish(run_id,record['decision'],folder/'result.json')
                row={'run_id':run_id,'symbol':spec['symbol'],'timeframe':spec['timeframe'],'family':spec['family'],'decision':record['decision'],**record.get('metrics',{})}
            except Exception as error:
                record={'run_id':run_id,'created_at':now.isoformat(),'spec':spec,'decision':'TECHNICAL_ERROR','reserves':[str(error)],'provenance':{'dataset':info,'code_sha256':code}}
                render_run(folder,record)
                (folder/'error.txt').write_text(traceback.format_exc(),encoding='utf-8')
                registry.finish(run_id,'TECHNICAL_ERROR',folder/'result.json',str(error))
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
