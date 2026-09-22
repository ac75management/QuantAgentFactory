"""Integridad de la particion IS/OOS sin analizar OOS.

Sello (una vez por particion, `python -m qaf.partition seal`): registra en
data/clean/manifest.json el sha256 de IS.parquet y OOS.parquet, el esquema y el
rango temporal leidos del footer parquet, y valida filas, esquema y corte. De OOS
se lee solo el footer y la columna `time` (para duplicados/orden); nunca precios.

Es un sello "trust on first use": prueba que los archivos no cambian desde el
sello, no que eran correctos antes. qaf.ingest sella en el momento de crear la
particion, que es el punto mas fuerte posible. Una particion ya sellada no se
vuelve a sellar: si hay que reconstruirla, se quitan sus campos de sello a mano,
con registro en PROJECT_STATE.md.

Verificacion (cada `qaf.cli run`, via qaf.data.load_is): hash de IS y de OOS
contra el sello. Sin sello -> estado UNSEALED (reserva: investigacion IS
permitida, validacion final bloqueada). Hash distinto -> error, la serie queda
no disponible.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq
from .io import ROOT, file_hash, read_json, write_json


def _time_range(path):
    meta = pq.read_metadata(path)
    names = [meta.schema.column(j).name for j in range(meta.num_columns)]
    if "time" not in names:
        raise ValueError(f"{path}: sin columna time")
    index = names.index("time")
    lows, highs = [], []
    for group in range(meta.num_row_groups):
        stats = meta.row_group(group).column(index).statistics
        if stats is None or not stats.has_min_max:
            raise ValueError(f"{path}: el footer parquet no trae min/max de time")
        lows.append(pd.Timestamp(stats.min))
        highs.append(pd.Timestamp(stats.max))
    if not lows:
        raise ValueError(f"{path}: archivo sin filas")
    low, high = min(lows), max(highs)
    if low.tzinfo is None or high.tzinfo is None:
        raise ValueError(f"{path}: time sin zona horaria")
    return meta.num_rows, low, high


def describe(path):
    rows, low, high = _time_range(path)
    schema = [f"{field.name}:{field.type}" for field in pq.read_schema(path)]
    return {"rows": rows, "schema": schema, "time_min": str(low), "time_max": str(high), "sha256": file_hash(path)}


def seal_entry(entry, root=ROOT):
    folder = Path(root) / "data/clean" / entry["symbol"] / entry["timeframe"]
    is_info, oos_info = describe(folder / "IS.parquet"), describe(folder / "OOS.parquet")
    oos_time = pq.read_table(folder / "OOS.parquet", columns=["time"]).column("time").to_pandas()
    cutoff = pd.Timestamp(entry["is_oos_cutoff_date"])
    problems = []
    if is_info["rows"] != entry["rows_is"]:
        problems.append(f"IS tiene {is_info['rows']} filas, manifest {entry['rows_is']}")
    if oos_info["rows"] != entry["rows_oos"]:
        problems.append(f"OOS tiene {oos_info['rows']} filas, manifest {entry['rows_oos']}")
    if is_info["schema"] != oos_info["schema"]:
        problems.append("Esquema IS distinto de OOS")
    if not pd.Timestamp(is_info["time_max"]) < cutoff:
        problems.append(f"IS termina en {is_info['time_max']}, no antes del corte {cutoff}")
    if not pd.Timestamp(oos_info["time_min"]) >= cutoff:
        problems.append(f"OOS empieza en {oos_info['time_min']}, antes del corte {cutoff}")
    if oos_time.duplicated().any() or not oos_time.is_monotonic_increasing:
        problems.append("OOS con timestamps duplicados o desordenados")
    if problems:
        raise ValueError(f"{entry['symbol']}/{entry['timeframe']}: " + "; ".join(problems))
    entry.update(is_sha256=is_info["sha256"], oos_sha256=oos_info["sha256"], schema=is_info["schema"],
                 is_time_min=is_info["time_min"], is_time_max=is_info["time_max"],
                 oos_time_min=oos_info["time_min"], oos_time_max=oos_info["time_max"],
                 sealed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 seal_method="TOFU: sha256 + footer parquet; de OOS solo footer y columna time")
    return entry


def seal(root=ROOT):
    path = Path(root) / "data/clean/manifest.json"
    manifest = read_json(path)
    results = []
    for entry in manifest["symbols"]:
        label = f"{entry.get('symbol')}/{entry.get('timeframe')}"
        if entry.get("is_sha256"):
            results.append({"series": label, "status": "ALREADY_SEALED"})
            continue
        try:
            seal_entry(entry, root)
            results.append({"series": label, "status": "SEALED"})
        except (ValueError, KeyError, OSError) as error:
            results.append({"series": label, "status": "FAILED", "reason": str(error)})
    if any(r["status"] == "SEALED" for r in results):
        write_json(path, manifest)
    return results


def verify(entry, is_path, oos_path):
    if not entry.get("is_sha256"):
        return {"status": "UNSEALED", "detail": "Sin sello en el manifest: integridad de OOS no verificable. Ejecutar python -m qaf.partition seal."}
    if not entry.get("oos_sha256"):
        raise ValueError(f"Sello incompleto para {entry['symbol']}/{entry['timeframe']}: falta oos_sha256")
    if file_hash(is_path) != entry["is_sha256"]:
        raise ValueError(f"IS.parquet de {entry['symbol']}/{entry['timeframe']} no coincide con el hash sellado")
    if file_hash(oos_path) != entry["oos_sha256"]:
        raise ValueError(f"OOS.parquet de {entry['symbol']}/{entry['timeframe']} no coincide con el hash sellado: la reserva pudo modificarse")
    return {"status": "SEALED", "sealed_at": entry.get("sealed_at"), "is_sha256": entry["is_sha256"], "oos_sha256": entry["oos_sha256"]}


def main():
    parser = argparse.ArgumentParser(description="Sello de integridad de particiones IS/OOS (no analiza OOS)")
    parser.add_argument("command", choices=["seal"])
    parser.parse_args()
    results = seal()
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 1 if any(r["status"] == "FAILED" for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
