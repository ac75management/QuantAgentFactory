from copy import deepcopy
import math
import numpy as np
from .aed import permutation_test as aed_permutation_test
from .contracts import validate_spec
from .engine import simulate
from .metrics import summarize, block_bootstrap

AED_ALPHA = 0.05  # CLAUDE.md regla 5
SENSITIVITY_STEPS = (-0.2, -0.1, 0.1, 0.2)  # CLAUDE.md regla 14: +-10-20% por parametro


def _finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def validate_policy(policy):
    integer_fields = {"min_trades": 1, "bootstrap_iterations": 1, "campaign_max_trials": 1,
                      "sensitivity_mc_iterations": 200, "sensitivity_min_valid": 1}
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
    if policy["sensitivity_min_valid"] > policy["sensitivity_mc_iterations"]:
        raise ValueError("Politica invalida: sensitivity_min_valid no puede superar sensitivity_mc_iterations")
    if not _finite(policy.get("sensitivity_mc_range")) or not 0 < policy["sensitivity_mc_range"] <= 1:
        raise ValueError("Politica invalida: sensitivity_mc_range debe estar en (0,1]")
    for key in ("sensitivity_max_original_percentile", "sensitivity_min_positive_share"):
        if not _finite(policy.get(key)) or not 0 <= policy[key] <= 1:
            raise ValueError(f"Politica invalida: {key} debe estar en [0,1]")
    return policy


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _scaled(value, factor):
    if _is_int(value):
        return int(round(value * (1 + factor)))
    return value * (1 + factor)


def _neighbor(spec, changes):
    neighbor = deepcopy(spec)
    neighbor["parameters"].update(changes)
    try:
        validate_spec(neighbor)
    except ValueError as error:
        return None, str(error)
    return neighbor, None


def parameter_sensitivity(df, spec, c, base_net_pnl, policy):
    """CLAUDE.md regla 14, sin seleccion: ningun vecino reemplaza a la spec.

    1) Uno a la vez: cada parametro de spec['parameters'] a -20/-10/+10/+20%
       (enteros redondeados; si el redondeo no cambia el valor, se mueve 1 unidad).
    2) Montecarlo: 200 vecinos con todos los parametros movidos a la vez, uniforme en +-20%.
    La spec original debe quedar dentro de su vecindad, no en su pico aislado.
    """
    params = spec["parameters"]
    one_at_a_time = []
    for name in sorted(params):
        seen = {params[name]}
        for step in SENSITIVITY_STEPS:
            value = _scaled(params[name], step)
            if _is_int(params[name]) and value == params[name]:
                value += 1 if step > 0 else -1
            if value in seen:
                continue
            seen.add(value)
            neighbor, error = _neighbor(spec, {name: value})
            if neighbor is None:
                one_at_a_time.append({"parameter": name, "step": step, "value": value, "status": "INVALID_NEIGHBOR", "reason": error})
                continue
            m = summarize(simulate(df, neighbor, c))
            one_at_a_time.append({"parameter": name, "step": step, "value": value, "status": "EVALUATED", "n_trades": m["n_trades"], "net_pnl": m["net_pnl"], "profit_factor": m["profit_factor"], "max_drawdown_fraction": m["max_drawdown_fraction"]})

    rng = np.random.default_rng(policy["seed"])
    pnls, invalid = [], 0
    iterations = policy["sensitivity_mc_iterations"]
    spread = policy["sensitivity_mc_range"]
    for _ in range(iterations):
        changes = {name: _scaled(value, rng.uniform(-spread, spread)) for name, value in params.items()}
        neighbor, _ = _neighbor(spec, changes)
        if neighbor is None:
            invalid += 1
            continue
        pnls.append(summarize(simulate(df, neighbor, c))["net_pnl"])

    out = {"method": "Uno a la vez (-20/-10/+10/+20%) y Montecarlo conjunto uniforme en +-20% sobre todos los parámetros; sin selección de vecinos",
           "one_at_a_time": one_at_a_time, "monte_carlo_iterations": iterations,
           "monte_carlo_valid": len(pnls), "monte_carlo_invalid": invalid, "original_net_pnl": base_net_pnl,
           "max_original_percentile": policy["sensitivity_max_original_percentile"],
           "min_positive_share": policy["sensitivity_min_positive_share"],
           "evaluations": len(pnls) + sum(r["status"] == "EVALUATED" for r in one_at_a_time)}
    if len(pnls) < policy["sensitivity_min_valid"]:
        return {**out, "status": "INCONCLUSIVE", "reason": f"Menos de {policy['sensitivity_min_valid']} vecinos válidos de Montecarlo"}
    values = np.array(pnls, dtype=float)
    return {**out, "status": "EXECUTED", "original_percentile": float((values < base_net_pnl).mean()),
            "positive_share": float((values > 0).mean()),
            "monte_carlo_net_pnl_p05_p50_p95": [float(x) for x in np.quantile(values, [.05, .5, .95])]}


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
    sensitivity = parameter_sensitivity(df, spec, c, summarize(base)["net_pnl"], policy)
    bootstrap = block_bootstrap(base["trades"], policy["seed"], policy["bootstrap_iterations"])
    if "p_centered_bootstrap_one_sided" in bootstrap:
        bootstrap["p_campaign_bonferroni_upper_bound"] = min(1, bootstrap["p_centered_bootstrap_one_sided"] * policy["campaign_max_trials"])
        bootstrap['minimum_resolvable_adjusted_p'] = min(1,policy['campaign_max_trials']/(policy['bootstrap_iterations']+1))
        bootstrap['selection_warning'] = 'Diagnóstico aproximado; familia incluye todos los ensayos de campaña. No contempla exposición histórica previa ni establece significación final.'
    evaluations = 1 + len(folds) + 1 + sensitivity["evaluations"] + 1
    return {"fixed_parameter_temporal_folds": folds, "cost_stress_2x": stressed, "parameter_sensitivity": sensitivity, "bootstrap": bootstrap,
            "permutation_test": aed_permutation_test(df, spec, policy), "holdout": {"status": "NOT_OPENED"},
            "walk_forward": {"status": "NOT_IMPLEMENTED", "reason": "Las ventanas de fixed_parameter_temporal_folds usan parámetros fijos; no hay reentrenamiento por ventana. El walk-forward real (regla 18) es prerrequisito de validación final, ver docs/VALIDATION_ROADMAP.md."},
            "search_accounting": {"evaluations_per_trial": evaluations, "detail": "base + folds temporales + estrés x2 + vecinos de sensibilidad + baseline; ningún vecino se selecciona ni reemplaza la spec"}}


def screening_gates(metrics, diagnostics, quality, reserves, policy, baseline_metrics=None):
    """Puertas IS. Fallan cerradas: un diagnostico ausente es FAIL, nunca una puerta omitida.
    baseline_metrics=None solo existe para llamadores aislados; el flujo normal
    (qaf.runner.execute) siempre lo calcula."""
    validate_policy(policy)
    # Calidad de datos fallida bloquea el veredicto aqui mismo, sin depender
    # de que quien llame ya haya evitado invocar esta funcion sobre datos FAIL.
    if quality.get("status") not in ("PASS", "RESERVE"):
        return "BLOCKED_DATA", []
    gates = []
    def record(name, status, observed, threshold):
        gates.append({"gate": name, "status": status, "observed": observed, "threshold": threshold})
    def gate(name, passed, observed, threshold):
        record(name, "PASS" if passed else "FAIL", observed, threshold)
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

    # CLAUDE.md regla 19: comprar y mantener del MISMO simbolo/timeframe/ventana/costos y el
    # mismo capital (qaf.baseline). Si el baseline es negativo el piso no es cero:
    # perder menos que el baseline no aprueba.
    baseline_threshold = "estrategia > 0 Y estrategia > baseline (comprar y mantener, mismo símbolo/timeframe/IS/costos/capital)"
    if baseline_metrics is None:
        record("beats_baseline", "FAIL", "NOT_COMPUTED", baseline_threshold)
    else:
        baseline_pnl = baseline_metrics["net_pnl"]
        gate("beats_baseline", _finite(net_pnl) and _finite(baseline_pnl) and net_pnl > 0 and net_pnl > baseline_pnl,
             {"strategy_net_pnl": net_pnl, "baseline_net_pnl": baseline_pnl}, baseline_threshold)

    # CLAUDE.md regla 5 + hallazgo C1: la senal cruda debe predecir direccion.
    aed_threshold = f"<{AED_ALPHA} (permutación por rotación de la señal cruda, qaf.aed)"
    perm = diagnostics.get("permutation_test") or {}
    if perm.get("status") == "EXECUTED":
        p_value = perm.get("p_value_one_sided")
        gate("aed_pattern_confirmed", _finite(p_value) and 0 < p_value <= 1 and p_value < AED_ALPHA, p_value, aed_threshold)
    elif perm.get("status") == "INCONCLUSIVE":
        record("aed_pattern_confirmed", "INCONCLUSIVE", {"n_signals": perm.get("n_signals"), "reason": perm.get("reason")}, aed_threshold)
    else:
        record("aed_pattern_confirmed", "FAIL", "NOT_EXECUTED", aed_threshold)

    # CLAUDE.md regla 14: la spec no puede ser una ganadora aislada en su vecindad.
    max_percentile = policy["sensitivity_max_original_percentile"]
    min_positive_share = policy["sensitivity_min_positive_share"]
    sens_threshold = f"percentil de la spec <= {max_percentile} y >= {min_positive_share:.0%} de vecinos Montecarlo con neto >0"
    sens = diagnostics.get("parameter_sensitivity") or {}
    if sens.get("status") == "EXECUTED":
        percentile, share = sens.get("original_percentile"), sens.get("positive_share")
        gate("parameter_sensitivity", _finite(percentile) and _finite(share) and percentile <= max_percentile and share >= min_positive_share,
             {"original_percentile": percentile, "positive_share": share}, sens_threshold)
    elif sens.get("status") == "INCONCLUSIVE":
        record("parameter_sensitivity", "INCONCLUSIVE", {"monte_carlo_valid": sens.get("monte_carlo_valid"), "reason": sens.get("reason")}, sens_threshold)
    else:
        record("parameter_sensitivity", "FAIL", "NOT_EXECUTED", sens_threshold)

    if not (valid_n and n_trades >= policy["min_trades"]):
        decision = "INCONCLUSIVE"
    elif any(g["status"] == "FAIL" for g in gates):
        decision = "DISCARDED_IS"
    elif any(g["status"] == "INCONCLUSIVE" for g in gates):
        decision = "INCONCLUSIVE"
    elif quality["status"] != "PASS" or reserves:
        decision = "EXPLORATORY_CANDIDATE"
    else:
        decision = "READY_FOR_FROZEN_VALIDATION"
    return decision, gates
