import html
import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from uuid import uuid4

from .io import ROOT, read_json
from .registry import Registry
from .catalog import list_candidates

STYLE=""":root{color-scheme:dark;--bg:#0a1020;--panel:#121b30;--line:#263654;--muted:#9dafca;--text:#edf4ff}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at top,#162545,var(--bg) 46%);color:var(--text);font:15px system-ui,sans-serif}main{max-width:1320px;margin:auto;padding:28px}.top{display:flex;justify-content:space-between;gap:20px;align-items:end;flex-wrap:wrap}h1{font-size:30px;margin:0}h2{margin:32px 0 14px}.muted{color:var(--muted)}.kpis,.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}.card{background:rgba(18,27,48,.94);border:1px solid var(--line);border-radius:14px;padding:17px;box-shadow:0 12px 28px #0004}.kpi b{display:block;font-size:28px;margin-top:6px}.badge{display:inline-block;padding:4px 9px;border-radius:999px;font-size:12px;font-weight:700;background:#34435d}.completed,.pass,.eligible,.promoted{background:#164e3b;color:#7ef0b7}.failed,.discarded_is,.rejected_by_user,.rejected{background:#632936;color:#ffb0ba}.blocked,.running,.blocked_architecture,.needs_data{background:#654a16;color:#ffda83}.queued,.pending,.captured,.triage{background:#194e72;color:#9ddcff}.strategy h3{margin:8px 0}.row{display:flex;justify-content:space-between;gap:12px;padding:10px 0;border-bottom:1px solid var(--line)}.row:last-child{border:0}.code{font-family:ui-monospace,monospace;font-size:12px;color:#b8cae6}.actions a{color:#91ceff;text-decoration:none;margin-right:12px}.empty{padding:20px;border:1px dashed var(--line);border-radius:12px;color:var(--muted)}button{border:1px solid var(--line);background:#28669b;color:#fff;padding:10px 14px;border-radius:9px;cursor:pointer;font-weight:700}label{display:block;margin:12px 0 5px;font-weight:700}input,select,textarea{width:100%;padding:10px;border:1px solid var(--line);border-radius:8px;background:#0c1528;color:var(--text)}textarea{min-height:90px;resize:vertical}.notice{background:#143c32;border:1px solid #28715c;padding:12px;border-radius:10px;margin:15px 0}.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}.step{padding:12px;border-left:3px solid #457caf;background:#0c1528;border-radius:6px}@media(max-width:650px){main{padding:18px}.row{display:block}}"""

def create_intake(root,form):
    """Persist a human request as queued work; it is not yet a tradable specification."""
    root=Path(root)
    idea=(form.get('idea') or '').strip()
    symbol=(form.get('symbol') or '').strip().upper()
    timeframe=(form.get('timeframe') or '').strip().upper()
    source=(form.get('source') or '').strip()
    if len(idea)<20 or len(idea)>4000:raise ValueError('Describe la idea con al menos 20 caracteres (máximo 4000).')
    instruments=read_json(root/'config/instruments.json')
    if symbol not in instruments:raise ValueError('Instrumento no registrado en el universo.')
    if timeframe not in instruments[symbol].get('timeframes',[]):raise ValueError('Ese marco temporal no está habilitado para el instrumento.')
    created=datetime.now(timezone.utc).isoformat();intake_id='INTAKE-'+uuid4().hex[:10].upper()
    payload={'intake_id':intake_id,'created_at':created,'status':'queued_research','symbol':symbol,'timeframe':timeframe,'idea':idea,'source':source or None}
    path=root/'state/intakes'/f'{intake_id}.json';path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
    registry=Registry(root/'state/research.sqlite3')
    try:registry.queue_task('research:'+intake_id,intake_id,'evidence_review','investigator',json.dumps([str(path.relative_to(root))],ensure_ascii=False),'Solicitud recibida; requiere investigación y contrato antes del backtest.')
    finally:registry.close()
    return intake_id

def _json(value,fallback):
    try:return json.loads(value) if isinstance(value,str) else value
    except (TypeError,json.JSONDecodeError):return fallback

def dashboard_state(root=ROOT):
    root=Path(root);registry=Registry(root/'state/research.sqlite3')
    try:trials=registry.rows();tasks=registry.tasks();events=registry.events(50)
    finally:registry.close()
    specs=[]
    for path in sorted((root/'config/strategies').glob('*.json')):
        try:spec=read_json(path);spec['_file']=path.name;specs.append(spec)
        except (OSError,ValueError,json.JSONDecodeError):continue
    latest={}
    for trial in sorted(trials,key=lambda row:(row.get('reserved_at') or '',row.get('run_id') or '')):
        spec=_json(trial.get('spec_json'),{})
        if spec.get('id'):latest[spec['id']]=trial
    hypotheses={}
    path=root/'config/hypotheses.json'
    if path.exists():
        payload=read_json(path);hypotheses={row['id']:row for row in payload.get('hypotheses',[]) if isinstance(row,dict) and row.get('id')}
    return {'specs':specs,'trials':trials,'tasks':tasks,'events':events,'latest':latest,'hypotheses':hypotheses,'candidates':list_candidates(root)}

def _outcome(trial,hypothesis):
    if not trial:return (hypothesis or {}).get('reason','Todavía no ejecutada.'),(hypothesis or {}).get('next_action','Revisar el contrato antes de ejecutar.')
    if trial.get('status')=='TECHNICAL_ERROR':return 'La ejecución falló por un error técnico.','Corregir el error y repetir el mismo contrato.'
    if trial.get('status')=='BLOCKED_DATA':return 'Los datos o su contrato bloquearon una conclusión.','Resolver Gate 0 sin modificar la estrategia.'
    try:record=read_json(trial['result_path']) if trial.get('result_path') else {}
    except (OSError,ValueError,json.JSONDecodeError):record={}
    metrics=record.get('metrics',{})
    if metrics.get('gross_pnl') is not None and metrics['gross_pnl']<=0:return 'La señal perdió antes de costos: no apareció el edge de precio.','Archivar esta regla y elegir otro mecanismo o mercado.'
    failed=[g.get('gate') for g in record.get('gates',[]) if g.get('status')=='FAIL']
    if 'friction' in failed:return 'El edge fue demasiado débil para la fricción. También falló: '+', '.join(failed)+'.','Archivar; solo una hipótesis nueva puede cambiar holding, vehículo o mecanismo.'
    if failed:return 'Fallaron las puertas: '+', '.join(failed)+'.','Archivar o formular una hipótesis nueva con evidencia independiente.'
    return 'La ejecución terminó sin una causa de descarte identificada.',(hypothesis or {}).get('next_action','Revisar el reporte completo.')

def render_dashboard(root=ROOT):
    root=Path(root);state=dashboard_state(root);esc=lambda x:html.escape(str(x if x is not None else '—'))
    active=sum(t['status']=='running' for t in state['tasks']);blocked=sum(t['status']=='blocked' for t in state['tasks']);completed=sum(t['status']=='completed' for t in state['tasks'])
    cards=[]
    for spec in state['specs']:
        trial=state['latest'].get(spec.get('id'));hyp=state['hypotheses'].get(spec.get('hypothesis_id'),{});status=hyp.get('status') or (trial or {}).get('status','queued').lower();reason,next_action=_outcome(trial,hyp);link=''
        if trial and trial.get('result_path'):
            try:rel=Path(trial['result_path']).relative_to(root).parent/'report.html';link=f'<a href="/files/{esc(rel.as_posix())}">Abrir reporte</a>'
            except ValueError:pass
        cards.append(f'<article class="card strategy"><span class="badge {esc(status)}">{esc(status.upper())}</span><h3>{esc(spec.get("id"))}</h3><p>{esc(spec.get("symbol"))} · {esc(spec.get("timeframe"))} · {esc(spec.get("family"))}</p><p class="muted">Hipótesis {esc(spec.get("hypothesis_id"))}</p><p><b>Qué ocurrió:</b> {esc(reason)}</p><p><b>Siguiente acción:</b> {esc(next_action)}</p><div class="actions">{link}</div></article>')
    task_rows=[f'<div class="row"><div><span class="badge {esc(t["status"])}">{esc(t["status"].upper())}</span> <b>{esc(t["stage"])}</b><div class="muted">Hipótesis {esc(t["hypothesis_id"])}</div></div><div>{esc(t.get("reason_code"))}<div class="code">{esc(t.get("started_at"))}</div></div></div>' for t in state['tasks'][:20]]
    event_rows=[f'<div class="row"><div><b>{esc(e["event_type"])}</b> · {esc(e["task_id"])}</div><div class="code">{esc(e["created_at"])}</div></div>' for e in state['events'][:15]]
    candidate_rows=[]
    for candidate in state['candidates']:
        assessment=candidate.get('assessment',{});blockers=assessment.get('blockers',[]);review=candidate.get('review',{});hypothesis_id=candidate.get('hypothesis_id')
        detail=review.get('decision_reason') or (blockers[0] if blockers else 'Lista para revisión de evidencia')
        link=f' · Hipótesis {esc(hypothesis_id)}' if hypothesis_id else ''
        candidate_rows.append(f'<div class="row"><div><span class="badge {esc(candidate.get("status","captured"))}">{esc(candidate.get("status","captured").upper())}</span> <b>{esc(candidate.get("name"))}</b><div class="muted">{esc(candidate.get("source_name"))} · {esc(candidate.get("candidate_id"))}{link}</div></div><div><b>Prioridad {esc(assessment.get("score",0))}/100</b><div class="muted">{esc(detail)}</div></div></div>')
    instruments_path=root/'config/instruments.json'
    instruments=read_json(instruments_path) if instruments_path.exists() else {}
    options=''.join(f'<option value="{esc(s)}">{esc(s)}</option>' for s,c in instruments.items() if c.get('status')=='research')
    return f'''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="15"><title>QuantAgentFactory · Centro de Control</title><style>{STYLE}</style><main><div class="top"><div><p class="muted">QUANT AGENT FACTORY</p><h1>Centro de Control</h1><p class="muted">Estado real · actualización cada 15 segundos</p></div><button onclick="location.reload()">Actualizar</button></div><section class="kpis"><div class="card kpi">Ideas catalogadas<b>{len(state['candidates'])}</b></div><div class="card kpi">Estrategias registradas<b>{len(state['specs'])}</b></div><div class="card kpi">Trabajando ahora<b>{active}</b></div><div class="card kpi">En cola<b>{sum(t['status']=='queued' for t in state['tasks'])}</b></div><div class="card kpi">Bloqueadas<b>{blocked}</b></div><div class="card kpi">Tareas terminadas<b>{completed}</b></div></section><h2>Crear una investigación</h2><section class="grid"><form class="card" method="post" action="/intake"><label>Idea o mecanismo</label><textarea name="idea" maxlength="4000" required placeholder="Ejemplo: ruptura del máximo de N días solo cuando el Efficiency Ratio indique una tendencia limpia..."></textarea><label>Instrumento</label><select name="symbol">{options}</select><label>Marco temporal</label><select name="timeframe"><option>H1</option><option>H4</option><option>D1</option></select><label>Fuente o autor (opcional)</label><input name="source" maxlength="300" placeholder="Libro, paper, enlace o autor"><p class="muted">Esto crea una solicitud de investigación. No inventa parámetros ni abre OOS.</p><button type="submit">Añadir a la cola</button></form><div class="card"><h3>Cómo avanza</h3><div class="steps"><div class="step"><b>1. Evidencia</b><br><span class="muted">investigator</span></div><div class="step"><b>2. Contrato</b><br><span class="muted">protocol</span></div><div class="step"><b>3. IS</b><br><span class="muted">motor QAF</span></div><div class="step"><b>4. Decisión</b><br><span class="muted">validator</span></div></div><p class="muted">“En cola” significa pendiente. “Trabajando ahora” solo aparece cuando un proceso real está ejecutándose.</p></div></section><h2>Catálogo de ideas</h2><section class="card">{''.join(candidate_rows) or '<div class="empty">Aún no hay ideas documentadas. Usa la plantilla del catálogo para cargar la primera.</div>'}</section><h2>Estrategias</h2><section class="grid">{''.join(cards) or '<div class="empty">No hay estrategias registradas.</div>'}</section><h2>Trabajo de agentes y motor</h2><section class="card">{''.join(task_rows) or '<div class="empty">No hay tareas.</div>'}</section><h2>Actividad reciente</h2><section class="card">{''.join(event_rows) or '<div class="empty">Todavía no hay eventos.</div>'}</section></main></html>'''

def write_snapshot(root=ROOT,path=None):
    root=Path(root);path=Path(path) if path else root/'reports/factory/control-center.html';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(render_dashboard(root),encoding='utf-8');return path

def serve(root=ROOT,host='127.0.0.1',port=8765,open_browser=False):
    root=Path(root).resolve()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path=urlparse(self.path).path
            if path=='/':
                body=render_dashboard(root).encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);return
            if path.startswith('/files/'):
                candidate=(root/unquote(path[7:])).resolve()
                if root not in candidate.parents or not candidate.is_file():self.send_error(404);return
                body=candidate.read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);return
            self.send_error(404)
        def do_POST(self):
            if urlparse(self.path).path!='/intake':self.send_error(404);return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if length<1 or length>10000:raise ValueError('Solicitud vacía o demasiado grande.')
                fields={k:v[0] for k,v in parse_qs(self.rfile.read(length).decode('utf-8'),keep_blank_values=True).items()}
                intake_id=create_intake(root,fields)
                body=(f'<!doctype html><meta charset="utf-8"><style>{STYLE}</style><main><div class="notice"><b>Solicitud {html.escape(intake_id)} añadida a la cola.</b><p>Ahora figura como pendiente de investigación; todavía no es una estrategia validada.</p></div><a href="/">Volver al Centro de Control</a></main>').encode()
                self.send_response(303);self.send_header('Location','/');self.send_header('Content-Length','0');self.end_headers()
            except (ValueError,KeyError,json.JSONDecodeError) as error:
                body=f'Error: {html.escape(str(error))}'.encode();self.send_response(400);self.send_header('Content-Type','text/plain; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def log_message(self,format,*args):return
    # Another dashboard may already own the preferred port. Try nearby ports
    # instead of forcing a nontechnical user to inspect Windows sockets.
    candidates=[port] if port==0 else range(port,port+20)
    server=None
    for candidate in candidates:
        try:
            server=ThreadingHTTPServer((host,candidate),Handler);break
        except PermissionError:
            continue
        except OSError as error:
            if getattr(error,'winerror',None)==10013 or getattr(error,'errno',None) in (13,98,10048):continue
            raise
    if server is None:raise RuntimeError(f'No hay un puerto disponible entre {port} y {port+19}')
    actual_port=server.server_address[1];url=f'http://{host}:{actual_port}/'
    print(f'Centro de Control: {url}',flush=True)
    if open_browser:
        import webbrowser
        webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
