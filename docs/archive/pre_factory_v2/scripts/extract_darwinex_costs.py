"""
Lee docs/universe.md (filas status=active), consulta mt5.symbol_info() /
mt5.symbol_info_tick() para cada symbol_mt5, y guarda un snapshot de costos
reales de la cuenta MT5 conectada.

Requiere terminal Darwinex MT5 abierto y logueado en esta misma maquina.

NO inventa comision: symbol_info() de MT5 no expone la comision real de la
cuenta (depende del tipo de cuenta) -- se guarda commission_source=manual/web
y hay que confirmarla a mano en docs/cost_model.md (tablas "Por cost_key" /
"Por simbolo"), consultando el tipo de cuenta en Darwinex.

Uso:
    python scripts/extract_darwinex_costs.py

Salida:
    docs/cost_snapshots/<YYYYMMDD_HHMM>.json
    Reemplaza la seccion "## Seccion LIVE" de docs/cost_model.md (todo lo que
    esta ANTES de ese encabezado no se toca).
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import MetaTrader5 as mt5
except ImportError:
    print("FALTA la libreria MetaTrader5. Instala con: pip install MetaTrader5")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
UNIVERSE_PATH = ROOT / "docs" / "universe.md"
COST_MODEL_PATH = ROOT / "docs" / "cost_model.md"
SNAPSHOTS_DIR = ROOT / "docs" / "cost_snapshots"

LIVE_HEADING = "## Sección LIVE (autogenerada por scripts/extract_darwinex_costs.py — no editar a mano)"

UNIVERSE_ROW_RE = re.compile(
    r"^\|\s*(?P<alias>[^|]+?)\s*\|\s*(?P<symbol_mt5>[^|]+?)\s*\|\s*(?P<type>[^|]+?)\s*\|"
    r"\s*(?P<tfs>[^|]+?)\s*\|\s*(?P<cost_key>[^|]+?)\s*\|\s*(?P<status>[^|]+?)\s*\|\s*$"
)


def read_active_symbols():
    """Parsea la tabla fija de docs/universe.md y devuelve las filas status=active."""
    if not UNIVERSE_PATH.exists():
        print(f"No existe {UNIVERSE_PATH}")
        return []
    text = UNIVERSE_PATH.read_text(encoding="utf-8")
    rows = []
    for line in text.splitlines():
        m = UNIVERSE_ROW_RE.match(line.strip())
        if not m:
            continue
        d = m.groupdict()
        alias = d["alias"].strip()
        if alias.lower() == "alias" or set(alias) <= {"-"}:
            continue
        if d["status"].strip().lower() == "active":
            rows.append({k: v.strip() for k, v in d.items()})
    return rows


def snapshot_symbol(row):
    name = row["symbol_mt5"]
    if not mt5.symbol_select(name, True):
        print(f"FAIL {row['alias']}: no se pudo seleccionar '{name}' en Market Watch")
        return None

    info = mt5.symbol_info(name)
    if info is None:
        print(f"FAIL {row['alias']}: symbol_info() vacio para '{name}'")
        return None

    tick = mt5.symbol_info_tick(name)

    data = {
        "alias": row["alias"],
        "symbol_mt5": name,
        "cost_key": row["cost_key"],
        "spread_points": info.spread,
        "point": info.point,
        "digits": info.digits,
        "swap_long": info.swap_long,
        "swap_short": info.swap_short,
        "swap_rollover3days": info.swap_rollover3days,
        "trade_contract_size": info.trade_contract_size,
        "trade_tick_value": info.trade_tick_value,
        "trade_tick_size": info.trade_tick_size,
        "volume_min": info.volume_min,
        "bid": tick.bid if tick else None,
        "ask": tick.ask if tick else None,
        "commission_per_side": None,
        "commission_source": "manual/web",
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    print(
        f"OK   {row['alias']}: spread={data['spread_points']}pt "
        f"swap_long={data['swap_long']} swap_short={data['swap_short']} "
        f"swap_rollover3days={data['swap_rollover3days']}"
    )
    return data


def render_live_section(snapshots, snapshot_rel_path):
    lines = [
        LIVE_HEADING,
        "",
        f"Último snapshot: `{snapshot_rel_path}`, capturado {datetime.now(timezone.utc).isoformat()}.",
        "",
        "| alias | symbol_mt5 | spread_points | swap_long | swap_short | swap_rollover3days | "
        "contract_size | tick_value | tick_size | commission_source |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in snapshots:
        lines.append(
            f"| {s['alias']} | {s['symbol_mt5']} | {s['spread_points']} | {s['swap_long']} | "
            f"{s['swap_short']} | {s['swap_rollover3days']} | {s['trade_contract_size']} | "
            f"{s['trade_tick_value']} | {s['trade_tick_size']} | {s['commission_source']} |"
        )
    lines.append("")
    lines.append(
        "Esta tabla confirma spread/swap/tamaño de contrato con la cuenta real. "
        "`commission_per_side` sigue sin confirmar aquí — MT5 no la expone vía `symbol_info()` "
        "para cuentas Darwinex. Rellenarla a mano en las tablas \"Por cost_key\" / \"Por símbolo\" "
        "de este documento, consultando el tipo de cuenta real, y marcar `status=CONFIRMED` ahí "
        "(esta sección LIVE no se toca a mano, se regenera corriendo el script de nuevo)."
    )
    lines.append(
        "`tick_size` es `trade_tick_size`/`point` de MT5 (el movimiento mínimo de precio). "
        "P&L en moneda de cuenta = (precio_salida - precio_entrada) / tick_size * tick_value * lotes. "
        "No asumir tick_size=1 -- varía por símbolo (SP500=0.1, EURUSD=0.00001, XAUUSD=0.01, ...)."
    )
    return "\n".join(lines) + "\n"


def update_cost_model(live_section_text):
    if not COST_MODEL_PATH.exists():
        print(f"AVISO: no existe {COST_MODEL_PATH}, no se actualiza.")
        return
    text = COST_MODEL_PATH.read_text(encoding="utf-8")
    idx = text.find(LIVE_HEADING)
    if idx == -1:
        print(f"AVISO: no encontre el encabezado '{LIVE_HEADING}' en {COST_MODEL_PATH}. Anexando al final.")
        new_text = text.rstrip() + "\n\n" + live_section_text
    else:
        new_text = text[:idx] + live_section_text
    COST_MODEL_PATH.write_text(new_text, encoding="utf-8")


def main():
    if not mt5.initialize(timeout=10_000):
        print(f"FAIL: no se pudo conectar al terminal MT5 en 10s (¿esta abierto y logueado?). Error: {mt5.last_error()}")
        sys.exit(1)

    active_rows = read_active_symbols()
    if not active_rows:
        print(f"No hay filas status=active en {UNIVERSE_PATH}")
        mt5.shutdown()
        sys.exit(1)

    snapshots = []
    for row in active_rows:
        s = snapshot_symbol(row)
        if s:
            snapshots.append(s)

    mt5.shutdown()

    if not snapshots:
        print("Ningun simbolo devolvio datos. No se actualiza cost_model.md.")
        sys.exit(2)

    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    snapshot_path = SNAPSHOTS_DIR / f"{ts}.json"
    snapshot_path.write_text(json.dumps(snapshots, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSnapshot escrito en {snapshot_path}")

    live_text = render_live_section(snapshots, snapshot_path.relative_to(ROOT).as_posix())
    update_cost_model(live_text)
    print("docs/cost_model.md actualizado (seccion LIVE).")

    print(f"\n{len(snapshots)}/{len(active_rows)} simbolos capturados correctamente.")
    sys.exit(0 if len(snapshots) == len(active_rows) else 2)


if __name__ == "__main__":
    main()
