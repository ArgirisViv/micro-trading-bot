# core/enhanced_strategy.py
"""
Enhanced Trading Strategy - experimental, performance not established
Combines Technical Analysis, ML Predictions, Fundamental Analysis, Market Regime Detection, and Macro Factors
"""

import pandas as pd
import numpy as np
from sklearn.dummy import DummyClassifier
from typing import Dict, Tuple, Optional
from .enhanced_indicators import add_enhanced_indicators, generate_enhanced_signals
from .ml_model import create_features, load_model
from .fundamentals import fetch_fundamentals
from .market_regime import MarketRegimeDetector
from .macro_factors import analyze_macro_factors

class EnhancedStrategy:
    """
    Advanced trading strategy combining multiple approaches with regime awareness
    """
    
    def __init__(self, 
                 confidence_threshold: float = 0.7,  # Επαναφέρω στο αρχικό - καλύτερη ποιότητα
                 volume_threshold: float = 1.5,
                 volatility_threshold: float = 0.02,
                 enable_regime_adaptation: bool = False,
                 enable_macro_adaptation: bool = True):
        self.confidence_threshold = confidence_threshold
        self.volume_threshold = volume_threshold
        self.volatility_threshold = volatility_threshold
        self.enable_regime_adaptation = enable_regime_adaptation
        self.enable_macro_adaptation = enable_macro_adaptation
        
    def apply_strategy(self, data: pd.DataFrame, symbol: Optional[str] = None) -> pd.DataFrame:
        """
        Apply enhanced strategy to data with regime and macro adaptation
        Returns DataFrame with enhanced signals and confidence scores
        """
        df = data.copy()
        
        # 1. Add all enhanced technical indicators
        df = add_enhanced_indicators(df)
        
        # 2. Generate technical signals
        df['technical_signal'] = generate_enhanced_signals(df)
        
        # 3. Add ML predictions with confidence
        df = self._add_ml_predictions(df)
        
        # 4. Add fundamental analysis (if stock)
        if symbol and not self._is_crypto(symbol):
            df = self._add_fundamental_analysis(df, symbol)
        else:
            # Use default values for crypto
            df['fundamental_score'] = 0.5
            df['fundamental_adjustment'] = 1.0
        
        # 5. Detect market regime and adapt strategy
        if self.enable_regime_adaptation:
            df = self._add_regime_analysis(df)
        else:
            # Use default regime values
            df['market_regime'] = 'neutral'
            df['regime_confidence'] = 0.5
            df['regime_signal_boost'] = 1.0
            df['regime_risk_multiplier'] = 1.0
        
        # 6. Analyze macro factors and adapt strategy (temporarily disabled due to yfinance issues)
        # if not use_mock_data and self.enable_macro_adaptation:
        #     df = self._add_macro_analysis(df, symbol)
        # else:
        # Use default macro values for now
        df['economic_cycle'] = 'neutral'
        df['monetary_policy'] = 'neutral'
        df['market_sentiment'] = 'neutral'
        df['macro_signal_boost'] = 1.0
        df['macro_risk_multiplier'] = 1.0
        df['monetary_boost'] = 1.0
        df['sentiment_boost'] = 1.0
        
        # 7. Generate final enhanced signals with regime awareness
        df = self._generate_final_signals(df)
        
        # 8. Add confidence scores and risk metrics
        df = self._add_confidence_scores(df)
        
        return df
    
    def _add_ml_predictions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add ML model predictions with confidence scoring"""
        try:
            import os
            if os.getenv('ENABLE_RESEARCH_ML', 'false').lower() != 'true':
                df['ml_prediction'] = 0
                df['ml_confidence'] = 0.0
                df['ml_available'] = False
                return df
            X, _ = create_features(df)
            model = load_model()
            
            if (model is not None and not X.empty
                    and hasattr(model, 'predict_proba')
                    and not isinstance(model, DummyClassifier)):
                # Get probability predictions for confidence
                proba = model.predict_proba(X)
                df.loc[X.index, 'ml_prediction'] = model.predict(X)
                df.loc[X.index, 'ml_confidence'] = np.max(proba, axis=1)
                df['ml_available'] = True
            else:
                df['ml_prediction'] = 0
                df['ml_confidence'] = 0.0
                df['ml_available'] = False
                
        except Exception:
            df['ml_prediction'] = 0
            df['ml_confidence'] = 0.0
            df['ml_available'] = False
            
        return df
    
    def _add_fundamental_analysis(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Add fundamental analysis overlay"""
        try:
            fundamentals = fetch_fundamentals(symbol)
            
            if fundamentals:
                # Create fundamental score
                fundamental_score = self._calculate_fundamental_score(fundamentals)
                df['fundamental_score'] = fundamental_score
                
                # Adjust signals based on fundamentals
                df['fundamental_adjustment'] = np.where(
                    fundamental_score > 0.6, 1.2,  # Boost bullish signals
                    np.where(fundamental_score < 0.4, 0.8, 1.0)  # Reduce bearish signals
                )
            else:
                df['fundamental_score'] = 0.5
                df['fundamental_adjustment'] = 1.0
                
        except Exception:
            df['fundamental_score'] = 0.5
            df['fundamental_adjustment'] = 1.0
            
        return df
    
    def _add_regime_analysis(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add market regime analysis and adaptation"""
        try:
            # Detect market regime for the entire dataset
            detector = MarketRegimeDetector()
            regime = detector.detect_market_regime(df)
            
            # Add regime information to DataFrame
            df['market_regime'] = regime
            df['regime_confidence'] = 0.8  # Default confidence
            df['regime_duration'] = 1      # Default duration
            
            # Add regime-based signal adjustments
            if regime == 'BULL_MARKET':
                df['regime_signal_boost'] = 1.2
                df['regime_risk_multiplier'] = 1.1
            elif regime == 'BEAR_MARKET':
                df['regime_signal_boost'] = 0.8
                df['regime_risk_multiplier'] = 0.9
            elif regime == 'BULL_VOLATILE':
                df['regime_signal_boost'] = 0.7
                df['regime_risk_multiplier'] = 0.8
            elif regime == 'CONSOLIDATION':
                df['regime_signal_boost'] = 1.0
                df['regime_risk_multiplier'] = 1.0
            elif regime == 'CHOPPY':
                df['regime_signal_boost'] = 0.9
                df['regime_risk_multiplier'] = 0.7
            else:
                df['regime_signal_boost'] = 1.0
                df['regime_risk_multiplier'] = 1.0
            
            # Store regime adaptations for later use
            df.attrs['regime_adaptations'] = {
                'regime': regime,
                'signal_boost': df['regime_signal_boost'].iloc[0],
                'risk_multiplier': df['regime_risk_multiplier'].iloc[0]
            }
            
        except Exception as e:
            print(f"Warning: Regime analysis failed: {e}")
            df['market_regime'] = 'unknown'
            df['regime_confidence'] = 0.5
            df['regime_duration'] = 1
            df['regime_signal_boost'] = 1.0
            df['regime_risk_multiplier'] = 1.0
            
        return df
    
    def _add_macro_analysis(self, df: pd.DataFrame, symbol: Optional[str] = None) -> pd.DataFrame:
        """Add macroeconomic analysis and adaptation"""
        if symbol is None:
            df['economic_cycle'] = 'neutral'
            df['monetary_policy'] = 'neutral'
            df['market_sentiment'] = 'neutral'
            df['macro_signal_boost'] = 1.0
            df['macro_risk_multiplier'] = 1.0
            df['monetary_boost'] = 1.0
            df['sentiment_boost'] = 1.0
            return df
        try:
            # Analyze macro environment
            macro_env = analyze_macro_factors(symbol)
            
            # Get macro adaptations
            from .macro_factors import get_macro_adaptations
            macro_adaptations = get_macro_adaptations(macro_env)
            
            # Add macro information to DataFrame
            df['economic_cycle'] = macro_env.economic_cycle
            df['monetary_policy'] = macro_env.monetary_policy
            df['market_sentiment'] = macro_env.market_sentiment
            df['volatility_regime'] = macro_env.volatility_regime
            df['macro_confidence'] = macro_env.confidence_score
            
            # Add macro-based signal adjustments
            if macro_env.economic_cycle == 'expansion':
                df['macro_signal_boost'] = 1.1
                df['macro_risk_multiplier'] = 1.05
            elif macro_env.economic_cycle == 'contraction':
                df['macro_signal_boost'] = 0.9
                df['macro_risk_multiplier'] = 0.95
            else:
                df['macro_signal_boost'] = 1.0
                df['macro_risk_multiplier'] = 1.0
            
            if macro_env.monetary_policy == 'accommodative':
                df['monetary_boost'] = 1.1
            elif macro_env.monetary_policy == 'restrictive':
                df['monetary_boost'] = 0.9
            else:
                df['monetary_boost'] = 1.0
            
            if macro_env.market_sentiment == 'bullish':
                df['sentiment_boost'] = 1.1
            elif macro_env.market_sentiment == 'bearish':
                df['sentiment_boost'] = 0.9
            else:
                df['sentiment_boost'] = 1.0
            
            # Store macro adaptations for later use
            df.attrs['macro_adaptations'] = macro_adaptations
            
        except Exception as e:
            print(f"Warning: Macro analysis failed: {e}")
            df['economic_cycle'] = 'neutral'
            df['monetary_policy'] = 'neutral'
            df['market_sentiment'] = 'neutral'
            df['volatility_regime'] = 'medium'
            df['macro_confidence'] = 0.5
            df['macro_signal_boost'] = 1.0
            df['macro_risk_multiplier'] = 1.0
            df['monetary_boost'] = 1.0
            df['sentiment_boost'] = 1.0
            
        return df
    
    def _calculate_fundamental_score(self, fundamentals: Dict) -> float:
        """Calculate composite fundamental score"""
        score = 0.0
        available_weight = 0.0
        weights = {
            'pe': 0.2,      # Inverted below: do not invert again with a negative weight.
            'pb': 0.15,
            'roe': 0.25,     # Higher is better
            'fcf_yield': 0.25,  # Higher is better
            'debt_to_equity': 0.1,
            'profit_margin': 0.15   # Higher is better
        }
        
        for metric, weight in weights.items():
            if metric in fundamentals and fundamentals[metric] is not None:
                value = float(fundamentals[metric])
                if not np.isfinite(value) or (metric in ['pe', 'pb', 'debt_to_equity'] and value < 0):
                    continue
                # Normalize and apply weight
                if metric in ['pe', 'pb', 'debt_to_equity']:
                    # Lower is better - inverse relationship
                    normalized = max(0, 1 - (value / 100))
                else:
                    # Higher is better
                    normalized = max(0, min(1, value))
                
                score += weight * normalized
                available_weight += weight
        
        return score / available_weight if available_weight > 0 else 0.5
    
    def _generate_final_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate final enhanced trading signals with regime awareness"""
        df = df.copy()
        
        # Initialize final signal
        df['signal'] = 0
        
        # Base weights
        technical_weight = 0.75
        ml_weight = 0.25
        fundamental_weight = 0.15
        regime_weight = 0.15
        
        # Calculate composite signal for each row
        signals = []
        for row in df.to_dict(orient='records'):
            # Base signals
            technical_sig = row.get('technical_signal', 0)
            ml_sig = row.get('ml_prediction', 0)
            ml_conf = row.get('ml_confidence', 0.5)
            ml_available = bool(row.get('ml_available', False))
            # The model trains on binary direction (0 down, 1 up).
            ml_direction = (1 if ml_sig == 1 else -1) if ml_available else 0
            
            # Fundamental adjustment
            # Regime adjustments
            regime_boost = row.get('regime_signal_boost', 1.0)
            macro_boost = row.get('macro_signal_boost', 1.0)
            monetary_boost = row.get('monetary_boost', 1.0)
            sentiment_boost = row.get('sentiment_boost', 1.0)
            
            # Calculate composite signal
            composite_signal = (
                (technical_weight if ml_available else 1.0) * technical_sig +
                ml_weight * ml_direction * ml_conf
            )
            
            # Apply fundamental adjustment
            if 'fundamental_score' in df.columns:
                fundamental_score = row.get('fundamental_score', 0.5)
                composite_signal += fundamental_weight * (fundamental_score - 0.5)
            
            # Apply regime and macro adjustments
            total_boost = regime_boost * macro_boost * monetary_boost * sentiment_boost
            composite_signal *= total_boost
            
            # Generate final signal with confidence threshold
            if composite_signal > self.confidence_threshold:
                signals.append(1)
            elif composite_signal < -self.confidence_threshold:
                signals.append(-1)
            else:
                signals.append(0)

        df['signal'] = signals
        
        return df
    
    def _add_confidence_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add confidence scores and risk metrics with regime awareness"""
        df = df.copy()
        
        # Overall confidence score
        df['confidence_score'] = 0.0
        
        confidence_scores = []
        for row in df.to_dict(orient='records'):
            confidence = 0.0
            
            # Technical confidence
            if row.get('technical_signal', 0) != 0:
                # Check indicator alignment
                tech_conf = 0.0
                if 'macd' in df.columns and 'macd_signal' in df.columns:
                    if abs(row['macd'] - row['macd_signal']) > 0:
                        tech_conf += 0.2
                if 'bb_percent_b' in df.columns:
                    bb_pos = row['bb_percent_b']
                    if bb_pos < 0.2 or bb_pos > 0.8:
                        tech_conf += 0.2
                if 'rsi' in df.columns:
                    rsi = row['rsi']
                    if rsi < 30 or rsi > 70:
                        tech_conf += 0.2
                if 'volume_momentum' in df.columns:
                    vol_mom = row['volume_momentum']
                    if vol_mom > 0.1:
                        tech_conf += 0.2
                
                confidence += tech_conf
            
            # ML confidence
            if 'ml_confidence' in df.columns:
                confidence += row['ml_confidence'] * 0.3
            
            # Fundamental confidence
            if 'fundamental_score' in df.columns:
                fund_score = row['fundamental_score']
                confidence += fund_score * 0.2
            
            # Regime confidence
            if 'regime_confidence' in df.columns:
                regime_conf = row['regime_confidence']
                confidence += regime_conf * 0.15
            
            # Macro confidence
            if 'macro_confidence' in df.columns:
                macro_conf = row['macro_confidence']
                confidence += macro_conf * 0.15
            
            confidence_scores.append(min(1.0, confidence))

        df['confidence_score'] = confidence_scores
        
        # Risk metrics with regime awareness
        df['risk_level'] = 'LOW'
        df.loc[df['confidence_score'] < 0.5, 'risk_level'] = 'HIGH'
        df.loc[(df['confidence_score'] >= 0.5) & (df['confidence_score'] < 0.7), 'risk_level'] = 'MEDIUM'
        
        # Regime-adjusted position sizing
        df['position_size'] = df['confidence_score'] * 100  # Base percentage
        
        # Apply regime risk multipliers
        if 'regime_risk_multiplier' in df.columns:
            df['position_size'] *= df['regime_risk_multiplier']
        
        if 'macro_risk_multiplier' in df.columns:
            df['position_size'] *= df['macro_risk_multiplier']
        
        # Ensure position size is within reasonable bounds
        df['position_size'] = df['position_size'].clip(10, 100)
        
        return df
    
    def _is_crypto(self, symbol: str) -> bool:
        """Check if symbol is crypto"""
        return '/' in symbol or symbol.endswith('USD') or symbol.endswith('USDT')
    
    def get_strategy_summary(self, df: pd.DataFrame) -> Dict:
        """Get comprehensive strategy performance summary"""
        if df.empty:
            return {}
        
        # Basic metrics
        signals = df['signal'].value_counts()
        confidence_avg = df['confidence_score'].mean()
        
        # Regime analysis
        regime_summary = {}
        if 'market_regime' in df.columns:
            regime_counts = df['market_regime'].value_counts()
            regime_summary = {f"regime_{k}": v for k, v in regime_counts.items()}
        
        # Macro analysis
        macro_summary = {}
        if 'economic_cycle' in df.columns:
            cycle_counts = df['economic_cycle'].value_counts()
            macro_summary.update({f"cycle_{k}": v for k, v in cycle_counts.items()})
        
        if 'monetary_policy' in df.columns:
            policy_counts = df['monetary_policy'].value_counts()
            macro_summary.update({f"policy_{k}": v for k, v in policy_counts.items()})
        
        # Risk analysis
        risk_counts = df['risk_level'].value_counts()
        risk_summary = {f"risk_{k}": v for k, v in risk_counts.items()}
        
        return {
            'total_signals': len(df),
            'buy_signals': signals.get(1, 0),
            'sell_signals': signals.get(-1, 0),
            'hold_signals': signals.get(0, 0),
            'avg_confidence': confidence_avg,
            'signal_quality': 'HIGH' if confidence_avg > 0.7 else 'MEDIUM' if confidence_avg > 0.5 else 'LOW',
            'regime_analysis': regime_summary,
            'macro_analysis': macro_summary,
            'risk_analysis': risk_summary
        }

def apply_enhanced_strategy(data: pd.DataFrame, symbol: str | None = None) -> pd.DataFrame:
    """
    Convenience function to apply enhanced strategy with regime and macro adaptation
    """
    strategy = EnhancedStrategy()
    return strategy.apply_strategy(data, symbol)
