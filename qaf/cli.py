import argparse
import json
from pathlib import Path
from .io import ROOT,read_json,digest,write_json
from .runner import run_daily
from .contracts import validate_spec,validate_instrument


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
    args=parser.parse_args()
    if args.command=='run':
        summary,folder=run_daily(limit=args.limit)
        print(json.dumps({'executed':summary['executed'],'status':summary['status'],'report':str(folder/'report.html')},ensure_ascii=False))
        return 2 if any(r['decision']=='TECHNICAL_ERROR' for r in summary['runs']) else 0
    if args.command=='status':
        path=ROOT/'reports/factory/latest.json'
        print(json.dumps(read_json(path) if path.exists() else {'status':'NOT_RUN'},indent=2,ensure_ascii=False));return 0
    if args.command in ('check-spec','register'):
        spec=validate_spec(read_json(args.path))
        instruments=read_json(ROOT/'config/instruments.json')
        if spec['symbol'] not in instruments:raise ValueError('Registrar primero el instrumento')
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


if __name__=='__main__':
    raise SystemExit(main())
