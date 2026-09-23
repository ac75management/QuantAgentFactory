"""AED (analisis exploratorio de datos): confirma que la senal cruda de
qaf.signals.generate predice un movimiento direccional futuro en los datos IS,
antes de aceptar como candidato el backtest costeado de qaf.engine.simulate.

Cierra el hallazgo C1 de docs/archive/reviews/audit_qaf_complete_2026-09-22.md y llena la puerta
"p-valor de permutacion < 0.05" de CLAUDE.md regla 5. Es una prueba de la senal,
no una busqueda: no cambia ningun parametro de la spec.
"""
import numpy as np
from .signals import generate

MIN_SIGNALS = 20


def permutation_test(df, spec, policy, min_signals=MIN_SIGNALS):
    """Prueba de permutacion por rotacion circular.

    Estadistico: retorno direccional medio, direction * (close[e+h] - open[e]) / open[e],
    sobre cada barra de entrada e (signal[e-1] != 0 llena en el open de e, igual que
    qaf.engine.simulate), con h = spec['parameters']['max_holding'] (ya declarado en
    la spec: cero parametros nuevos que ajustar despues de ver el resultado).

    H0: el momento en que dispara la senal no aporta informacion sobre ese retorno.
    Nula: se rotan circularmente las posiciones de entrada dentro del rango valido de
    barras. La rotacion conserva el numero de senales, su secuencia de direcciones y
    su agrupamiento en rachas; una permutacion de barras sueltas no lo conserva e
    infla falsas confirmaciones cuando la senal dispara en barras consecutivas.
    """
    signal = generate(df, spec)
    horizon = spec["parameters"]["max_holding"]
    opens = df.open.to_numpy(dtype=float)
    closes = df.close.to_numpy(dtype=float)
    n = len(df)
    base = {"method": "Permutación por rotación circular de las entradas (conserva número, direcciones y rachas de la señal). "
                      "H0: la temporalidad de la señal cruda —sin costos, SL/TP ni sizing— no informa el retorno direccional a horizon_bars. "
                      "No es el bootstrap de operaciones de diagnostics.bootstrap.",
            "horizon_bars": horizon, "min_signals": min_signals}

    first, last = 1, n - horizon - 1
    if last < first:
        return {**base, "status": "INCONCLUSIVE", "reason": "Ventana IS más corta que el horizonte", "n_signals": 0}
    bars = np.arange(first, last + 1)
    forward = (closes[bars + horizon] - opens[bars]) / opens[bars]

    entries = np.flatnonzero(signal[:-1]) + 1
    entries = entries[(entries >= first) & (entries <= last)]
    k = len(entries)
    if k < min_signals:
        return {**base, "status": "INCONCLUSIVE", "reason": f"Menos de {min_signals} señales crudas con horizonte completo en la ventana IS", "n_signals": k}

    directions = signal[entries - 1]
    positions = entries - first
    m = len(bars)
    observed = float((directions * forward[positions]).mean())

    iterations = policy["bootstrap_iterations"]
    rng = np.random.default_rng(policy["seed"])
    offsets = rng.integers(1, m, size=iterations)
    null = np.array([(directions * forward[(positions + s) % m]).mean() for s in offsets])
    p_value = (int((null >= observed).sum()) + 1) / (iterations + 1)
    return {**base, "status": "EXECUTED", "n_signals": k, "n_long": int((directions > 0).sum()), "n_short": int((directions < 0).sum()),
            "observed_mean_directional_return": observed, "null_mean_directional_return": float(null.mean()),
            "null_p95_directional_return": float(np.quantile(null, .95)), "p_value_one_sided": p_value,
            "iterations": iterations, "distinct_offsets_available": m - 1, "seed": policy["seed"]}
