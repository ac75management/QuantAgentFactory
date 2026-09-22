"""Auditoria de solo lectura antes de modificar o ejecutar el proyecto."""
import argparse
import json
import subprocess
from pathlib import Path

from .consistency import check_hypothesis_registry
from .coordination import Coordination
from .io import ROOT
from .pipeline import pipeline_state


REQUIRED = (
    "AGENTS.md",
    "CLAUDE.md",
    "config/hypotheses.json",
    "config/instruments.json",
    "config/runner.json",
    "docs/VALIDATION_ROADMAP.md",
)
CRITICAL_PREFIXES = ("qaf/", "tests/", "config/", ".claude/agents/")


def _git_status(root):
    process = subprocess.run(
        ["git", "status", "--porcelain=v1"], cwd=root, text=True,
        capture_output=True, check=False,
    )
    if process.returncode:
        return None, process.stderr.strip() or "git status fallo"
    return [line for line in process.stdout.splitlines() if line], None


def audit(root=ROOT, include_git=True):
    root = Path(root).resolve()
    checks = []

    def add(name, status, detail, evidence=None):
        row = {"check": name, "status": status, "detail": detail}
        if evidence is not None:
            row["evidence"] = evidence
        checks.append(row)

    missing = [path for path in REQUIRED if not (root / path).exists()]
    add("required_files", "FAIL" if missing else "PASS",
        "Faltan fuentes autoritativas" if missing else "Fuentes autoritativas presentes", missing or None)

    try:
        registry = check_hypothesis_registry(root)
        errors = [row for row in registry if row["severity"] == "error"]
        add("hypothesis_consistency", "FAIL" if errors else "PASS",
            f"{len(errors)} errores; {len(registry) - len(errors)} advertencias", registry or None)
    except Exception as error:
        add("hypothesis_consistency", "FAIL", str(error))

    try:
        state = pipeline_state(root)
        blocking = [row for row in state["violations"] if row["severity"] == "error"]
        add("pipeline", "FAIL" if blocking else "PASS",
            f"{len(blocking)} violaciones bloqueantes; {len(state['violations']) - len(blocking)} advertencias",
            state["violations"] or None)
    except Exception as error:
        add("pipeline", "FAIL", str(error))

    try:
        coordination_db = root / "state/coordination.sqlite3"
        if coordination_db.exists():
            with Coordination(root) as coordination:
                leases = coordination.active()
        else:
            leases = []
        stale = [row for row in leases if row["stale"]]
        add("coordination", "WARN" if stale else "PASS",
            f"{len(leases)} reservas activas; {len(stale)} vencidas", stale or None)
    except Exception as error:
        add("coordination", "FAIL", str(error))

    if include_git:
        status, error = _git_status(root)
        if error:
            add("git", "FAIL", error)
        else:
            critical = [line for line in status if line[3:].replace("\\", "/").startswith(CRITICAL_PREFIXES)]
            detail = f"{len(status)} cambios sin consolidar; {len(critical)} afectan código, pruebas, configuración o agentes"
            add("git", "WARN" if status else "PASS", detail, status or None)

    state_lines = len((root / "PROJECT_STATE.md").read_text(encoding="utf-8-sig").splitlines()) if (root / "PROJECT_STATE.md").exists() else 0
    add("state_log", "WARN" if state_lines > 250 else "PASS",
        f"PROJECT_STATE.md tiene {state_lines} líneas; es historial, no fuente operativa" if state_lines else "PROJECT_STATE.md ausente")
    overall = "FAIL" if any(row["status"] == "FAIL" for row in checks) else ("WARN" if any(row["status"] == "WARN" for row in checks) else "PASS")
    return {"status": overall, "checks": checks}


def main():
    parser = argparse.ArgumentParser(description="Preflight de coherencia y coordinación de QuantAgentFactory")
    parser.add_argument("--strict", action="store_true", help="tratar advertencias como error de salida")
    parser.add_argument("--no-git", action="store_true")
    args = parser.parse_args()
    result = audit(include_git=not args.no_git)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result["status"] == "FAIL" or (args.strict and result["status"] == "WARN"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
