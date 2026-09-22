import math
import re

TIMEFRAMES = {"H1": 60, "H4": 240, "D1": 1440}
FAMILIES = {"streak_reversal", "trend_cross", "channel_breakout"}


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
    return spec


def validate_instrument(c):
    for key in ("point", "tick_size", "tick_value", "contract_size", "volume_min", "volume_step", "volume_max", "max_leverage", "currency_to_account"):
        positive(c.get(key), key)
    for key in ("spread_points", "slippage_points_per_side", "commission_per_side"):
        positive(c.get(key), key, zero=True)
    if c["volume_max"] < c["volume_min"]:
        raise ValueError("volume_max < volume_min")
    if c.get("commission_type") not in ("cash", "notional_fraction"):
        raise ValueError("Tipo de comision no soportado")
    if c.get("swap_unit") != "account_cash_per_lot":
        raise ValueError("Convertir swap a moneda de cuenta antes de simular")
    for key in ("swap_long", "swap_short"):
        if not isinstance(c.get(key), (int, float)) or not math.isfinite(c[key]):
            raise ValueError(f"Swap invalido: {key}")
    if c.get("price_basis") not in ("mid", "unknown"):
        raise ValueError("Motor actual requiere referencia mid o escenario unknown documentado")
    return c
