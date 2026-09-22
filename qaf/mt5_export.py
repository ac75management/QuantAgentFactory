"""Explicit read-only extraction; never imported by the strategy runner."""
import argparse
from datetime import datetime,timezone
from .io import ROOT,read_json,write_json
from .contracts import TIMEFRAMES

FIELDS=('point','digits','spread','spread_float','swap_mode','swap_long','swap_short','swap_rollover3days','trade_contract_size','trade_tick_size','trade_tick_value','trade_tick_value_profit','trade_tick_value_loss','trade_calc_mode','volume_min','volume_step','volume_max','volume_limit','currency_base','currency_profit','currency_margin','trade_stops_level','trade_freeze_level','margin_initial','margin_maintenance')


def main(kind):
    p=argparse.ArgumentParser(description='Extracción explícita MT5 de solo lectura')
    p.add_argument('--connect-mt5',action='store_true')
    p.add_argument('--count',type=int,default=100000)
    args=p.parse_args()
    if not args.connect_mt5:p.error('Use --connect-mt5 para una conexión explícita; no forma parte del runner diario')
    if args.count<100:p.error('count debe ser >=100')
    import MetaTrader5 as mt5
    import pandas as pd
    if not mt5.initialize(timeout=10000):raise RuntimeError(str(mt5.last_error()))
    stamp=datetime.now(timezone.utc);token=stamp.strftime('%Y%m%dT%H%M%S%fZ')
    batch=ROOT/'data/raw/darwinex'/token
    rows=[];failed=[]
    try:
        account=mt5.account_info()
        account_meta={k:getattr(account,k,None) for k in ('currency','leverage','margin_mode','margin_so_mode','margin_so_call','margin_so_so')}
        if kind=='ohlc':batch.mkdir(parents=True,exist_ok=False)
        for alias,c in read_json(ROOT/'config/instruments.json').items():
            if c.get('status')!='research' or not c.get('symbol_mt5'):continue
            name=c['symbol_mt5'];selected=mt5.symbol_select(name,True)
            if kind=='costs':
                info=mt5.symbol_info(name) if selected else None
                tick=mt5.symbol_info_tick(name)
                if info is None:failed.append(alias);continue
                row={k:getattr(info,k,None) for k in FIELDS}
                row.update(alias=alias,symbol_mt5=name,bid=tick.bid if tick else None,ask=tick.ask if tick else None,commission_per_side=None,commission_source='Account tariff required; not supplied by symbol_info')
                rows.append(row)
            else:
                for tf in c['timeframes']:
                    if tf not in TIMEFRAMES:raise ValueError('Timeframe no soportado')
                    rates=mt5.copy_rates_from_pos(name,getattr(mt5,'TIMEFRAME_'+tf),1,args.count) if selected else None
                    row={'symbol':alias,'timeframe':tf,'symbol_mt5':name,'status':'FAILED'}
                    if rates is not None and len(rates):
                        df=pd.DataFrame(rates);df['time']=pd.to_datetime(df.time,unit='s',utc=True)
                        df.to_parquet(batch/f'{alias}_{tf}.parquet',index=False)
                        row.update(status='EXPORTED',rows=len(df),first=str(df.time.min()),last=str(df.time.max()))
                    else:row['error']=str(mt5.last_error());failed.append(alias+'/'+tf)
                    rows.append(row);print(row,flush=True)
    finally:mt5.shutdown()
    path=ROOT/'docs/cost_snapshots'/f'{token}.json' if kind=='costs' else batch/'extraction.json'
    write_json(path,{'captured_at':stamp.isoformat(),'account_contract':account_meta,'symbols':rows,'failed':failed,'note':'Snapshot actual, no costos históricos. Convertir swap_mode explícitamente. Barras MT5 no se declaran mid automáticamente.'})
    print(path)
    return 2 if failed or not rows else 0
