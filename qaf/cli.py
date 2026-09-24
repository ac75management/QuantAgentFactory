import argparse
import json
from .io import ROOT,read_json,digest,write_json,load_registered_hypothesis_ids
from .runner import run_daily
from .contracts import validate_spec


def main():
    parser=argparse.ArgumentParser(description='QuantAgentFactory: investigación offline reproducible')
    sub=parser.add_subparsers(dest='command',required=True)
    run=sub.add_parser('run',help='Ejecutar estrategias registradas explícitamente')
    run.add_argument('--limit',type=int)
    sub.add_parser('status',help='Última ejecución y bloqueos')
    check=sub.add_parser('check-spec',help='Validar contrato de estrategia')
    check.add_argument('path')
    add=sub.add_parser('register',help='Registrar una estrategia del usuario en la cola')
    add.add_argument('path')
    freeze=sub.add_parser('freeze',help='Congelar un run elegible sin abrir OOS')
    freeze.add_argument('run_id')
    validate=sub.add_parser('validate',help='Evaluar una reserva con contrato congelado')
    validate.add_argument('freeze_id')
    dashboard=sub.add_parser('dashboard',help='Abrir el Centro de Control local')
    dashboard.add_argument('--port',type=int,default=8765)
    dashboard.add_argument('--open',action='store_true',help='Abrir el navegador automáticamente')
    dashboard.add_argument('--snapshot',action='store_true',help='Generar HTML sin iniciar servidor')
    catalog_add=sub.add_parser('catalog-add',help='Agregar una idea al catálogo y a la cola de investigación')
    catalog_add.add_argument('path')
    sub.add_parser('catalog-list',help='Listar ideas catalogadas y su triaje')
    catalog_review=sub.add_parser('catalog-review',help='Registrar la revisión de evidencia de una idea')
    catalog_review.add_argument('candidate_id')
    catalog_review.add_argument('path',help='JSON con la revisión de evidencia')
    catalog_promote=sub.add_parser('catalog-promote',help='Crear una hipótesis desde una idea elegible')
    catalog_promote.add_argument('candidate_id')
    catalog_ack=sub.add_parser('catalog-ack-refresh',help='Reconocer un cambio de metadatos ya revisado')
    catalog_ack.add_argument('candidate_id')
    catalog_ack.add_argument('metadata_sha256')
    source_sync=sub.add_parser('source-sync',help='Extraer periódicamente metadatos y encolar candidatos nuevos')
    source_sync.add_argument('--provider',action='append',dest='providers',help='ID de proveedor; se puede repetir')
    source_sync.add_argument('--limit',type=int,default=20,help='Máximo de acciones nuevas por proveedor (1-200)')
    source_sync.add_argument('--dry-run',action='store_true',help='Consultar sin escribir catálogo, tareas, reservas ni cursores')
    trials=sub.add_parser('count-trials',help='Contar ensayos registrados en el laboratorio')
    trials.add_argument('--hypothesis')
    trials.add_argument('--family')
    args=parser.parse_args()
    if args.command=='run':
        summary,folder=run_daily(limit=args.limit)
        print(json.dumps({'executed':summary['executed'],'status':summary['status'],'report':str(folder/'report.html')},ensure_ascii=False))
        return 2 if any(r['decision']=='TECHNICAL_ERROR' for r in summary['runs']) else 0
    if args.command=='count-trials':
        from .experiment_registry import count_trials
        print(json.dumps(count_trials(ROOT, args.hypothesis, args.family), ensure_ascii=False, indent=2)); return 0
    if args.command=='status':
        path=ROOT/'reports/factory/latest.json'
        print(json.dumps(read_json(path) if path.exists() else {'status':'NOT_RUN'},indent=2,ensure_ascii=False));return 0
    if args.command in ('check-spec','register'):
        spec=validate_spec(read_json(args.path))
        instruments=read_json(ROOT/'config/instruments.json')
        if spec['symbol'] not in instruments:raise ValueError('Registrar primero el instrumento')
        if spec['hypothesis_id'] not in load_registered_hypothesis_ids(ROOT):
            raise ValueError(f"hypothesis_id {spec['hypothesis_id']!r} no existe en config/hypotheses.json")
        if args.command=='register':
            path=ROOT/'config/strategies'/f'{digest(spec)[:24]}.json'
            write_json(path,spec);print(f'Registrada: {path}')
        else:print('SPEC_OK')
        return 0
    if args.command=='freeze':
        from .holdout import freeze
        print(freeze(args.run_id));return 0
    if args.command=='validate':
        from .holdout import validate_final
        record,folder=validate_final(args.freeze_id)
        print(json.dumps({'decision':record['decision'],'report':str(folder/'report.html')}));return 0
    if args.command=='dashboard':
        from .dashboard import serve,write_snapshot
        if args.snapshot:
            print(write_snapshot());return 0
        serve(port=args.port,open_browser=args.open);return 0
    if args.command=='catalog-add':
        from .catalog import add_candidate
        record,path=add_candidate(read_json(args.path))
        possible_duplicates=record['assessment'].get('possible_duplicates',[])
        print(json.dumps({'candidate_id':record['candidate_id'],'score':record['assessment']['score'],'verdict':record['assessment']['verdict'],'possible_duplicates':possible_duplicates,'warning':'Revisa los posibles duplicados antes de investigar.' if possible_duplicates else None,'path':str(path)},ensure_ascii=False));return 0
    if args.command=='catalog-list':
        from .catalog import list_candidates
        rows=[{'candidate_id':r.get('candidate_id'),'name':r.get('name'),'source':r.get('source_name'),'status':r.get('status'),'hypothesis_id':r.get('hypothesis_id'),'score':r.get('assessment',{}).get('score'),'verdict':r.get('assessment',{}).get('verdict')} for r in list_candidates()]
        print(json.dumps(rows,indent=2,ensure_ascii=False));return 0
    if args.command=='catalog-review':
        from .catalog import review_candidate
        record,path=review_candidate(args.candidate_id,read_json(args.path))
        print(json.dumps({'candidate_id':record['candidate_id'],'status':record['status'],'path':str(path)},ensure_ascii=False));return 0
    if args.command=='catalog-promote':
        from .catalog import promote_candidate
        hypothesis,path=promote_candidate(args.candidate_id)
        print(json.dumps({'candidate_id':args.candidate_id,'hypothesis_id':hypothesis['id'],'status':hypothesis['status'],'path':str(path)},ensure_ascii=False));return 0
    if args.command=='catalog-ack-refresh':
        from .catalog import acknowledge_refresh
        record,path=acknowledge_refresh(args.candidate_id,args.metadata_sha256)
        print(json.dumps({'candidate_id':record['candidate_id'],'acknowledged':args.metadata_sha256,'path':str(path)},ensure_ascii=False));return 0
    if args.command=='source-sync':
        from .source_sync import sync_sources
        if args.limit < 1 or args.limit > 200:raise ValueError('--limit debe estar entre 1 y 200')
        result=sync_sources(provider_ids=args.providers,limit=args.limit,dry_run=args.dry_run)
        print(json.dumps(result,indent=2,ensure_ascii=False));return 1 if result['failed'] else 0


if __name__=='__main__':
    raise SystemExit(main())
