"""Controlador determinista de fases: no es un agente ni ejecuta nada.

Deriva solo de artefactos del repo en que fase esta cada hipotesis y a que
agente le toca actuar. Los agentes lo consultan antes de actuar
(`python -m qaf.pipeline --hypothesis <id> --as <agente>`) y se detienen si
no les toca. Un estado inconsistente frena la hipotesis hasta que Alexander
lo resuelva, en vez de dejar que cada agente interprete a su manera.

Fuentes (todas de solo lectura):
  config/hypotheses.json              estado autoritativo de la hipotesis
  docs/hypotheses/<slug>.md           salida de investigator
  docs/specs/<slug>.json + .md        salida de protocol
  config/strategies/<digest>.json     registro de engine (qaf.cli register)
  state/research.sqlite3              corridas IS (trials) y tareas en curso (tasks)
"""
import argparse
import json
import sqlite3
from pathlib import Path
from .contracts import validate_spec
from .io import ROOT, canonical, digest, load_hypotheses, read_json

ACTORS = ("investigator", "protocol", "engine", "validator", "alexander")
RUNNABLE = {"pending", "ready"}
TERMINAL = {
    "discarded_is": ("CLOSED", None, "Cerrada. Reabrir exige una hipótesis nueva registrada con justificación distinta."),
    "rejected_by_user": ("CLOSED", None, "Cerrada por decisión de Alexander."),
    "rejected_oos": ("CLOSED", None, "Rechazada en OOS. No se reoptimiza."),
    "inconclusive": ("NEEDS_DECISION", "alexander", "Muestra insuficiente: decidir si se archiva o se formula una hipótesis nueva con más datos."),
    "invalid_por_datos": ("NEEDS_DECISION", "alexander", "Datos insuficientes o no confirmados: decidir si se corrigen los datos o se archiva."),
    "blocked_architecture": ("BLOCKED", "alexander", "La familia de señal no existe en qaf: decidir si se implementa."),
    "blocked_data": ("BLOCKED", "alexander", "Faltan datos o contrato del instrumento: decidir si se consiguen."),
    "ready_for_frozen_validation": ("FROZEN_VALIDATION_BLOCKED", "validator",
                                    "Lista para ENTRAR en validación congelada, no validada. qaf/holdout.py bloquea OOS hasta cumplir docs/VALIDATION_ROADMAP.md."),
    "approved": ("APPROVED", "alexander", "Incubación demo y lote mínimo real requieren confirmación explícita (CLAUDE.md regla 15)."),
}


def _json_files(folder):
    for path in sorted(Path(folder).glob("*.json")):
        try:
            yield path, read_json(path)
        except (ValueError, OSError) as error:
            yield path, error


def _database(root):
    path = Path(root) / "state/research.sqlite3"
    if not path.exists():
        return [], []
    db = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    try:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        trials = db.execute("SELECT spec_json, status FROM trials").fetchall() if "trials" in tables else []
        tasks = db.execute("SELECT hypothesis_id, task_id, status FROM tasks").fetchall() if "tasks" in tables else []
    finally:
        db.close()
    return trials, tasks


def pipeline_state(root=ROOT):
    root = Path(root)
    catalog = load_hypotheses(root) or {}
    violations = []

    def severity(hypothesis_id):
        status = (catalog.get(hypothesis_id) or {}).get("status")
        if hypothesis_id not in catalog or status in RUNNABLE:
            return "error"
        # A closed hypothesis is frozen history: the anomaly stays visible in its row,
        # but it is not a pending warning that anyone can act on.
        return "history" if TERMINAL.get(status, (None,))[0] == "CLOSED" else "warning"

    def violation(hypothesis_id, text, level=None):
        violations.append({"severity": level or severity(hypothesis_id), "hypothesis_id": hypothesis_id, "issue": text})

    specs = {}
    for path, spec in _json_files(root / "docs/specs"):
        if not isinstance(spec, dict):
            violation(None, f"docs/specs/{path.name}: JSON ilegible", "error")
            continue
        try:
            validate_spec(spec)
        except ValueError as error:
            violation(spec.get("hypothesis_id"), f"docs/specs/{path.name}: contrato inválido ({error})")
            continue
        specs.setdefault(spec["hypothesis_id"], []).append((path, spec))
        if not path.with_suffix(".md").exists():
            violation(spec["hypothesis_id"], f"docs/specs/{path.name}: contrato sin narrativa .md de protocol")

    registered = {}
    for path, spec in _json_files(root / "config/strategies"):
        if not isinstance(spec, dict) or not spec.get("hypothesis_id"):
            violation(None, f"config/strategies/{path.name}: estrategia ilegible o sin hypothesis_id", "error")
            continue
        registered[path.stem] = spec
    delivered = {digest(spec)[:24] for rows in specs.values() for _, spec in rows}
    for stem, spec in sorted(registered.items()):
        hypothesis_id = spec["hypothesis_id"]
        if hypothesis_id not in catalog:
            violation(hypothesis_id, f"config/strategies/{stem}.json apunta a una hipótesis inexistente", "error")
        if stem not in delivered:
            violation(hypothesis_id, f"config/strategies/{stem}.json no tiene un contrato idéntico en docs/specs: protocol saltado o spec editada después de registrar")

    trials, tasks = _database(root)
    runs = {}
    for spec_json, status in trials:
        runs.setdefault(spec_json, []).append(status)
    running = {}
    for hypothesis_id, task_id, status in tasks:
        if status == "running":
            running.setdefault(hypothesis_id, []).append(task_id)

    rows = []
    for hypothesis_id, row in catalog.items():
        status = row.get("status")
        base = {"hypothesis_id": hypothesis_id, "status": status, "slug": row.get("slug")}
        if status in TERMINAL:
            stage, actor, action = TERMINAL[status]
        elif status not in RUNNABLE:
            stage, actor, action = "INCONSISTENT", "alexander", f"Estado {status!r} fuera del vocabulario (qaf/consistency.py)"
        elif any(v["hypothesis_id"] == hypothesis_id and v["severity"] == "error" for v in violations):
            stage, actor, action = "INCONSISTENT", "alexander", "Resolver las violaciones de esta hipótesis antes de que actúe cualquier agente"
        elif not row.get("slug") or not (root / "docs/hypotheses" / f"{row['slug']}.md").exists():
            stage, actor, action = "NEEDS_HYPOTHESIS_DOC", "investigator", f"Escribir docs/hypotheses/{row.get('slug')}.md"
        elif hypothesis_id in running:
            stage, actor, action = "RUNNING", None, f"Tarea en curso ({', '.join(running[hypothesis_id])}): esperar, o recuperarla si quedó caída"
        elif not specs.get(hypothesis_id):
            stage, actor, action = "NEEDS_SPEC", "protocol", f"Escribir docs/specs/{row.get('slug')}.md + .json"
        else:
            own = specs[hypothesis_id]
            pending = [path.name for path, spec in own if digest(spec)[:24] not in registered]
            results = [runs.get(canonical(spec), []) for _, spec in own]
            if pending:
                stage, actor, action = "NEEDS_REGISTRATION", "engine", "qaf.cli check-spec + register: " + ", ".join(f"docs/specs/{name}" for name in pending)
            elif any("RUNNING" in result for result in results):
                stage, actor, action = "RUNNING", None, "Corrida IS en curso: esperar, o recuperarla si quedó caída"
            elif any(not [d for d in result if d != "TECHNICAL_ERROR"] for result in results):
                failed = any("TECHNICAL_ERROR" in result for result in results)
                stage, actor, action = "NEEDS_IS_RUN", "engine", "qaf.cli run" + (" — la última corrida terminó en TECHNICAL_ERROR: revisar error.txt y corregir antes de reintentar" if failed else "")
            else:
                decisions = sorted({d for result in results for d in result if d != "TECHNICAL_ERROR"})
                stage, actor, action = "NEEDS_VALIDATOR_REVIEW", "validator", f"Clasificar {decisions} y actualizar config/hypotheses.json + espejo"
        rows.append({**base, "stage": stage, "next_actor": actor, "next_action": action,
                     "violations": [v["issue"] for v in violations if v["hypothesis_id"] == hypothesis_id]})
    return {"hypotheses": rows, "violations": violations}


def check_turn(hypothesis_id, actor, root=ROOT):
    if actor not in ACTORS:
        raise ValueError(f"Agente desconocido: {actor}")
    row = next((r for r in pipeline_state(root)["hypotheses"] if r["hypothesis_id"] == hypothesis_id), None)
    if row is None:
        return False, f"La hipótesis {hypothesis_id} no existe en config/hypotheses.json"
    if row["next_actor"] == actor:
        return True, f"{row['stage']}: {row['next_action']}"
    return False, f"{row['stage']}: le toca a {row['next_actor'] or 'nadie'} — {row['next_action']}"


def main():
    parser = argparse.ArgumentParser(description="Fase y siguiente agente permitido por hipótesis (solo lectura)")
    parser.add_argument("--hypothesis")
    parser.add_argument("--as", dest="actor", choices=ACTORS, help="Salir con código 3 si no le toca a este agente")
    args = parser.parse_args()
    if args.actor:
        if not args.hypothesis:
            parser.error("--as requiere --hypothesis")
        ok, message = check_turn(args.hypothesis, args.actor)
        print(("PERMITIDO " if ok else "DETENERSE ") + message)
        return 0 if ok else 3
    state = pipeline_state()
    if args.hypothesis:
        state = {"hypotheses": [r for r in state["hypotheses"] if r["hypothesis_id"] == args.hypothesis],
                 "violations": [v for v in state["violations"] if v["hypothesis_id"] == args.hypothesis]}
    print(json.dumps(state, indent=2, ensure_ascii=False))
    return 1 if any(v["severity"] == "error" for v in state["violations"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
