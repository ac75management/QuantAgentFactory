# Sensitivity Analysis — Diagnostic Status

**Status:** Infrastructure ready, execution deferred.

## Schema
Sensitivity analysis is **documented but not executed** as of 2026-09-24. The registry schema includes support:
- `is_sensitivity_run: bool` — marks a trial as a sensitivity neighbor (±10%, ±20% parameter sweep)
- `sensitivity_parent_run_id: str` — links each neighbor trial to its base run

**Example registry entries:**
```json
{ "hypothesis_id": "007", "is_sensitivity_run": false, "sensitivity_parent_run_id": null, ... }  // Base run
{ "hypothesis_id": "007", "is_sensitivity_run": true, "sensitivity_parent_run_id": "7a8b9c0d", ... }  // Neighbor
```

## Policy
- Each executed neighbor (±10%, ±20% variant) is registered as a **separate trial** in `data/trials_registry.jsonl`.
- Sensitivity trials count toward `N` (total trial accounting per hypothesis/family) to control multiple-testing inflation.
- **Execution trigger:** When a hypothesis IS-run is approved for deep investigation.
- **No active campaign:** Sensitivity runs are not launched proactively; they are part of a diagnostic, not a search.

## Next Step
When Alexander approves a candidate for detailed sensitivity study, implement `qaf/runner.py::run_sensitivity()` to:
1. Read base spec and results.
2. Generate ±10%, ±20% parameter neighbors.
3. Execute each as a separate IS run.
4. Register each with `sensitivity_parent_run_id` pointing to the base run.
5. Report counts and statistics (mean PnL, robustness score) in the result.html.

## Files
- Registry: `data/trials_registry.jsonl` (17-field JSONL, append-only)
- CLI: `python -m qaf count-trials --hypothesis <id>` (sums all trials including sensitivity)
- Validator: `qaf/experiment_registry.py::count_trials()`
