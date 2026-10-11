# core/__init__.py
"""
Core Trading Bot Modules
Exposes main functions and classes for easy importing
"""

# Core trading functions
def get_position(symbol):
    from .alpaca_trade import get_position
    return get_position(symbol)

def get_all_symbols(asset_class: str):
    from .alpaca_trade import get_all_symbols
    return get_all_symbols(asset_class)

def submit_order(symbol, side, qty, **kwargs):
    from .alpaca_trade import submit_order
    return submit_order(symbol, side, qty, **kwargs)

def close_position(symbol):
    from .alpaca_trade import close_position
    return close_position(symbol)

def get_open_positions_count():
    from .alpaca_trade import get_open_positions_count
    return get_open_positions_count()

# Strategy functions
def apply_enhanced_strategy(data, symbol=None):
    from .enhanced_strategy import apply_enhanced_strategy
    return apply_enhanced_strategy(data, symbol)

def apply_ultimate_strategy(data, symbol=None):
    from .ultimate_strategy import apply_ultimate_strategy
    return apply_ultimate_strategy(data, symbol)

# Market regime detection
def detect_market_regime(data):
    from .market_regime import MarketRegimeDetector
    return MarketRegimeDetector().detect_market_regime(data)

def get_regime_adaptations(regime):
    from .market_regime import MarketRegimeDetector
    detector = MarketRegimeDetector()
    return detector.get_regime_adaptation(regime)

# Macro factors analysis
def analyze_macro_factors(symbol=None):
    from .macro_factors import analyze_macro_factors
    return analyze_macro_factors(symbol)

def get_macro_adaptations(macro_env):
    from .macro_factors import get_macro_adaptations
    return get_macro_adaptations(macro_env)

# Enhanced fundamentals (Warren Buffett style)
def analyze_business_quality(symbol):
    from .enhanced_fundamentals import analyze_business_quality
    return analyze_business_quality(symbol)

def get_value_candidates(symbols, min_score=70.0):
    from .enhanced_fundamentals import get_value_candidates
    return get_value_candidates(symbols, min_score)

# Portfolio allocation
def calculate_optimal_allocation(market_regime, macro_environment, active_performance, value_performance):
    from .portfolio_allocator import calculate_optimal_allocation
    return calculate_optimal_allocation(market_regime, macro_environment, active_performance, value_performance)

def get_rebalancing_instructions(allocation):
    from .portfolio_allocator import get_rebalancing_instructions
    return get_rebalancing_instructions(allocation)

# Hybrid strategy (BEST OF BOTH WORLDS!)
def generate_hybrid_signals(symbols, market_data, portfolio_state=None):
    from .hybrid_strategy import generate_hybrid_signals
    return generate_hybrid_signals(symbols, market_data, portfolio_state)

def get_hybrid_portfolio_summary(signals):
    from .hybrid_strategy import get_hybrid_portfolio_summary
    return get_hybrid_portfolio_summary(signals)

# Risk management
def calculate_position_size(account_value, risk_per_trade, stop_loss_pct):
    if account_value <= 0 or not 0 < risk_per_trade <= 1 or not 0 < stop_loss_pct <= 1:
        raise ValueError("account_value must be positive and risk percentages must be in (0, 1]")
    return account_value * risk_per_trade / stop_loss_pct

def check_correlation_limits(positions, new_symbol, max_correlation=0.7, price_data=None):
    if price_data is None:
        raise ValueError("price_data is required to evaluate position correlations")
    from .risk_management import PortfolioRiskManager, RiskLimits
    manager = PortfolioRiskManager(RiskLimits(max_correlation=max_correlation))
    return manager.check_correlation_limits(new_symbol, positions, price_data)

# Data functions
def get_live_data(symbol):
    from ..data.live_data_fetch import get_live_data
    return get_live_data(symbol)

# Enhanced indicators
def add_enhanced_indicators(data):
    from .enhanced_indicators import add_enhanced_indicators
    return add_enhanced_indicators(data)

def generate_enhanced_signals(data):
    from .enhanced_indicators import generate_enhanced_signals
    return generate_enhanced_signals(data)

# ML model
def create_features(data):
    from .ml_model import create_features
    return create_features(data)

def load_model():
    from .ml_model import load_model
    return load_model()

# Fundamentals
def fetch_fundamentals(symbol):
    from .fundamentals import fetch_fundamentals
    return fetch_fundamentals(symbol)

# Advanced backtesting
def run_advanced_backtest(data, strategy_func, strategy_params=None):
    raise RuntimeError('Legacy advanced backtest retired. Use core.research_pipeline.evaluate '
                       'or python -m scripts.backtesting.offline_backtest with CSV/timeframe.')

__all__ = [
    # Core trading
    'get_position',
    'get_all_symbols',
    'submit_order',
    'close_position',
    'get_open_positions_count',
    
    # Strategy
    'apply_enhanced_strategy',
    'apply_ultimate_strategy',
    
    # Market regime
    'detect_market_regime',
    'get_regime_adaptations',
    
    # Macro factors
    'analyze_macro_factors',
    'get_macro_adaptations',
    
    # Enhanced fundamentals (Warren Buffett style)
    'analyze_business_quality',
    'get_value_candidates',
    
    # Portfolio allocation
    'calculate_optimal_allocation',
    'get_rebalancing_instructions',
    
    # Hybrid strategy (BEST OF BOTH WORLDS!)
    'generate_hybrid_signals',
    'get_hybrid_portfolio_summary',
    
    # Risk management
    'calculate_position_size',
    'check_correlation_limits',
    
    # Data
    'get_live_data',
    
    # Indicators
    'add_enhanced_indicators',
    'generate_enhanced_signals',
    
    # ML
    'create_features',
    'load_model',
    
    # Fundamentals
    'fetch_fundamentals',
    
    # Backtesting
    'run_advanced_backtest'
]
