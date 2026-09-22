import math
import re
from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

TIMEFRAMES = {"H1": 60, "H4": 240, "D1": 1440}
SWAP_SCHEDULES = {"triple", "daily_equal"}
MARGIN_MODES = {"cfd_notional", "forex_base_account", "forex_base_quote"}
FAMILIES = {"streak_reversal", "trend_cross", "channel_breakout", "oscillator_reversion"}


def positive(value, name, zero=False):
    if not isinstance(value, (float, int)) or isinstance(value, bool) or not math.isfinite(value) or (value < 0 if zero else value <= 0):
        raise ValueError(f"{name}: numero finito {'no negativo' if zero else 'positivo'} requerido")


def validate_spec(spec):
    for key in ("id", "family", "symbol", "timeframe", "parameters", "rationale", "hypothesis_id"):
        if key not in spec or not spec[key]:
            raise ValueError(f"Spec incompleta: {key}")
    if not isinstance(spec["hypothesis_id"], str) or not spec["hypothesis_id"].strip():
        raise ValueError("hypothesis_id invalido: la estrategia debe estar vinculada al registro de hipótesis")
    if spec["family"] not in FAMILIES:
        raise ValueError("Familia no implementada")
    if not isinstance(spec['symbol'], str) or not re.fullmatch(r'[A-Za-z0-9_]+',spec['symbol']):
        raise ValueError('Simbolo invalido')
    if spec.get('direction','both') not in ('both','long','short'):
        raise ValueError('Direccion invalida')
    positive(spec.get('initial_equity',100000),'initial_equity')
    if spec["timeframe"] not in TIMEFRAMES:
        raise ValueError("Timeframe no implementado")
    p = spec["parameters"]
    for key in ("atr_period", "max_holding"):
        if not isinstance(p.get(key), int) or not 1 <= p[key] <= 2000:
            raise ValueError(f"Parametro entero fuera de rango: {key}")
    for key in ("sl_atr", "tp_atr"):
        positive(p.get(key), key)
    risk = spec.get("risk_fraction", 0.005)
    positive(risk,'risk_fraction')
    if not 0 < risk <= 0.02:
        raise ValueError("Riesgo por operacion fuera de (0, 2%]")
    if spec["family"] == "streak_reversal":
        if not isinstance(p.get("streak"), int) or not 2 <= p["streak"] <= 20:
            raise ValueError("Racha invalida")
    if spec["family"] == "trend_cross":
        if not all(isinstance(p.get(k), int) for k in ("fast", "slow")) or not 2 <= p["fast"] < p["slow"] <= 500:
            raise ValueError("Periodos fast/slow invalidos")
    if spec["family"] == "channel_breakout":
        if not isinstance(p.get("lookback"), int) or not 2 <= p["lookback"] <= 500:
            raise ValueError("lookback invalido")
    if spec["family"] == "oscillator_reversion":
        if not isinstance(p.get("rsi_period"), int) or not 2 <= p["rsi_period"] <= 100:
            raise ValueError("rsi_period invalido")
        positive(p.get("entry_threshold"), "entry_threshold")
        if not 0 < p["entry_threshold"] <= 50:
            raise ValueError("entry_threshold fuera de (0, 50]")
        if not isinstance(p.get("trend_filter_sma"), int) or not 2 <= p["trend_filter_sma"] <= 500:
            raise ValueError("trend_filter_sma invalido")
    return spec


def validate_instrument(c):
    for key in ("symbol_mt5", "asset_class", "source_snapshot"):
        if not isinstance(c.get(key), str) or not c[key].strip():
            raise ValueError(f"{key} ausente o invalido")
    if c.get("status") != "research":
        raise ValueError("Solo instrumentos con status=research pueden ejecutarse")
    for key in ("point", "tick_size", "tick_value", "contract_size", "volume_min", "volume_step", "volume_max", "max_leverage", "currency_to_account"):
        positive(c.get(key), key)
    for key in ("spread_points", "slippage_points_per_side", "commission_per_side"):
        positive(c.get(key), key, zero=True)
    if c["volume_max"] < c["volume_min"]:
        raise ValueError("volume_max < volume_min")
    if c["volume_step"] > c["volume_max"]:
        raise ValueError("volume_step > volume_max")
    for key in ("volume_min", "volume_max"):
        units = c[key] / c["volume_step"]
        if not math.isclose(units, round(units), rel_tol=0, abs_tol=1e-8):
            raise ValueError(f"{key} no esta alineado con volume_step")
    tick_units = c["tick_size"] / c["point"]
    if not math.isclose(tick_units, round(tick_units), rel_tol=0, abs_tol=1e-8):
        raise ValueError("tick_size debe ser un multiplo entero de point")
    if c.get("commission_type") not in ("cash", "notional_fraction"):
        raise ValueError("Tipo de comision no soportado")
    if c.get("swap_unit") != "account_cash_per_lot":
        raise ValueError("Convertir swap a moneda de cuenta antes de simular")
    for key in ("swap_long", "swap_short"):
        if not isinstance(c.get(key), (int, float)) or not math.isfinite(c[key]):
            raise ValueError(f"Swap invalido: {key}")
    if c.get("price_basis") not in ("mid", "unknown"):
        raise ValueError("Motor actual requiere referencia mid o escenario unknown documentado")
    if c.get("swap_schedule") not in SWAP_SCHEDULES:
        raise ValueError(f"swap_schedule invalido: debe ser uno de {sorted(SWAP_SCHEDULES)}")
    if not isinstance(c.get("triple_weekday"), int) or not 0 <= c["triple_weekday"] <= 6:
        raise ValueError("triple_weekday invalido: debe ser un entero 0 (lunes) a 6 (domingo)")
    try:
        ZoneInfo(c.get("rollover_timezone", ""))
    except (ZoneInfoNotFoundError, KeyError, TypeError, ValueError):
        raise ValueError("rollover_timezone invalida o ausente")
    if not isinstance(c.get("rollover_time"), str) or not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", c["rollover_time"]):
        raise ValueError("rollover_time invalido: se espera HH:MM en 24h")
    timeframes = c.get("timeframes")
    if not isinstance(timeframes, list) or not timeframes or not all(tf in TIMEFRAMES for tf in timeframes):
        raise ValueError("timeframes ausente o con un valor fuera de TIMEFRAMES")
    if len(timeframes) != len(set(timeframes)):
        raise ValueError("timeframes contiene duplicados")
    mode = c.get("margin_calc_mode")
    if mode not in MARGIN_MODES:
        raise ValueError(f"margin_calc_mode invalido: debe ser uno de {sorted(MARGIN_MODES)}")
    expected_modes = {"commodity_cfd": {"cfd_notional"}, "index_cfd": {"cfd_notional"}, "fx": {"forex_base_account", "forex_base_quote"}}
    if c["asset_class"] not in expected_modes or mode not in expected_modes[c["asset_class"]]:
        raise ValueError("margin_calc_mode incompatible con asset_class")
    for key in ("costs_verified", "calendar_verified", "provenance_verified"):
        if type(c.get(key)) is not bool:
            raise ValueError(f"{key} debe ser booleano")
    if not isinstance(c.get("reserves"), list) or not all(isinstance(x, str) and x.strip() for x in c["reserves"]):
        raise ValueError("reserves debe ser una lista de textos no vacios")
    try:
        date.fromisoformat(c.get("as_of", ""))
    except (TypeError, ValueError):
        raise ValueError("as_of debe ser una fecha ISO valida")
    return c
