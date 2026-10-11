"""Continuous development-only DAY protection audit. Reserved later data not simulated."""
import argparse
from dataclasses import asdict
from datetime import date,timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any
import pandas as pd
from core.stock_sessions import load_calendar,session_windows
from core.research_pipeline import load_dataset,signals_for,buy_hold,save_report
from core.backtest_engine import simulate,BacktestPolicy


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv')
    parser.add_argument('--calendar',required=True)
    parser.add_argument('--development-end',required=True,help='Inclusive ET date; keep reserved holdout outside')
    parser.add_argument('--symbol',default='AAPL')
    parser.add_argument('--timeframe',default='5min')
    parser.add_argument('--output',default='session_audit_001')
    args=parser.parse_args()
    if Path(args.output).exists(): raise ValueError('Choose a NEW output folder')
    data,dataset_metadata=load_dataset(args.csv,args.timeframe)
    dataset: dict[str, Any] = dataset_metadata
    calendar=load_calendar(args.calendar)
    cutoff=pd.Timestamp(date.fromisoformat(args.development_end)+timedelta(days=1),tz='America/New_York').tz_convert('UTC')
    development=data.loc[data.index<cutoff]
    if len(development)<101: raise ValueError('At least 100 warmup bars plus test data required')
    sample=development.iloc[100:]
    signals=signals_for(development,args.symbol,'enhanced_technical')
    endings,_=session_windows(sample.index,calendar,args.timeframe)
    regular=[i for i,ending in enumerate(endings) if pd.notna(ending)]
    if not regular: raise ValueError('No regular-session bars in development sample')
    report: dict[str, Any] = dict(protocol='continuous development-only regular-session DAY audit v1',
        development_end=args.development_end,evaluated_rows=len(sample),warmup_rows=100,
        reserved_later_rows=int((data.index>=cutoff).sum()),later_performance_evaluated=False,
        scenarios={},interpretation='Diagnostic of current DAY order lifetime. No forced close or automatic re-protection. '
        'Expired protection may leave inventory exposed indefinitely. Not broker execution validation.')
    artifacts=[]
    for number,(name,fee,slip) in enumerate([('base',1,5),('stress',5,15)]):
        policy=BacktestPolicy(fee_bps=fee,slippage_bps=slip)
        curve,trades,metrics=simulate(sample,signals.loc[sample.index],policy,
            initial_signal=int(signals.iloc[99]),initial_signal_time=development.index[99],
            calendar=calendar,timeframe=args.timeframe)
        report['scenarios'][name]=dict(policy=asdict(policy),enhanced_technical=metrics,
            buy_hold=buy_hold(sample.iloc[regular[0]:],policy))
        artifacts.append((number,'enhanced_technical',curve,trades))
    dataset['calendar_sha256']=sha256(Path(args.calendar).read_bytes()).hexdigest()
    save_report(args.output,report,artifacts,dataset,args.symbol)
    print('Development-only DAY audit saved. Inspect expired protection and open inventory, not just return.')


if __name__=='__main__': main()
