"""Comprar y mantener con el mismo ledger que qaf.engine.simulate (spread,
slippage, comision, financiacion): una posicion abierta al open de la primera
barra y cerrada al close de la ultima. Sin senal, SL/TP ni time-stop.

Exposicion (CLAUDE.md regla 19, "mismo capital"): por defecto el tamano es el
capital inicial invertido 1x -- nocional a la entrada = initial_equity, redondeado
hacia abajo a volume_step. Es el estandar "invertir el mismo dinero en el activo",
comparable entre simbolos; un lote fijo no lo es (1 lote XAUUSD ~2x el capital,
1 lote US30 ~0.3x). La estrategia arriesga risk_fraction por operacion: la
comparacion es de P&L neto absoluto sobre el mismo capital, no ajustada por riesgo.

Si el baseline neto es negativo (financiacion en CFD a holding largo), el piso de
la puerta no es cero: perder menos que el baseline no aprueba.
"""
import math
from .contracts import validate_instrument
from .costs import execution_cost, financing, margin_cash_per_lot, price_cash


def capital_matched_lots(price, c, capital):
    notional = margin_cash_per_lot(price, c)
    lots = min(math.floor((capital / notional + 1e-12) / c["volume_step"]) * c["volume_step"], c["volume_max"])
    if lots < c["volume_min"]:
        raise ValueError(f"Capital {capital} insuficiente para volume_min {c['volume_min']} (nocional por lote {notional:,.2f})")
    return lots


def simulate_baseline(df, instrument, direction=1, lots=None, initial_equity=100000, stress=1.0):
    """lots=None: mismo capital 1x (flujo normal). lots explicito: solo pruebas unitarias."""
    c = validate_instrument(instrument)
    if direction not in (1, -1):
        raise ValueError("direction debe ser 1 (largo) o -1 (corto)")
    if not isinstance(initial_equity, (int, float)) or isinstance(initial_equity, bool) or initial_equity <= 0 or not math.isfinite(initial_equity):
        raise ValueError("initial_equity invalido")
    if len(df) < 2:
        raise ValueError("Se necesitan al menos 2 barras para un baseline de comprar y mantener")

    times = df.time.tolist()
    opens, closes = df.open.to_numpy(dtype=float), df.close.to_numpy(dtype=float)
    entry_price = float(opens[0])
    if lots is None:
        lots = capital_matched_lots(entry_price, c, initial_equity)
        method = "capital_matched_1x"
    elif not isinstance(lots, (int, float)) or isinstance(lots, bool) or lots <= 0:
        raise ValueError("lots debe ser un numero positivo")
    else:
        method = "fixed_lots"
    notional = margin_cash_per_lot(entry_price, c) * lots

    entry_spread, entry_slip, entry_commission = execution_cost(entry_price, lots, c, stress)
    balance = initial_equity - entry_spread - entry_slip - entry_commission
    financing_cashflow = 0.0
    spread_cost, slippage_cost, commission_cost = entry_spread, entry_slip, entry_commission
    gross = exit_price = reason = exit_bar = None
    curve = []
    last = len(times) - 1
    # Mismo orden por barra que qaf.engine.simulate: financiacion al cruzar a la barra i,
    # chequeo de insolvencia al open, cierre en la ultima barra ANTES de registrar su equity.
    for i in range(1, len(times)):
        if exit_bar is not None:
            curve.append({"time": str(times[i]), "balance": balance, "floating_pnl": 0.0, "equity": balance, "exposed": 0})
            continue
        cashflow = financing(times[i - 1], times[i], direction, lots, c, stress)
        balance += cashflow
        financing_cashflow += cashflow
        if balance + price_cash(direction * (opens[i] - entry_price), c, lots) <= 0:
            exit_price, reason = float(opens[i]), "INSOLVENT_OPEN"
        elif i == last:
            exit_price, reason = float(closes[i]), "END_OF_SAMPLE"
        if reason is not None:
            exit_spread, exit_slip, exit_commission = execution_cost(exit_price, lots, c, stress)
            gross = price_cash(direction * (exit_price - entry_price), c, lots)
            balance += gross - exit_spread - exit_slip - exit_commission
            spread_cost += exit_spread
            slippage_cost += exit_slip
            commission_cost += exit_commission
            exit_bar = i
            curve.append({"time": str(times[i]), "balance": balance, "floating_pnl": 0.0, "equity": balance, "exposed": 1})
        else:
            floating = price_cash(direction * (closes[i] - entry_price), c, lots)
            liquidation = sum(execution_cost(closes[i], lots, c, stress))
            curve.append({"time": str(times[i]), "balance": balance, "floating_pnl": floating, "equity": balance + floating - liquidation, "exposed": 1})

    trade = {
        "entry_bar": 0, "entry_time": str(times[0]), "entry_price": entry_price, "direction": direction, "lots": lots,
        "exit_bar": exit_bar, "exit_time": str(times[exit_bar]), "exit_price": exit_price, "exit_reason": reason,
        "gross_pnl": gross, "financing_cashflow": financing_cashflow, "dividend_cashflow": 0.0,
        "spread_cost": spread_cost, "slippage_cost": slippage_cost, "commission_cost": commission_cost, "risk_cash": None,
    }
    trade["net_pnl"] = trade["gross_pnl"] + trade["financing_cashflow"] + trade["dividend_cashflow"] - trade["spread_cost"] - trade["slippage_cost"] - trade["commission_cost"]
    trade["return_r"] = None

    sizing = {"method": method, "lots": lots, "notional_at_entry": notional, "notional_to_capital": notional / initial_equity}
    result = {"trades": [trade], "equity": curve, "initial_equity": float(initial_equity), "skipped": {}, "sizing": sizing}
    if not math.isclose(initial_equity + trade["net_pnl"], balance, abs_tol=1e-6):
        raise ArithmeticError("El ledger del baseline no reconcilia con el balance final")
    return result
