from pathlib import Path
import numpy as np
import pandas as pd
from .contracts import TIMEFRAMES
from .io import ROOT, file_hash, read_json


def inspect_frame(df, timeframe, metadata=None):
    metadata = metadata or {}
    checks = []
    def add(name, status, detail):
        checks.append({"check": name, "status": status, "detail": detail})
    required = ["time", "open", "high", "low", "close"]
    missing = sorted(set(required) - set(df.columns))
    add("columns", "FAIL" if missing else "PASS", missing)
    if missing:
        return {"status": "FAIL", "checks": checks, "rows": len(df)}
    numeric = df[required[1:]].apply(pd.to_numeric, errors="coerce")
    finite = bool(np.isfinite(numeric.to_numpy(dtype=float)).all())
    add("finite_prices", "PASS" if finite else "FAIL", "OHLC numerico y finito")
    valid_time = pd.api.types.is_datetime64_any_dtype(df.time)
    tz = getattr(df.time.dtype, "tz", None)
    valid_time = valid_time and tz is not None and not df.time.isna().any()
    add("utc_timestamp", "PASS" if valid_time and str(tz) == "UTC" else "FAIL", str(df.time.dtype))
    unique = not df.time.duplicated().any() and df.time.is_monotonic_increasing
    add("unique_sorted", "PASS" if unique else "FAIL", "Sin ordenar/eliminar barras silenciosamente")
    consistent = finite and bool(((numeric.high >= numeric[["open", "close"]].max(axis=1)) & (numeric.low <= numeric[["open", "close"]].min(axis=1)) & (numeric.high >= numeric.low)).all())
    add("ohlc", "PASS" if consistent else "FAIL", "Extremos contienen open/close")
    add("minimum_rows", "PASS" if len(df) >= 60 else "FAIL", len(df))
    if valid_time and unique and len(df) > 1:
        delta = df.time.diff().dt.total_seconds().div(60)
        expected = TIMEFRAMES[timeframe]
        short = int((delta.dropna() < expected * 0.5).sum())
        add("frequency", "FAIL" if short else "PASS", {"median_minutes": float(delta.median()), "too_short": short})
        gaps = int((delta > expected * 1.5).sum())
        # Without an instrument calendar, never infer that every Friday gap is harmless.
        add("session_calendar", "RESERVE" if gaps or not metadata.get("calendar_verified") else "PASS", {"long_intervals": gaps, "calendar_verified": bool(metadata.get("calendar_verified"))})
        if metadata.get("symbol") == "EURUSD" and df.time.min() < pd.Timestamp("1999-01-01", tz="UTC"):
            add("pre_euro_provenance", "FAIL", "Historico anterior a 1999 necesita procedencia explicita; no se recorta automaticamente")
    add("price_basis", "PASS" if metadata.get("price_basis") == "mid" else "RESERVE", metadata.get("price_basis", "unknown"))
    add("source_provenance", "PASS" if metadata.get("provenance_verified") else "RESERVE", "Proveedor, continuidad y ajustes pendientes" if not metadata.get("provenance_verified") else "Verificado")
    status = "FAIL" if any(c["status"] == "FAIL" for c in checks) else ("RESERVE" if any(c["status"] == "RESERVE" for c in checks) else "PASS")
    return {"status": status, "checks": checks, "rows": len(df)}


def load_is(symbol, timeframe, root=ROOT):
    # Deliberately no generic arbitrary path or partition argument in the data API.
    if not symbol.replace("_", "").isalnum() or timeframe not in TIMEFRAMES:
        raise ValueError("Identificador de datos invalido")
    path = Path(root) / "data/clean" / symbol / timeframe / "IS.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Sin datos IS: {symbol}/{timeframe}")
    df = pd.read_parquet(path)
    info = {"path": str(path.relative_to(root)), "sha256": file_hash(path)}
    manifest = Path(root)/'data/clean/manifest.json'
    if manifest.exists():
        entries = read_json(manifest).get('symbols',[])
        cutoffs = [pd.Timestamp(x['is_oos_cutoff_date']) for x in entries if x['symbol']==symbol and x.get('is_oos_cutoff_date')]
        if cutoffs:
            cutoff=min(cutoffs)
            count=len(df)
            df=df.loc[df.time < cutoff].reset_index(drop=True)
            info.update(effective_exclusive_cutoff=str(cutoff),rows_removed_to_protect_other_timeframes=count-len(df))
    return df, info
