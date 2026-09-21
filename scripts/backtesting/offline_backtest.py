"""CSV-only canonical backtest; deliberately no provider or broker connection."""
import argparse
import json
from pathlib import Path
import pandas as pd
from core.backtest_engine import BacktestPolicy, simulate
from core.enhanced_indicators import add_enhanced_indicators, generate_enhanced_signals


def research_signals(bars, symbol):
    # Exactly the existing technical-only branch: neutral overlays, technical
    # weight 1 and threshold .7 map technical {-1,0,1} identically. Avoid importing
    # inactive ML/provider/macro dependencies just to monkeypatch them away.
    return generate_enhanced_signals(add_enhanced_indicators(bars)).rename('signal')


def main():
    from core.research_pipeline import load_dataset, evaluate, save_report
    from core.stock_sessions import load_calendar
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', help='OHLCV CSV with UTC timestamp column (bar start)')
    parser.add_argument('--symbol', default='AAPL')
    parser.add_argument('--output', default='research_output')
    parser.add_argument('--timeframe', required=True, help='Explicit bar duration, e.g. 5min')
    parser.add_argument('--warmup-bars', type=int, default=100)
    parser.add_argument('--test-bars', type=int, default=100)
    parser.add_argument('--fee-bps', type=float, default=1)
    parser.add_argument('--slippage-bps', type=float, default=5)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--calendar',help='Read-only Alpaca calendar JSON export')
    mode.add_argument('--legacy-all-sessions',action='store_true',help='Historical approximation only, not live-matched')
    args = parser.parse_args()
    bars, dataset = load_dataset(args.csv, args.timeframe)
    calendar = load_calendar(args.calendar) if args.calendar else None
    if args.calendar:
        from hashlib import sha256
        dataset['calendar_sha256']=sha256(Path(args.calendar).read_bytes()).hexdigest()
        dataset['session_model']='regular fills, DAY expiry, no automatic re-protection'
    else:
        dataset['session_model']='explicit legacy all-session approximation'
    report, artifacts = evaluate(bars, args.symbol,
        BacktestPolicy(fee_bps=args.fee_bps, slippage_bps=args.slippage_bps),
        args.warmup_bars, args.test_bars,calendar=calendar,
        timeframe=args.timeframe if calendar is not None else None)
    save_report(args.output, report, artifacts, dataset, args.symbol)
    print(f'Offline report saved: {len(report["folds"])} independent test windows. No edge claim.')


if __name__ == '__main__': main()
