"""Sondeo reproducible, solo IS; imprime JSON sin modificar datos ni contratos.

Ejecutar desde la raíz: python -m scripts.audit_is_spotcheck
No certifica calendario, procedencia, costos recientes ni la estrategia completa.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from qaf.signals import rsi


def manual_rsi2(values):
    """Wilder, semilla media de los primeros dos cambios; sin funciones QAF."""
    result = [None] * len(values)
    gains = [max(b - a, 0) for a, b in zip(values, values[1:])]
    losses = [max(a - b, 0) for a, b in zip(values, values[1:])]
    gain, loss = sum(gains[:2]) / 2, sum(losses[:2]) / 2
    for i in range(2, len(values)):
        if i > 2:
            gain = (gain + gains[i - 1]) / 2
            loss = (loss + losses[i - 1]) / 2
        result[i] = 50.0 if gain + loss == 0 else 100 * gain / (gain + loss)
    return result


def main():
    source = Path('data/clean/EURUSD/H1/IS.parquet')
    frame = pd.read_parquet(source)
    sample = frame.iloc[:10]
    values = sample.close.tolist()
    reference = manual_rsi2(values)
    actual = np.asarray(rsi(sample, 2))
    errors = [abs(reference[i] - actual[i]) for i in range(2, 10)]
    if not np.all(np.isfinite(errors)) or max(errors) > 1e-10:
        raise RuntimeError('Divergencia RSI; no emitir entrega aprobada')
    contract_path = Path('config/instruments.json')
    contract = json.loads(contract_path.read_text(encoding='utf-8'))['EURUSD']
    result = {
        'source': str(source),
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'contract_sha256': hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        'rows': len(frame), 'start': str(frame.time.min()), 'end': str(frame.time.max()),
        'duplicate_times': int(frame.time.duplicated().sum()),
        'rsi_method': 'Wilder RSI2; media simple inicial de dos cambios; tolerancia absoluta 1e-10',
        'rsi_rows': [dict(time=str(sample.time.iloc[i]), close=values[i], manual=reference[i],
                          qaf=None if not np.isfinite(actual[i]) else float(actual[i])) for i in range(10)],
        'rsi_max_error': float(max(errors)),
        'spread_stored_units': {k: float(v) for k, v in frame.spread.describe().items()},
        'contract_spread_points': contract['spread_points'],
        'assessment': 'Compartir con reservas; no certifica infraestructura completa',
        'limitations': [
            'Solo diez barras iniciales para RSI; sin selección por rentabilidad.',
            'Spread de IS antiguo, no últimos seis meses; unidades y semántica sin verificar.',
            'No permite calibrar slippage sin fills ni confirmar costos actuales.',
            'Sin acceso a OOS, bróker, ni adopción de evidencia de hipótesis.',
            'Comparativa de operaciones separada en data/QUALITY_AUDIT.md; no reproducida por este script.'
        ]
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
