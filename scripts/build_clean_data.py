import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse
import json
from qaf.ingest import import_batch
from qaf.io import ROOT
if __name__=='__main__':
    p=argparse.ArgumentParser(description='Importar particiones nuevas; preservar IS/OOS existentes')
    p.add_argument('--raw-dir',type=Path,default=ROOT/'data/raw/darwinex')
    rows=import_batch(p.parse_args().raw_dir)
    print(json.dumps(rows,indent=2))
    raise SystemExit(2 if any(x['status'] in ('INVALID_RAW','INSUFFICIENT_BEFORE_FIXED_CUTOFF') for x in rows) else 0)
