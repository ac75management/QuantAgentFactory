from copy import deepcopy
import numpy as np
from .engine import simulate
from .metrics import summarize, block_bootstrap


def diagnose(df, spec, c, base, policy):
    """IS diagnostics with fixed parameters. Explicitly not optimizing or opening OOS."""
    folds = []
    warmup = max(spec["parameters"].get("slow", 0), spec["parameters"].get("lookback", 0), spec["parameters"]["atr_period"]) + 2
    boundaries = np.linspace(warmup, len(df), 4, dtype=int)
    for left, right in zip(boundaries[:-1], boundaries[1:]):
        if right-left < 60:
            continue
        begin = max(0, left-warmup)
        part = df.iloc[begin:right].reset_index(drop=True)
        result = simulate(part, spec, c, start_bar=left-begin)
        folds.append({"from": str(df.time.iloc[left]), "to": str(df.time.iloc[right-1]), **summarize(result)})
    stressed = summarize(simulate(df,spec,c,stress=2.0))
    sensitivity = []
    for factor in (.8, 1.2):
        neighbor = deepcopy(spec)
        neighbor["parameters"]["sl_atr"] *= factor
        neighbor["parameters"]["tp_atr"] *= factor
        sensitivity.append({"factor": factor, **summarize(simulate(df,neighbor,c))})
    bootstrap = block_bootstrap(base["trades"], policy["seed"], policy["bootstrap_iterations"])
    if "p_centered_bootstrap_one_sided" in bootstrap:
        bootstrap["p_campaign_bonferroni_upper_bound"] = min(1, bootstrap["p_centered_bootstrap_one_sided"] * policy["campaign_max_trials"])
        bootstrap['minimum_resolvable_adjusted_p'] = min(1,policy['campaign_max_trials']/(policy['bootstrap_iterations']+1))
        bootstrap['selection_warning'] = 'Diagnóstico aproximado; familia incluye todos los ensayos de campaña. No contempla exposición histórica previa ni establece significación final.'
    return {"fixed_parameter_temporal_folds": folds, "cost_stress_2x": stressed, "joint_stop_target_sensitivity": sensitivity, "bootstrap": bootstrap, "holdout": {"status": "NOT_OPENED"}, "walk_forward_optimization": {"status": "NOT_APPLICABLE", "reason": "Parametros fijos, sin entrenamiento ni optimizacion en este run"}, "permutation_test": {"status": "NOT_EXECUTED", "reason": "No confundir bootstrap de incertidumbre con permutacion de una hipotesis causal"}, "search_accounting": {"evaluations_per_trial": 7, "detail": "base + 3 folds + stress + 2 vecinos; presupuesto por candidato incluye esos diagnosticos preregistrados"}}


def screening_gates(metrics, diagnostics, quality, reserves, policy):
    gates = []
    def gate(name, passed, observed, threshold):
        gates.append({"gate": name, "status": "PASS" if passed else "FAIL", "observed": observed, "threshold": threshold})
    gate("minimum_trades", metrics["n_trades"] >= policy["min_trades"], metrics["n_trades"], policy["min_trades"])
    gate("net_positive", metrics["net_pnl"] > 0, metrics["net_pnl"], ">0")
    gate("profit_factor", (metrics["profit_factor"] or 0) > policy["min_profit_factor"], metrics["profit_factor"], policy["min_profit_factor"])
    gate("equity_drawdown", metrics["max_drawdown_fraction"] <= policy["max_drawdown_fraction"], metrics["max_drawdown_fraction"], policy["max_drawdown_fraction"])
    gate("friction", (metrics["friction_ratio"] or 0) >= policy["min_friction_ratio"], metrics["friction_ratio"], policy["min_friction_ratio"])
    gate("stress_net_positive", diagnostics["cost_stress_2x"]["net_pnl"] > 0, diagnostics["cost_stress_2x"]["net_pnl"], ">0 con friccion x2")
    bounds = diagnostics["bootstrap"].get("mean_r_ci95")
    gate("bootstrap_lower_bound", bool(bounds and bounds[0] > 0), bounds, "limite inferior >0; diagnostico IS")
    if metrics["n_trades"] < policy["min_trades"]:
        decision = "INCONCLUSIVE"
    elif any(g["status"] == "FAIL" for g in gates):
        decision = "DISCARDED_IS"
    elif quality["status"] != "PASS" or reserves:
        decision = "EXPLORATORY_CANDIDATE"
    else:
        decision = "READY_FOR_FROZEN_VALIDATION"
    return decision, gates
