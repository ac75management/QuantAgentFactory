"""Immutable ingestion: existing partitions are never overwritten."""
from pathlib import Path
import re
import pandas as pd
from .io import ROOT, read_json, write_json, file_hash
from .partition import seal_entry


def normalize(df):
    df = df.copy()
    if 'time' not in df: raise ValueError('Falta time')
    numeric = pd.api.types.is_numeric_dtype(df.time)
    df['time'] = pd.to_datetime(df.time, utc=True, **({'unit':'s'} if numeric else {}))
    if 'volume' not in df:
        df['volume'] = df.get('tick_volume', df.get('real_volume', pd.NA))
    return df.reset_index(drop=True)


def import_batch(raw_dir, root=ROOT):
    root, raw_dir = Path(root), Path(raw_dir)
    manifest_path=root/'data/clean/manifest.json'
    manifest=read_json(manifest_path) if manifest_path.exists() else {'symbols':[]}
    entries=manifest['symbols'];cutoffs={}
    for e in entries:
        if e.get('is_oos_cutoff_date'):
            symbol=e['symbol']; value=pd.Timestamp(e['is_oos_cutoff_date'])
            cutoffs[symbol]=min(cutoffs.get(symbol,value),value)
    pending=[];results=[]
    for path in sorted(raw_dir.glob('*.parquet')):
        match=re.fullmatch(r'([A-Za-z0-9_]+)_(H1|H4|D1)\.parquet',path.name)
        if not match:continue
        symbol,tf=match.groups(); out=root/'data/clean'/symbol/tf
        if out.exists() and any(out.iterdir()):
            results.append({'symbol':symbol,'timeframe':tf,'status':'EXISTS_PRESERVED'});continue
        df=normalize(pd.read_parquet(path))
        if len(df)<100 or df.time.isna().any() or df.time.duplicated().any() or not df.time.is_monotonic_increasing:
            results.append({'symbol':symbol,'timeframe':tf,'status':'INVALID_RAW'});continue
        pending.append((symbol,tf,path,df))
    new_cutoffs={}
    for symbol,tf,path,df in pending:
        if symbol not in cutoffs:
            value=df.time.iloc[int(len(df)*.7)]
            new_cutoffs[symbol]=min(new_cutoffs.get(symbol,value),value)
    cutoffs.update(new_cutoffs)
    for symbol,tf,path,df in pending:
        cutoff=cutoffs[symbol]; ins=df.loc[df.time<cutoff]; oos=df.loc[df.time>=cutoff]
        if len(ins)<60 or len(oos)==0:
            results.append({'symbol':symbol,'timeframe':tf,'status':'INSUFFICIENT_BEFORE_FIXED_CUTOFF'});continue
        out=root/'data/clean'/symbol/tf
        out.mkdir(parents=True,exist_ok=True)
        # Failed partial writes prevent a subsequent overwrite.
        with (out/'import.lock').open('x') as lock:lock.write(str(path))
        ins.to_parquet(out/'IS.parquet',index=False)
        oos.to_parquet(out/'OOS.parquet',index=False)
        entry={'symbol':symbol,'timeframe':tf,'raw_file':str(path),'raw_sha256':file_hash(path),'is_oos_cutoff_date':str(cutoff),'rows_is':len(ins),'rows_oos':len(oos),'price_basis':'unknown','source':'Export; contract and provenance pending','verdict_gate0':'NOT_RUN'}
        # Sello en el momento de crear la particion: el punto mas fuerte de "trust on first use".
        entries.append(seal_entry(entry,root))
        manifest.update(generated_from='qaf.ingest',note='Fixed cutoff per symbol. Existing partitions immutable. OOS generated, not analyzed.')
        write_json(manifest_path,manifest)
        results.append({'symbol':symbol,'timeframe':tf,'status':'IMPORTED','rows_is':len(ins)})
    return results
