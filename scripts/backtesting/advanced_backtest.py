"""Compatibility CLI: all research entrypoints use the canonical offline protocol.

Legacy online signatures intentionally removed: CSV and timeframe are required.
"""
from scripts.backtesting.offline_backtest import main

if __name__ == '__main__':
    main()
