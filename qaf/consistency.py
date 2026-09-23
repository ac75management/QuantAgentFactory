"""Coherencia entre las fuentes autoritativas y sus espejos legibles.

- Hipotesis: config/hypotheses.json es la fuente (qaf.io.load_hypotheses);
  docs/hypotheses/_registry.md es su espejo; state/research.sqlite3 guarda las
  decisiones reales de cada corrida. Las divergencias se reportan, no se corrigen.
- Universo: config/instruments.json es la fuente; la tabla de docs/universe.md se
  genera desde ahi (--write-universe) y cualquier edicion a mano se detecta.

Uso: python -m qaf.consistency [--write-universe]   (codigo de salida 1 si hay errores)
"""
import argparse
import json
import sqlite3
from pathlib import Path
from .io import ROOT, load_hypotheses, read_json

# Vocabulario permitido en config/hypotheses.json -> marcas aceptadas en la columna
# "estado" del espejo markdown (minusculas, subcadena).
STATUS_MARKERS = {
    "pending": ("pendiente", "pending"),
    "ready": ("ready", "lista para protocol", "lista para engine"),
    "discarded_is": ("discarded_is", "descartada_is", "descartada is", "descartada en is"),
    "inconclusive": ("inconclusive", "inconclusa"),
    "invalid_por_datos": ("invalid_por_datos", "invalida_por_datos", "inválida por datos"),
    "blocked_data": ("blocked_data", "bloqueada por datos"),
    "blocked_architecture": ("blocked_architecture", "bloqueada por arquitectura"),
    "rejected_by_user": ("rejected_by_user", "rechazada"),
    "ready_for_frozen_validation": ("ready_for_frozen_validation", "lista_para_oos"),
    "rejected_oos": ("rejected_oos", "rechazada_oos"),
    "approved": ("approved", "aprobada"),
}
RUNNABLE = {"pending", "ready"}
TERMINAL_RUN_DECISIONS = {"DISCARDED_IS", "BLOCKED_DATA"}
UNIVERSE_DOC = "docs/universe.md"
UNIVERSE_START = "<!-- qaf:universe:start -->"
UNIVERSE_END = "<!-- qaf:universe:end -->"


def markdown_states(root):
    path = Path(root) / "docs/hypotheses/_registry.md"
    states = {}
    if not path.exists():
        return states
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        cells = [cell.strip() for cell in line.strip().split("|")]
        if len(cells) < 4 or not line.strip().startswith("|"):
            continue
        hypothesis_id = cells[1]
        if not hypothesis_id or hypothesis_id == "#" or set(hypothesis_id) <= {"-"}:
            continue
        states[hypothesis_id] = cells[-2]
    return states


def run_decisions(root):
    path = Path(root) / "state/research.sqlite3"
    if not path.exists():
        return {}, None
    try:
        db = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
        try:
            rows = db.execute("SELECT hypothesis_id, reason_code FROM tasks WHERE stage='is_backtest' AND status IN ('completed','blocked')").fetchall()
        finally:
            db.close()
    except sqlite3.Error as error:
        return {}, str(error)
    decisions = {}
    for hypothesis_id, decision in rows:
        decisions.setdefault(hypothesis_id, set()).add(decision)
    return decisions, None


def check_hypothesis_registry(root=ROOT):
    issues = []
    def issue(severity, hypothesis_id, text):
        issues.append({"severity": severity, "hypothesis_id": hypothesis_id, "issue": text})
    catalog = load_hypotheses(root)
    if catalog is None:
        issue("error", None, "Falta config/hypotheses.json (fuente autoritativa)")
        return issues
    mirror = markdown_states(root)
    for hypothesis_id, row in catalog.items():
        status = row.get("status")
        if status not in STATUS_MARKERS:
            issue("error", hypothesis_id, f"Estado {status!r} fuera del vocabulario {sorted(STATUS_MARKERS)}")
            continue
        if hypothesis_id not in mirror:
            issue("error", hypothesis_id, "Existe en config/hypotheses.json pero no en docs/hypotheses/_registry.md")
            continue
        text = mirror[hypothesis_id].lower()
        if not any(marker in text for marker in STATUS_MARKERS[status]):
            issue("error", hypothesis_id, f"El espejo markdown no refleja el estado {status!r}: {mirror[hypothesis_id][:120]!r}")
    for hypothesis_id in sorted(set(mirror) - set(catalog)):
        issue("error", hypothesis_id, "Existe en docs/hypotheses/_registry.md pero no en config/hypotheses.json")
    decisions, error = run_decisions(root)
    if error:
        issue("warning", None, f"No se pudo leer state/research.sqlite3: {error}")
    for hypothesis_id, found in decisions.items():
        status = (catalog.get(hypothesis_id) or {}).get("status")
        if status in RUNNABLE and found & TERMINAL_RUN_DECISIONS:
            issue("warning", hypothesis_id, f"Estado {status!r} pero SQLite registra {sorted(found & TERMINAL_RUN_DECISIONS)}: revisar si debe cerrarse")
    return issues


def render_universe_table(root=ROOT):
    """Tabla legible del universo, derivada solo de config/instruments.json."""
    instruments = read_json(Path(root) / "config/instruments.json")
    lines = ["| alias | symbol_mt5 | clase | timeframes | status |", "|---|---|---|---|---|"]
    for alias, row in instruments.items():
        lines.append(f"| {alias} | {row.get('symbol_mt5') or '—'} | {row.get('asset_class')} | "
                     f"{', '.join(row.get('timeframes', []))} | {row.get('status')} |")
    return "\n".join(lines)


def _universe_block(text):
    if UNIVERSE_START not in text or UNIVERSE_END not in text:
        return None
    return text.split(UNIVERSE_START, 1)[1].split(UNIVERSE_END, 1)[0].strip()


def check_universe_mirror(root=ROOT):
    path = Path(root) / UNIVERSE_DOC
    if not path.exists():
        return []
    block = _universe_block(path.read_text(encoding="utf-8-sig"))
    if block is None:
        return [{"severity": "error", "hypothesis_id": None, "issue": f"{UNIVERSE_DOC} no tiene los marcadores de la tabla generada"}]
    if block != render_universe_table(root):
        return [{"severity": "error", "hypothesis_id": None,
                 "issue": f"{UNIVERSE_DOC} no coincide con config/instruments.json: regenerar con python -m qaf.consistency --write-universe"}]
    return []


def write_universe_mirror(root=ROOT):
    path = Path(root) / UNIVERSE_DOC
    text = path.read_text(encoding="utf-8-sig")
    if _universe_block(text) is None:
        raise ValueError(f"{UNIVERSE_DOC} no tiene los marcadores {UNIVERSE_START} / {UNIVERSE_END}")
    head, rest = text.split(UNIVERSE_START, 1)
    tail = rest.split(UNIVERSE_END, 1)[1]
    path.write_text(f"{head}{UNIVERSE_START}\n{render_universe_table(root)}\n{UNIVERSE_END}{tail}", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Coherencia entre fuentes autoritativas y espejos")
    parser.add_argument("--write-universe", action="store_true", help="regenerar la tabla de docs/universe.md")
    args = parser.parse_args()
    if args.write_universe:
        write_universe_mirror()
    issues = check_hypothesis_registry() + check_universe_mirror()
    print(json.dumps(issues, indent=2, ensure_ascii=False))
    return 1 if any(i["severity"] == "error" for i in issues) else 0


if __name__ == "__main__":
    raise SystemExit(main())
