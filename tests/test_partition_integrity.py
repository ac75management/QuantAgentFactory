"""Integridad IS/OOS verificable sin analizar OOS (qaf.partition + qaf.data.load_is)."""
import json

import numpy as np
import pandas as pd
import pytest

from qaf.data import load_is
from qaf.ingest import import_batch
from qaf.io import read_json
from qaf.partition import seal, seal_entry

CUTOFF = pd.Timestamp('2021-01-01', tz='UTC')


def _frame(start, periods):
    rng = np.random.default_rng(3)
    close = 100 + np.cumsum(rng.normal(0, 1, periods))
    opening = np.r_[close[0], close[:-1]]
    return pd.DataFrame({'time': pd.date_range(start, periods=periods, freq='D', tz='UTC'), 'open': opening,
                         'high': np.maximum(opening, close) + 1, 'low': np.minimum(opening, close) - 1, 'close': close, 'volume': 1.0})


def _partition(tmp_path, is_frame=None, oos_frame=None, cutoff=CUTOFF):
    is_frame = _frame('2020-01-01', 300) if is_frame is None else is_frame
    oos_frame = _frame(cutoff, 60) if oos_frame is None else oos_frame
    folder = tmp_path / 'data/clean/XAUUSD/D1'
    folder.mkdir(parents=True)
    is_frame.to_parquet(folder / 'IS.parquet', index=False)
    oos_frame.to_parquet(folder / 'OOS.parquet', index=False)
    entry = {'symbol': 'XAUUSD', 'timeframe': 'D1', 'is_oos_cutoff_date': str(cutoff), 'rows_is': len(is_frame), 'rows_oos': len(oos_frame)}
    (tmp_path / 'data/clean/manifest.json').write_text(json.dumps({'symbols': [entry]}))
    return folder


def test_unsealed_partition_loads_with_explicit_reserve_and_never_reads_oos(tmp_path):
    folder = _partition(tmp_path)
    (folder / 'OOS.parquet').write_bytes(b'POISON: not parquet')
    df, info = load_is('XAUUSD', 'D1', tmp_path)
    assert len(df) == 300
    assert info['partition_integrity']['status'] == 'UNSEALED'
    assert (folder / 'OOS.parquet').read_bytes().startswith(b'POISON')


def test_seal_records_hashes_schema_and_ranges(tmp_path):
    _partition(tmp_path)
    results = seal(tmp_path)
    assert results == [{'series': 'XAUUSD/D1', 'status': 'SEALED'}]
    entry = read_json(tmp_path / 'data/clean/manifest.json')['symbols'][0]
    for key in ('is_sha256', 'oos_sha256', 'schema', 'is_time_min', 'is_time_max', 'oos_time_min', 'oos_time_max', 'sealed_at'):
        assert entry[key]
    assert pd.Timestamp(entry['is_time_max']) < CUTOFF <= pd.Timestamp(entry['oos_time_min'])
    df, info = load_is('XAUUSD', 'D1', tmp_path)
    assert info['partition_integrity']['status'] == 'SEALED'
    manifest_path = tmp_path / 'data/clean/manifest.json'
    before = (manifest_path.read_bytes(), manifest_path.stat().st_mtime_ns)
    assert seal(tmp_path) == [{'series': 'XAUUSD/D1', 'status': 'ALREADY_SEALED'}]
    assert (manifest_path.read_bytes(), manifest_path.stat().st_mtime_ns) == before


def test_tampered_oos_after_seal_blocks_load(tmp_path):
    folder = _partition(tmp_path)
    seal(tmp_path)
    tampered = _frame(CUTOFF, 60)
    tampered.loc[5, 'close'] += 50
    tampered.to_parquet(folder / 'OOS.parquet', index=False)
    with pytest.raises(ValueError, match='OOS.parquet .*hash sellado'):
        load_is('XAUUSD', 'D1', tmp_path)


def test_tampered_is_after_seal_blocks_load(tmp_path):
    folder = _partition(tmp_path)
    seal(tmp_path)
    changed = _frame('2020-01-01', 300)
    changed.loc[10, 'open'] += 1
    changed.to_parquet(folder / 'IS.parquet', index=False)
    with pytest.raises(ValueError, match='IS.parquet .*hash sellado'):
        load_is('XAUUSD', 'D1', tmp_path)


def test_is_overlapping_its_cutoff_is_rejected(tmp_path):
    _partition(tmp_path, is_frame=_frame('2020-06-01', 300))  # termina despues de 2021-01-01
    with pytest.raises(ValueError, match='solapada'):
        load_is('XAUUSD', 'D1', tmp_path)


@pytest.mark.parametrize('problem,match', [
    ('oos_before_cutoff', 'antes del corte'),
    ('row_mismatch', 'filas'),
    ('schema', 'Esquema'),
    ('oos_duplicates', 'duplicados'),
])
def test_seal_refuses_inconsistent_partitions(tmp_path, problem, match):
    oos = _frame(CUTOFF, 60)
    if problem == 'oos_before_cutoff':
        oos = _frame(CUTOFF - pd.Timedelta(days=5), 60)
    if problem == 'schema':
        oos = oos.drop(columns=['volume'])
    if problem == 'oos_duplicates':
        oos.loc[7, 'time'] = oos.loc[6, 'time']
    _partition(tmp_path, oos_frame=oos)
    if problem == 'row_mismatch':
        manifest = read_json(tmp_path / 'data/clean/manifest.json')
        manifest['symbols'][0]['rows_oos'] = 61
        (tmp_path / 'data/clean/manifest.json').write_text(json.dumps(manifest))
    result = seal(tmp_path)[0]
    assert result['status'] == 'FAILED' and match in result['reason']
    assert 'is_sha256' not in read_json(tmp_path / 'data/clean/manifest.json')['symbols'][0]


def test_ingest_seals_new_partitions(tmp_path):
    raw = tmp_path / 'raw'
    raw.mkdir()
    _frame('2015-01-01', 400).to_parquet(raw / 'XAUUSD_D1.parquet', index=False)
    results = import_batch(raw, tmp_path)
    assert results[0]['status'] == 'IMPORTED'
    entry = read_json(tmp_path / 'data/clean/manifest.json')['symbols'][0]
    assert entry['is_sha256'] and entry['oos_sha256']
    df, info = load_is('XAUUSD', 'D1', tmp_path)
    assert info['partition_integrity']['status'] == 'SEALED'
