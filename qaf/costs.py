from datetime import timedelta
import pandas as pd


def price_cash(delta, c, lots=1):
    return delta / c["tick_size"] * c["tick_value"] * lots


def points_cash(points, c, lots=1):
    return price_cash(points * c["point"], c, lots)


def execution_cost(price, lots, c, stress=1.0):
    spread = points_cash(c["spread_points"] / 2, c, lots) * stress
    slippage = points_cash(c["slippage_points_per_side"], c, lots) * stress
    if c["commission_type"] == "cash":
        commission = c["commission_per_side"] * lots * c["currency_to_account"]
    else:
        commission = abs(price * c["contract_size"] * lots) * c["commission_per_side"] * c["currency_to_account"]
    return spread, slippage, commission * stress


def financing(start, end, direction, lots, c, stress=1.0):
    """Cashflows at configured local rollover instants, start < instant <= end.

    Input rates are an explicitly labelled current-cost scenario, not historical rates.
    Energy daily_equal deliberately does not multiply a Monday quote on Wednesdays.
    """
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    zone = c.get("rollover_timezone", "America/New_York")
    first, last = start.tz_convert(zone).date(), end.tz_convert(zone).date()
    rate = c["swap_long"] if direction == 1 else c["swap_short"]
    total = 0.0
    day = first
    while day <= last:
        instant = pd.Timestamp(f"{day} {c.get('rollover_time', '17:00')}", tz=zone)
        if day.weekday() < 5 and start < instant <= end:
            multiplier = 3 if day.weekday() == c.get("triple_weekday") and c.get("swap_schedule") != "daily_equal" else 1
            # Stress costs, never improve credits.
            total += rate * multiplier * lots * (stress if rate < 0 else 1 / stress)
        day += timedelta(days=1)
    return total
