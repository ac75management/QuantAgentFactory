"""
Corre el Gate 0 de calidad de datos (.claude/skills/data-quality-check/SKILL.md)
sobre cada IS.parquet en data/clean/, y actualiza data/clean/manifest.json con
el veredicto. NO interpola ni corrige nada -- solo evalua y reporta.

Uso:
    python scripts/run_gate0.py

Entrada:
    data/clean/<SYMBOL>/<TF>/IS.parquet
    docs/universe.md (cost_key por simbolo)
    docs/cost_model.md (status del cost_key: CONFIRMED | SIN_CONFIRMAR)

Salida:
    reports/_data_quality/<SYMBOL>_<TF>.md
    data/clean/manifest.json actualizado (agrega verdict_gate0 + notas por entrada)
    Resumen en consola: conteo APTO / APTO_CON_RESERVAS / RECHAZADO
"""

import json
import re
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("FALTA pandas/pyarrow. Instala con: pip install pandas pyarrow")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
CLEAN_DIR = ROOT / "data" / "clean"
MANIFEST_PATH = CLEAN_DIR / "manifest.json"
UNIVERSE_PATH = ROOT / "docs" / "universe.md"
COST_MODEL_PATH = ROOT / "docs" / "cost_model.md"
REPORTS_DIR = ROOT / "reports" / "_data_quality"

TF_EXPECTED_DELTA = {
    "D1": pd.Timedelta(days=1),
    "H4": pd.Timedelta(hours=4),
}
MIN_ROWS = 30

UNIVERSE_ROW_RE = re.compile(
    r"^\|\s*(?P<alias>[^|]+?)\s*\|\s*(?P<symbol_mt5>[^|]+?)\s*\|\s*(?P<type>[^|]+?)\s*\|"
    r"\s*(?P<tfs>[^|]+?)\s*\|\s*(?P<cost_key>[^|]+?)\s*\|\s*(?P<status>[^|]+?)\s*\|\s*$"
)


def load_universe():
    """alias -> {cost_key, status} desde la tabla fija de docs/universe.md."""
    if not UNIVERSE_PATH.exists():
        return {}
    text = UNIVERSE_PATH.read_text(encoding="utf-8")
    out = {}
    for line in text.splitlines():
        m = UNIVERSE_ROW_RE.match(line.strip())
        if not m:
            continue
        d = m.groupdict()
        alias = d["alias"].strip()
        if alias.lower() == "alias" or set(alias) <= {"-"}:
            continue
        out[alias] = {"cost_key": d["cost_key"].strip(), "status": d["status"].strip()}
    return out


def load_cost_key_status():
    """cost_key -> status, leido de la tabla 'Por cost_key' de docs/cost_model.md."""
    if not COST_MODEL_PATH.exists():
        return {}
    text = COST_MODEL_PATH.read_text(encoding="utf-8")
    status_by_key = {}
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("| cost_key"):
            in_table = True
            continue
        if in_table:
            if not stripped.startswith("|"):
                if status_by_key:
                    break
                continue
            if set(stripped.replace("|", "").strip()) <= {"-", " "}:
                continue
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cells) >= 2:
                status_by_key[cells[0]] = cells[-1]
    return status_by_key


def load_symbol_cost_status():
    """alias -> status, leido de la tabla 'Por símbolo' de docs/cost_model.md.
    Mas preciso que el cost_key generico -- un simbolo puede estar CONFIRMED
    ahi aunque su cost_key generico (compartido con otros simbolos) siga
    SIN_CONFIRMAR."""
    if not COST_MODEL_PATH.exists():
        return {}
    text = COST_MODEL_PATH.read_text(encoding="utf-8")
    status_by_alias = {}
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("| alias | symbol_mt5 | commission_per_side"):
            in_table = True
            continue
        if in_table:
            if not stripped.startswith("|"):
                if status_by_alias:
                    break
                continue
            if set(stripped.replace("|", "").strip()) <= {"-", " "}:
                continue
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cells) >= 7:
                status_by_alias[cells[0]] = cells[-1].replace("*", "").strip()
    return status_by_alias


def check_structural(df):
    issues = []
    required = ["time", "open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        issues.append(f"Faltan columnas: {missing}")
        return issues
    if df[required].isna().any().any():
        issues.append("Hay valores NaN en OHLC")
    numeric_ok = df[required[1:]].apply(
        lambda column: pd.to_numeric(column, errors="coerce").notna().all()
    ).all()
    if not numeric_ok:
        issues.append("Hay valores no numericos en OHLC")
    if not (df["high"] >= df["low"]).all():
        issues.append("Hay barras con high < low")
    if not df["time"].is_monotonic_increasing:
        issues.append("Timestamps no estan ordenados ascendentemente")
    dup = df["time"].duplicated().sum()
    if dup:
        issues.append(f"{dup} timestamps duplicados")
    return issues


def check_timezone(df):
    tz = df["time"].dt.tz
    if tz is None:
        return ["Columna 'time' sin timezone explicita (deberia ser UTC)"]
    if str(tz) != "UTC":
        return [f"Timezone es '{tz}', se esperaba UTC"]
    return []


def check_ohlc_consistency(df):
    issues = []
    bad_high = (df["high"] < df[["open", "close"]].max(axis=1)).sum()
    bad_low = (df["low"] > df[["open", "close"]].min(axis=1)).sum()
    if bad_high:
        issues.append(f"{bad_high} barras con high < max(open, close)")
    if bad_low:
        issues.append(f"{bad_low} barras con low > min(open, close)")
    return issues


def check_gaps(df, tf):
    expected = TF_EXPECTED_DELTA.get(tf)
    if expected is None or len(df) < 2:
        return [], 0, 0
    deltas = df["time"].diff()
    threshold = expected * 1.5
    weekend_like = 0
    feed_holes = 0
    for i in range(1, len(df)):
        gap = deltas.iloc[i]
        if pd.isna(gap) or gap <= threshold:
            continue
        prev_time = df["time"].iloc[i - 1]
        # Fin de semana / feriado corto esperado: el hueco empieza viernes/sabado
        # y no supera ~3 dias (cubre viernes tarde -> lunes en CFDs 24/5).
        if prev_time.weekday() >= 4 and gap <= pd.Timedelta(days=3, hours=6):
            weekend_like += 1
        else:
            feed_holes += 1
    notes = []
    if weekend_like:
        notes.append(f"{weekend_like} hueco(s) clasificados como fin de semana/feriado (esperado)")
    if feed_holes:
        notes.append(f"{feed_holes} hueco(s) NO explicados por fin de semana (posible feed hole)")
    return notes, weekend_like, feed_holes


def evaluate(symbol, tf, is_path, universe, cost_status, symbol_cost_status):
    df = pd.read_parquet(is_path)
    n = len(df)

    structural_issues = check_structural(df)
    tz_issues = [] if structural_issues else check_timezone(df)
    ohlc_issues = [] if structural_issues else check_ohlc_consistency(df)
    gap_notes, weekend_gaps, feed_holes = ([], 0, 0) if structural_issues else check_gaps(df, tf)

    coverage_days = (df["time"].max() - df["time"].min()).days if n and not structural_issues else 0

    alias_info = universe.get(symbol, {})
    cost_key = alias_info.get("cost_key")
    # Override por simbolo (tabla "Por simbolo") tiene prioridad sobre el cost_key
    # generico compartido -- un simbolo puede estar CONFIRMED sin que el resto de
    # simbolos de su mismo cost_key lo esten.
    if symbol in symbol_cost_status:
        cost_conf_status = symbol_cost_status[symbol]
    else:
        cost_conf_status = cost_status.get(cost_key, "DESCONOCIDO") if cost_key else "DESCONOCIDO"

    hard_failures = list(structural_issues) + list(ohlc_issues)
    if n < MIN_ROWS:
        hard_failures.append(f"Solo {n} barras en IS, insuficiente para AED/backtest (minimo {MIN_ROWS})")

    reserve_reasons = list(tz_issues)
    if feed_holes > 0:
        reserve_reasons.append(f"{feed_holes} gap(s) no explicados por fin de semana")
    reserve_reasons.append(
        "El spread historico NO viene en las barras OHLC exportadas -- todo backtest debe usar "
        "docs/cost_model.md, nunca asumir spread cero."
    )
    if cost_conf_status != "CONFIRMED":
        reserve_reasons.append(
            f"cost_key '{cost_key}' tiene status='{cost_conf_status}' en docs/cost_model.md (no CONFIRMED) "
            f"-- techo de veredicto: APTO_CON_RESERVAS"
        )

    manual_checks = [
        "MANUAL_PENDIENTE: outliers de rango y justificacion por evento/regimen",
        "MANUAL_PENDIENTE: sesion de trading y alineacion con el subyacente",
        "MANUAL_PENDIENTE: segunda fuente y estabilidad as-of del historico",
        "MANUAL_PENDIENTE: rollover/ajuste de contrato si aplica",
    ]

    if hard_failures:
        verdict = "RECHAZADO"
    elif cost_conf_status != "CONFIRMED" or feed_holes > 0 or tz_issues or manual_checks:
        verdict = "APTO_CON_RESERVAS"
    else:
        verdict = "APTO"

    return {
        "symbol": symbol,
        "timeframe": tf,
        "rows": n,
        "date_min": str(df["time"].min()) if n else None,
        "date_max": str(df["time"].max()) if n else None,
        "coverage_days": coverage_days,
        "hard_failures": hard_failures,
        "reserve_reasons": reserve_reasons,
        "manual_checks": manual_checks,
        "gap_notes": gap_notes,
        "cost_key": cost_key,
        "cost_key_status": cost_conf_status,
        "verdict": verdict,
    }


def write_report_md(report):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"{report['symbol']}_{report['timeframe']}.md"
    lines = [
        f"# Gate 0 — {report['symbol']} [{report['timeframe']}]",
        "",
        f"- Filas (IS): {report['rows']}",
        f"- Rango de fechas: {report['date_min']} -> {report['date_max']} ({report['coverage_days']} dias)",
        f"- cost_key: {report['cost_key']} (status: {report['cost_key_status']})",
        "",
        "## Fallos duros" if report["hard_failures"] else "## Fallos duros: ninguno",
    ]
    for f in report["hard_failures"]:
        lines.append(f"- {f}")
    lines.append("")
    lines.append("## Reservas" if report["reserve_reasons"] else "## Reservas: ninguna")
    for r in report["reserve_reasons"]:
        lines.append(f"- {r}")
    if report["gap_notes"]:
        lines.append("")
        lines.append("## Huecos detectados")
        for g in report["gap_notes"]:
            lines.append(f"- {g}")
    lines.append("")
    lines.append("## Controles manuales pendientes")
    for check in report["manual_checks"]:
        lines.append(f"- {check}")
    lines.append("")
    lines.append(f"## VEREDICTO: {report['verdict']}")
    lines.append("")
    lines.append("No se interpolo ningun precio ni se corrigio ningun outlier en este chequeo.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def update_manifest(reports_by_key):
    if not MANIFEST_PATH.exists():
        print(f"AVISO: no existe {MANIFEST_PATH}, no se actualiza (¿corriste build_clean_data.py?)")
        return
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for entry in manifest.get("symbols", []):
        key = (entry["symbol"], entry["timeframe"])
        report = reports_by_key.get(key)
        if report:
            entry["verdict_gate0"] = report["verdict"]
            entry["gate0_notes"] = report["hard_failures"] + report["reserve_reasons"]
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    universe = load_universe()
    cost_status = load_cost_key_status()
    symbol_cost_status = load_symbol_cost_status()

    is_files = sorted(CLEAN_DIR.glob("*/*/IS.parquet"))
    if not is_files:
        print(f"No hay archivos IS.parquet en {CLEAN_DIR}. Corre primero build_clean_data.py")
        sys.exit(1)

    reports_by_key = {}
    counts = {"APTO": 0, "APTO_CON_RESERVAS": 0, "RECHAZADO": 0}
    for is_path in is_files:
        tf = is_path.parent.name
        symbol = is_path.parent.parent.name
        report = evaluate(symbol, tf, is_path, universe, cost_status, symbol_cost_status)
        path = write_report_md(report)
        reports_by_key[(symbol, tf)] = report
        counts[report["verdict"]] += 1
        print(f"{report['verdict']:20s} {symbol} [{tf}] -> {path.relative_to(ROOT)}")

    update_manifest(reports_by_key)

    print("\n--- Resumen Gate 0 ---")
    for k, v in counts.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
