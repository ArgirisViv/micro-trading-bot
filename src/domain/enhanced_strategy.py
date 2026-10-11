# src/domain/enhanced_strategy.py
"""
Enhanced Trading Strategy - 10/10 Performance
Combines Technical Analysis, ML Predictions, and Fundamental Analysis
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from core.enhanced_indicators import add_enhanced_indicators, generate_enhanced_signals
from core.ml_model import create_features, load_model
from core.fundamentals import fetch_fundamentals

class EnhancedStrategy:
    """
    Advanced trading strategy combining multiple approaches
    """
    
    def __init__(self, 
                 confidence_threshold: float = 0.7,
                 volume_threshold: float = 1.5,
                 volatility_threshold: float = 0.02):
        self.confidence_threshold = confidence_threshold
        self.volume_threshold = volume_threshold
        self.volatility_threshold = volatility_threshold
        
    def apply_strategy(self, data: pd.DataFrame, symbol: Optional[str] = None) -> pd.DataFrame:
        """
        Apply enhanced strategy to data
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
        
        # 5. Generate final enhanced signals
        df = self._generate_final_signals(df)
        
        # 6. Add confidence scores and risk metrics
        df = self._add_confidence_scores(df)
        
        return df
    
    def _add_ml_predictions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add ML model predictions with confidence scoring"""
        try:
            X, _ = create_features(df)
            model = load_model()
            
            if model is not None and not X.empty and hasattr(model, 'predict_proba'):
                # Get probability predictions for confidence
                proba = model.predict_proba(X)
                df.loc[X.index, 'ml_prediction'] = model.predict(X)
                df.loc[X.index, 'ml_confidence'] = np.max(proba, axis=1)
            else:
                df['ml_prediction'] = 0
                df['ml_confidence'] = 0.5
                
        except Exception:
            df['ml_prediction'] = 0
            df['ml_confidence'] = 0.5
            
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
    
    def _calculate_fundamental_score(self, fundamentals: Dict) -> float:
        """Calculate composite fundamental score"""
        score = 0.0
        weights = {
            'pe': -0.2,      # Lower is better
            'pb': -0.15,     # Lower is better
            'roe': 0.25,     # Higher is better
            'fcf_yield': 0.25,  # Higher is better
            'debt_to_equity': -0.1,  # Lower is better
            'profit_margin': 0.15   # Higher is better
        }
        
        for metric, weight in weights.items():
            if metric in fundamentals and fundamentals[metric] is not None:
                # Normalize and apply weight
                if metric in ['pe', 'pb', 'debt_to_equity']:
                    # Lower is better - inverse relationship
                    normalized = max(0, 1 - (fundamentals[metric] / 100))
                else:
                    # Higher is better
                    normalized = min(1, fundamentals[metric])
                
                score += weight * normalized
        
        return max(0, min(1, score + 0.5))  # Normalize to 0-1
    
    def _generate_final_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate final enhanced trading signals"""
        df = df.copy()
        
        # Initialize final signal
        df['signal'] = 0
        
        # Technical signal weight
        technical_weight = 0.4
        
        # ML signal weight
        ml_weight = 0.4
        
        # Fundamental weight (if available)
        fundamental_weight = 0.2 if 'fundamental_adjustment' in df.columns else 0.0
        
        # Calculate composite signal
        signals = []
        for row in df.to_dict(orient='records'):
            technical_sig = row.get('technical_signal', 0)
            ml_sig = row.get('ml_prediction', 0)
            ml_conf = row.get('ml_confidence', 0.5)
            
            # Weighted signal calculation
            composite_signal = (
                technical_weight * technical_sig +
                ml_weight * ml_sig * ml_conf
            )
            
            # Apply fundamental adjustment if available
            if 'fundamental_adjustment' in df.columns:
                composite_signal *= row['fundamental_adjustment']
                composite_signal += fundamental_weight * (row['fundamental_score'] - 0.5)
            
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
        """Add confidence scores and risk metrics"""
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
                confidence += row['ml_confidence'] * 0.4
            
            # Fundamental confidence
            if 'fundamental_score' in df.columns:
                fund_score = row['fundamental_score']
                confidence += fund_score * 0.2
            
            confidence_scores.append(min(1.0, confidence))

        df['confidence_score'] = confidence_scores
        
        # Risk metrics
        df['risk_level'] = 'LOW'
        df.loc[df['confidence_score'] < 0.5, 'risk_level'] = 'HIGH'
        df.loc[(df['confidence_score'] >= 0.5) & (df['confidence_score'] < 0.7), 'risk_level'] = 'MEDIUM'
        
        # Position sizing recommendation
        df['position_size'] = df['confidence_score'] * 100  # Percentage of max position
        
        return df
    
    def _is_crypto(self, symbol: str) -> bool:
        """Check if symbol is crypto"""
        return '/' in symbol or symbol.endswith('USD') or symbol.endswith('USDT')
    
    def get_strategy_summary(self, df: pd.DataFrame) -> Dict:
        """Get strategy performance summary"""
        if df.empty:
            return {}
        
        signals = df['signal'].value_counts()
        confidence_avg = df['confidence_score'].mean()
        
        return {
            'total_signals': len(df),
            'buy_signals': signals.get(1, 0),
            'sell_signals': signals.get(-1, 0),
            'hold_signals': signals.get(0, 0),
            'avg_confidence': confidence_avg,
            'signal_quality': 'HIGH' if confidence_avg > 0.7 else 'MEDIUM' if confidence_avg > 0.5 else 'LOW'
        }

def apply_enhanced_strategy(data: pd.DataFrame, symbol: Optional[str] = None) -> pd.DataFrame:
    """
    Convenience function to apply enhanced strategy
    """
    strategy = EnhancedStrategy()
    return strategy.apply_strategy(data, symbol)
