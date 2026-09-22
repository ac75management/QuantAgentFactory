"""Funciones monetarias comunes para simulaciones historicas.

Este modulo no decide valores de mercado. Recibe los parametros del cost model
y evita que cada backtest implemente conversiones distintas.
"""


def price_pnl_per_lot(entry_price, exit_price, tick_size, tick_value):
    if tick_size <= 0 or tick_value <= 0:
        raise ValueError("tick_size y tick_value deben ser positivos")
    return (exit_price - entry_price) / tick_size * tick_value


def spread_cost_per_lot(spread_points, tick_size, tick_value, *, point):
    if spread_points < 0:
        raise ValueError("spread_points no puede ser negativo")
    if point <= 0 or tick_size <= 0 or tick_value <= 0:
        raise ValueError('point, tick_size y tick_value deben ser positivos')
    return spread_points * point / tick_size * tick_value


def commission_roundturn_per_lot(commission_per_side):
    if commission_per_side < 0:
        raise ValueError("commission_per_side no puede ser negativo")
    return 2.0 * commission_per_side


def commission_percentage_roundturn(
    entry_notional, exit_notional, percentage_per_side
):
    if entry_notional < 0 or exit_notional < 0 or percentage_per_side < 0:
        raise ValueError("notionales y porcentaje deben ser no negativos")
    return percentage_per_side * (entry_notional + exit_notional)


def swap_cost_per_lot(nights, swap_long, triple_night_indices=()):
    if nights < 0 or swap_long == 0:
        return 0.0
    triple_indices = set(triple_night_indices)
    return swap_long * sum(3 if index in triple_indices else 1 for index in range(nights))
