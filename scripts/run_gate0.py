"""Run current quality checks on IS only; never rewrite partitions or old reports."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from qaf.io import ROOT,read_json,write_json
from qaf.data import load_is,inspect_frame

def main():
    rows=[]
    for symbol,c in read_json(ROOT/'config/instruments.json').items():
        if c.get('status')!='research':continue
        for tf in c['timeframes']:
            try:
                df,info=load_is(symbol,tf)
                rows.append({'symbol':symbol,'timeframe':tf,'dataset':info,**inspect_frame(df,tf,{'symbol':symbol,**c})})
            except FileNotFoundError:
                rows.append({'symbol':symbol,'timeframe':tf,'status':'MISSING_DATA'})
    path=ROOT/'reports/factory/quality.json';write_json(path,rows)
    print(path)
    return 2 if any(x['status']=='FAIL' for x in rows) else 0
if __name__=='__main__':raise SystemExit(main())
