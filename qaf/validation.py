from copy import deepcopy
import math
import numpy as np
from .engine import simulate
from .metrics import summarize, block_bootstrap


def _finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def validate_policy(policy):
    integer_fields = {"min_trades": 1, "bootstrap_iterations": 1, "campaign_max_trials": 1}
    for key, minimum in integer_fields.items():
        if not isinstance(policy.get(key), int) or isinstance(policy.get(key), bool) or policy[key] < minimum:
            raise ValueError(f"Politica invalida: {key} debe ser entero >= {minimum}")
    if not isinstance(policy.get("seed"), int) or isinstance(policy.get("seed"), bool):
        raise ValueError("Politica invalida: seed debe ser entero")
    if not _finite(policy.get("min_profit_factor")) or policy["min_profit_factor"] <= 1:
        raise ValueError("Politica invalida: min_profit_factor debe ser finito y > 1")
    if not _finite(policy.get("max_drawdown_fraction")) or not 0 < policy["max_drawdown_fraction"] <= 1:
        raise ValueError("Politica invalida: max_drawdown_fraction debe estar en (0,1]")
    if not _finite(policy.get("min_friction_ratio")) or policy["min_friction_ratio"] <= 0:
        raise ValueError("Politica invalida: min_friction_ratio debe ser > 0")
    return policy


def diagnose(df, spec, c, base, policy):
    """IS diagnostics with fixed parameters. Explicitly not optimizing or opening OOS."""
    validate_policy(policy)
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
    validate_policy(policy)
    # Calidad de datos fallida bloquea el veredicto aqui mismo, sin depender
    # de que quien llame ya haya evitado invocar esta funcion sobre datos FAIL.
    if quality.get("status") not in ("PASS", "RESERVE"):
        return "BLOCKED_DATA", []
    gates = []
    def gate(name, passed, observed, threshold):
        gates.append({"gate": name, "status": "PASS" if passed else "FAIL", "observed": observed, "threshold": threshold})
    n_trades = metrics["n_trades"]
    valid_n = isinstance(n_trades, int) and not isinstance(n_trades, bool) and n_trades >= 0
    gate("minimum_trades", valid_n and n_trades >= policy["min_trades"], n_trades, policy["min_trades"])
    net_pnl = metrics["net_pnl"]
    gate("net_positive", _finite(net_pnl) and net_pnl > 0, net_pnl, ">0")
    pf = metrics["profit_factor"]
    no_loss_profit = pf is None and valid_n and n_trades > 0 and _finite(net_pnl) and net_pnl > 0 and metrics.get("profit_factor_note") == "Sin perdidas: PF indefinido"
    gate("profit_factor", no_loss_profit or (_finite(pf) and pf > policy["min_profit_factor"]), pf, policy["min_profit_factor"])
    dd = metrics["max_drawdown_fraction"]
    gate("equity_drawdown", _finite(dd) and 0 <= dd <= policy["max_drawdown_fraction"], dd, policy["max_drawdown_fraction"])
    fr = metrics["friction_ratio"]
    gate("friction", _finite(fr) and fr >= policy["min_friction_ratio"], fr, policy["min_friction_ratio"])
    stress_pnl = diagnostics["cost_stress_2x"]["net_pnl"]
    gate("stress_net_positive", _finite(stress_pnl) and stress_pnl > 0, stress_pnl, ">0 con friccion x2")
    bootstrap = diagnostics["bootstrap"]
    bounds = bootstrap.get("mean_r_ci95")
    valid_bounds = bool(bounds and len(bounds) == 2 and all(_finite(b) for b in bounds) and bounds[0] <= bounds[1])
    valid_bootstrap = bootstrap.get("status") == "DIAGNOSTIC" and bootstrap.get("n") == n_trades and bootstrap.get("iterations") == policy["bootstrap_iterations"]
    gate("bootstrap_lower_bound", valid_bootstrap and valid_bounds and bounds[0] > 0, bounds, "bootstrap completo del conjunto de operaciones; limite inferior >0")
    if not (valid_n and n_trades >= policy["min_trades"]):
        decision = "INCONCLUSIVE"
    elif any(g["status"] == "FAIL" for g in gates):
        decision = "DISCARDED_IS"
    elif quality["status"] != "PASS" or reserves:
        decision = "EXPLORATORY_CANDIDATE"
    else:
        decision = "READY_FOR_FROZEN_VALIDATION"
    return decision, gates
