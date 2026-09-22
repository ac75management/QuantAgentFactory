import html
from pathlib import Path
import pandas as pd
from .io import write_json
from .metrics import monthly_returns


def table(rows):
    if not rows:
        return '<p class="muted">No ejecutado / no disponible.</p>'
    keys = list(rows[0])
    return '<div class="scroll"><table><thead><tr>' + ''.join('<th>'+html.escape(str(k))+'</th>' for k in keys) + '</tr></thead><tbody>' + ''.join('<tr>'+''.join('<td>'+html.escape(str(row.get(k, "—")))+'</td>' for k in keys)+'</tr>' for row in rows)+'</tbody></table></div>'


def chart(curve, initial, trades=None):
    if not curve:
        return '<p>Sin curva: ejecucion bloqueada.</p>'
    values = [initial]+[r["equity"] for r in curve]
    stride = max(1, len(values)//900)
    indices = list(range(0,len(values),stride))
    if indices[-1] != len(values)-1:
        indices.append(len(values)-1)
    low, high = min(values), max(values)
    span = max(1e-9, high-low)
    def x_of(i): return 40+900*i/max(1,len(values)-1)
    def y_of(v): return 230-190*(v-low)/span
    peak, running = [], values[0]
    for v in values:
        running = max(running, v)
        peak.append(running)
    equity_points = ' '.join(f'{x_of(i):.1f},{y_of(values[i]):.1f}' for i in indices)
    peak_points_rev = ' '.join(f'{x_of(i):.1f},{y_of(peak[i]):.1f}' for i in reversed(indices))
    gridlines = ''.join(
        f'<line x1="40" y1="{230-190*f:.1f}" x2="940" y2="{230-190*f:.1f}" stroke="#dbe3ed" stroke-width="1"/>'
        f'<text x="945" y="{230-190*f+4:.1f}" font-size="10" fill="#536174">{low+span*f:,.0f}</text>'
        for f in (0,0.25,0.5,0.75,1.0)
    )
    markers = ''
    if trades:
        for t in trades:
            i = t.get('exit_bar')
            if i is None or i+1>=len(values):continue
            color = '#16a34a' if t.get('net_pnl',0)>0 else '#dc2626'
            markers += f'<circle cx="{x_of(i+1):.1f}" cy="{y_of(values[i+1]):.1f}" r="2.2" fill="{color}"/>'
    start, end = html.escape(curve[0]["time"][:10]), html.escape(curve[-1]["time"][:10])
    return (f'<svg viewBox="0 0 1000 280" role="img" aria-label="Equity y drawdown por barra">{gridlines}'
            f'<polygon points="{equity_points} {peak_points_rev}" fill="#dc2626" fill-opacity="0.12" stroke="none"/>'
            f'<text x="40" y="20">Equity {low:,.0f} a {high:,.0f} · area roja = drawdown desde el pico</text>'
            f'<polyline fill="none" stroke="#0891b2" stroke-width="2" points="{equity_points}"/>{markers}'
            f'<text x="40" y="265">{start}</text><text x="840" y="265">{end}</text></svg>')


def gates_table(gates):
    if not gates:
        return '<p class="muted">No ejecutado / no disponible.</p>'
    rows = ''.join(
        '<tr><td>'+html.escape(str(g.get('gate','—')))+'</td><td><span class="badge badge-'
        +('pass' if g.get('status')=='PASS' else 'fail')+'">'+html.escape(str(g.get('status','—')))
        +'</span></td><td>'+html.escape(str(g.get('observed','—')))+'</td><td>'+html.escape(str(g.get('threshold','—')))+'</td></tr>'
        for g in gates
    )
    return f'<div class="scroll"><table><thead><tr><th>Puerta</th><th>Estado</th><th>Observado</th><th>Umbral</th></tr></thead><tbody>{rows}</tbody></table></div>'


def kv_table(d):
    return table([{"campo": k, "valor": v} for k, v in (d or {}).items()])


STYLE = 'body{font:16px system-ui;margin:0;background:#eef2f6;color:#172033}main{max-width:1120px;margin:auto;padding:28px}h1{font-size:30px}h2{margin-top:32px}.box{background:white;padding:22px;border-radius:12px;margin:16px 0}.muted{color:#536174}.flag{background:#fff4d6;padding:14px;border-left:4px solid #d19000}table{border-collapse:collapse;width:100%;font-size:13px}td,th{padding:9px;border-bottom:1px solid #dbe3ed;text-align:left;vertical-align:top}.scroll{overflow:auto}svg{width:100%}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#075985}.badge{color:white;padding:2px 9px;border-radius:10px;font-size:12px;font-weight:600;white-space:nowrap}.badge-pass{background:#16a34a}.badge-fail{background:#dc2626}'


def render_run(folder, record, result=None):
    folder = Path(folder); folder.mkdir(parents=True,exist_ok=True)
    write_json(folder/'result.json',record)
    metrics = record.get("metrics", {})
    spec = record["spec"]
    limits = record.get("reserves", [])
    diag = record.get("diagnostics", {})
    partition = record.get('provenance',{}).get('partition','IS')
    if result:
        pd.DataFrame(result["trades"]).to_csv(folder/'trades.csv',index=False)
        pd.DataFrame(result["equity"]).to_csv(folder/'equity.csv',index=False)
        write_json(folder/'monthly.json',monthly_returns(result))
    title = f'{spec["symbol"]} · {spec["timeframe"]} · {spec["family"]}'
    body = f'<h1>{html.escape(title)}</h1><p>Run {html.escape(record["run_id"])} · {html.escape(record["created_at"])}</p><div class="flag"><b>{html.escape(record["decision"])}</b> — Investigación {html.escape(partition)}. No es aprobación para operar.</div>'
    body += '<h2>Qué se investigó</h2><p>'+html.escape(spec['rationale'])+'</p>'+kv_table(spec['parameters'])
    body += '<h2>Limitaciones y costos</h2>'+table([{"reserva":x} for x in limits])
    body += '<h2>Calidad de datos</h2>'+table(record.get('quality',{}).get('checks',[]))
    body += '<h2>Resultados netos</h2>'+kv_table(metrics)
    body += chart(result['equity'],result['initial_equity'],result.get('trades')) if result else ''
    body += '<h2>Puertas y decisión</h2>'+gates_table(record.get('gates',[]))
    body += '<h2>Ventanas temporales, parámetros fijos</h2>'+table(diag.get('fixed_parameter_temporal_folds',[]))
    body += '<h2>Costos x2</h2>'+table([diag['cost_stress_2x']] if 'cost_stress_2x' in diag else [])
    body += '<h2>Sensibilidad conjunta SL/TP</h2>'+table(diag.get('joint_stop_target_sensitivity',[]))
    body += '<h2>Incertidumbre / selección</h2>'+kv_table(diag.get('bootstrap',{}))
    body += '<h2>Comparador</h2><p>No operar: retorno nominal cero, exposición cero. Es un piso económico, no un benchmark equiparado por riesgo. B&amp;H no calculado: requiere dividendos, margen y financiación histórica comparables.</p>'
    reserve_state = 'Reserva OOS evaluada una vez con contrato congelado.' if partition=='OOS' else 'Reserva OOS no abierta en esta ejecución.'
    body += '<h2>Fases pendientes</h2><p>'+reserve_state+' Permutación causal no ejecutada. No se presenta segmentación temporal como optimización walk-forward. Equity marcada al cierre de barra: el drawdown intrabar puede ser mayor. Dividendos y costos históricos variables pendientes de integración.</p>'
    body += '<h2>Reproducibilidad</h2>'+kv_table(record.get('provenance',{}))+'<p><a href="result.json">Resultado estructurado</a>'
    if result:
        body += ' · <a href="trades.csv">Operaciones</a> · <a href="equity.csv">Equity por barra</a> · <a href="monthly.json">Meses</a>'
    body += '</p>'
    (folder/'report.html').write_text(f'<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>{STYLE}</style><main>{body}</main></html>',encoding='utf-8')
    lines=[f'# {title}', '', f'Run: {record["run_id"]}', f'Decisión: **{record["decision"]}**', '', f'Investigación {partition}; no aprobación operativa.', '', '## Reservas']+['- '+x for x in limits]+['','## Métricas']+[f'- {k}: {v}' for k,v in metrics.items()]+['','Ver report.html y result.json para evidencia completa.']
    (folder/'report.md').write_text('\n'.join(lines),encoding='utf-8')


def render_daily(folder, summary):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    write_json(folder/'summary.json',summary)
    rows=[]
    for r in summary['runs']:
        rows.append({k:r.get(k) for k in ('run_id','symbol','timeframe','family','decision','net_pnl','profit_factor','max_drawdown_fraction')})
    body=f'<h1>Ejecución diaria de estrategias registradas · {summary["day"]}</h1><div class="flag">Solo investigación IS · reserva final cerrada · sin órdenes al bróker</div><p>{summary["executed"]} ejecuciones nuevas. {summary["duplicates_skipped"]} ya calculadas. Presupuesto {summary["budget"]}.</p>'
    body+='<h2>Resultados</h2>'+table(rows)+'<h2>Reportes individuales</h2><ul>'
    for r in summary['runs']:
        body+=f'<li><a href="../../runs/{r["run_id"]}/report.html">{html.escape(r["symbol"]+" "+r["timeframe"]+" "+r["family"])} — {html.escape(r["decision"])}</a></li>'
    body+='</ul><h2>Combinaciones pendientes</h2>'+table(summary['unavailable'])+'<p>Los resultados son escenarios con costos actuales. No se obliga a encontrar una estrategia ganadora. Un día sin datos o candidatos nuevos no repite ensayos idénticos.</p>'
    (folder/'report.html').write_text(f'<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ejecución diaria</title><style>{STYLE}</style><main>{body}</main></html>',encoding='utf-8')
