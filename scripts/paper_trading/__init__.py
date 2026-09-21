# Paper trading module
# Lazy imports to avoid API key issues

def run_paper_trading_loop():
    from .paper_trading_loop import run_paper_trading_loop
    return run_paper_trading_loop()

def run_multi_asset_loop():
    from .multi_asset_loop import run_multi_asset_loop
    return run_multi_asset_loop()

__all__ = ['run_paper_trading_loop', 'run_multi_asset_loop']
