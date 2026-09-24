"""Registro append-only de ensayos IS para contabilidad de investigación."""
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def append_trial(root, record, agent="Codex", campaign=None, sensitivity=False, parent_run_id=None):
    spec = record.get("spec", {})
    metrics = record.get("metrics", {})
    quality = record.get("quality", {})
    row = {
        "run_id": record["run_id"], "timestamp": record.get("created_at") or datetime.now(timezone.utc).isoformat(),
        "agent": agent, "campaign": campaign, "hypothesis_id": spec.get("hypothesis_id"),
        "spec_hash": record.get("provenance", {}).get("spec_sha256"), "family": spec.get("family"),
        "symbol": spec.get("symbol"), "timeframe": spec.get("timeframe"),
        "is_sensitivity_run": bool(sensitivity), "seed": record.get("policy", {}).get("seed"),
        "gate_0_passed": quality.get("status") in {"PASS", "RESERVE"},
        "gate_0_failures": quality.get("failures", []), "trade_count": metrics.get("n_trades"),
        "net_pnl": metrics.get("net_pnl"), "pnl_percent": metrics.get("return_fraction"),
        "profit_factor": metrics.get("profit_factor"), "max_dd_percent": metrics.get("max_drawdown_fraction"),
        "aed_p_value": (record.get("diagnostics", {}).get("permutation_test") or {}).get("p_value_one_sided"),
        "aed_rejected": any(g.get("gate") == "aed_pattern_confirmed" and g.get("status") == "FAIL" for g in record.get("gates", [])),
        "costs_version": record.get("provenance", {}).get("cost_sha256"), "sensitivity_parent_run_id": parent_run_id,
    }
    path = Path(root) / "data" / "trials_registry.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if any(json.loads(line).get("run_id") == row["run_id"] for line in existing.splitlines() if line.strip()):
        raise ValueError(f"run_id duplicado en experiment registry: {row['run_id']}")
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")
    return row


def count_trials(root, hypothesis_id=None, family=None):
    path = Path(root) / "data" / "trials_registry.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []
    rows = [r for r in rows if (hypothesis_id is None or r.get("hypothesis_id") == hypothesis_id) and (family is None or r.get("family") == family)]
    return {"total": len(rows), "by_hypothesis": dict(sorted(Counter(r.get("hypothesis_id") for r in rows).items())), "by_family": dict(sorted(Counter(r.get("family") for r in rows).items()))}
