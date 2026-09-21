# core/ultimate_strategy.py
"""
ULTIMATE ENHANCED STRATEGY - 10/10 Performance
Combines ALL advanced features:
- Enhanced Technical Indicators
- ML Predictions with Confidence
- Fundamental Analysis
- Advanced Risk Management (Kelly Criterion + VaR)
- Market Regime Detection
- Dynamic Position Sizing
- Portfolio Heat Management
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional, List
from .enhanced_indicators import add_enhanced_indicators, generate_enhanced_signals
from .enhanced_strategy import EnhancedStrategy
from .advanced_risk import AdvancedRiskManager
from .market_regime import MarketRegimeDetector, detect_market_regime, adapt_strategy_to_regime
from .ml_model import create_features, load_model
from .fundamentals import fetch_fundamentals

class UltimateStrategy:
    """
    The ultimate trading strategy combining all advanced features
    """
    
    def __init__(self, 
                 confidence_threshold: float = 0.7,
                 max_portfolio_risk: float = 0.02,
                 max_position_risk: float = 0.01):
        
        self.confidence_threshold = confidence_threshold
        self.risk_manager = AdvancedRiskManager(
            max_portfolio_risk=max_portfolio_risk,
            max_position_risk=max_position_risk
        )
        self.regime_detector = MarketRegimeDetector()
        self.base_strategy = EnhancedStrategy(confidence_threshold=confidence_threshold)
        
    def apply_ultimate_strategy(self, 
                              data: pd.DataFrame, 
                              symbol: str = None,
                              portfolio_value: float = 100000.0,
                              current_positions: Dict = None,
                              trade_history: List[Dict] = None) -> Dict:
        """
        Apply the ultimate strategy with all features
        
        Returns comprehensive analysis and recommendations
        """
        df = data.copy()
        
        # 1. MARKET REGIME DETECTION
        regime_analysis = self._detect_and_adapt_regime(df)
        
        # 2. ENHANCED TECHNICAL ANALYSIS
        technical_analysis = self._apply_enhanced_technical_analysis(df)
        
        # 3. ML PREDICTIONS
        ml_analysis = self._apply_ml_analysis(df)
        
        # 4. FUNDAMENTAL ANALYSIS
        fundamental_analysis = self._apply_fundamental_analysis(df, symbol)
        
        # 5. RISK MANAGEMENT
        risk_analysis = self._apply_risk_management(
            df, symbol, portfolio_value, current_positions, trade_history
        )
        
        # 6. GENERATE ULTIMATE SIGNALS
        ultimate_signals = self._generate_ultimate_signals(
            technical_analysis, ml_analysis, fundamental_analysis, 
            risk_analysis, regime_analysis
        )
        
        # 7. POSITION SIZING RECOMMENDATIONS
        position_recommendations = self._calculate_position_recommendations(
            df, symbol, portfolio_value, risk_analysis, regime_analysis
        )
        
        # 8. COMPREHENSIVE SUMMARY
        strategy_summary = self._create_strategy_summary(
            regime_analysis, technical_analysis, ml_analysis, 
            fundamental_analysis, risk_analysis, ultimate_signals, 
            position_recommendations
        )
        
        return strategy_summary
    
    def _detect_and_adapt_regime(self, df: pd.DataFrame) -> Dict:
        """Detect market regime and adapt strategy parameters"""
        regime = detect_market_regime(df)
        adapted_params = adapt_strategy_to_regime(regime)
        
        return {
            'regime': regime,
            'adapted_params': adapted_params,
            'summary': self.regime_detector.get_regime_summary(regime)
        }
    
    def _apply_enhanced_technical_analysis(self, df: pd.DataFrame) -> Dict:
        """Apply enhanced technical indicators and analysis"""
        # Add all enhanced indicators
        df_with_indicators = add_enhanced_indicators(df)
        
        # Generate technical signals
        technical_signals = generate_enhanced_signals(df_with_indicators)
        
        # Calculate technical confidence
        technical_confidence = self._calculate_technical_confidence(df_with_indicators)
        
        return {
            'df_with_indicators': df_with_indicators,
            'technical_signals': technical_signals,
            'technical_confidence': technical_confidence,
            'latest_signal': int(technical_signals.iloc[-1]) if not technical_signals.empty else 0,
            'signal_strength': self._calculate_signal_strength(df_with_indicators, technical_signals)
        }
    
    def _apply_ml_analysis(self, df: pd.DataFrame) -> Dict:
        """Apply ML model predictions with confidence"""
        try:
            X, _ = create_features(df)
            model = load_model()
            
            if not X.empty and hasattr(model, 'predict_proba'):
                predictions = model.predict(X)
                proba = model.predict_proba(X)
                confidence = np.max(proba, axis=1)
                
                return {
                    'predictions': predictions,
                    'confidence': confidence,
                    'latest_prediction': int(predictions[-1]) if len(predictions) > 0 else 0,
                    'latest_confidence': float(confidence[-1]) if len(confidence) > 0 else 0.5,
                    'model_loaded': True
                }
            else:
                return {
                    'predictions': np.array([0]),
                    'confidence': np.array([0.5]),
                    'latest_prediction': 0,
                    'latest_confidence': 0.5,
                    'model_loaded': False
                }
                
        except Exception as e:
            return {
                'predictions': np.array([0]),
                'confidence': np.array([0.5]),
                'latest_prediction': 0,
                'latest_confidence': 0.5,
                'model_loaded': False,
                'error': str(e)
            }
    
    def _apply_fundamental_analysis(self, df: pd.DataFrame, symbol: str) -> Dict:
        """Apply fundamental analysis overlay"""
        if not symbol or self._is_crypto(symbol):
            return {
                'fundamental_score': 0.5,
                'fundamental_adjustment': 1.0,
                'available': False
            }
        
        try:
            fundamentals = fetch_fundamentals(symbol)
            
            if fundamentals:
                fundamental_score = self._calculate_fundamental_score(fundamentals)
                fundamental_adjustment = self._calculate_fundamental_adjustment(fundamental_score)
                
                return {
                    'fundamental_score': fundamental_score,
                    'fundamental_adjustment': fundamental_adjustment,
                    'fundamentals': fundamentals,
                    'available': True
                }
            else:
                return {
                    'fundamental_score': 0.5,
                    'fundamental_adjustment': 1.0,
                    'available': False
                }
                
        except Exception as e:
            return {
                'fundamental_score': 0.5,
                'fundamental_adjustment': 1.0,
                'available': False,
                'error': str(e)
            }
    
    def _apply_risk_management(self, 
                              df: pd.DataFrame, 
                              symbol: str, 
                              portfolio_value: float,
                              current_positions: Dict,
                              trade_history: List[Dict]) -> Dict:
        """Apply advanced risk management"""
        
        # Calculate volatility
        returns = df['close'].pct_change().dropna()
        volatility = self.risk_manager._calculate_volatility(returns)
        
        # Calculate portfolio heat
        portfolio_heat = self.risk_manager.calculate_portfolio_heat(
            current_positions or {}, 
            {symbol: df['close'].iloc[-1]}, 
            portfolio_value
        )
        
        # Calculate VaR
        var_analysis = self.risk_manager.calculate_var(returns)
        
        # Get win rate from trade history
        win_rate, avg_win, avg_loss = self._calculate_performance_metrics(trade_history)
        
        # Calculate optimal position size
        current_price = df['close'].iloc[-1]
        position_size_analysis = self.risk_manager.calculate_optimal_position_size(
            symbol, current_price, portfolio_value, volatility, 
            win_rate, avg_win, avg_loss, portfolio_heat
        )
        
        # Risk assessment
        risk_summary = self.risk_manager.get_risk_summary(
            portfolio_heat, volatility, self._get_recent_performance(trade_history)
        )
        
        return {
            'volatility': volatility,
            'portfolio_heat': portfolio_heat,
            'var_analysis': var_analysis,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'position_size_analysis': position_size_analysis,
            'risk_summary': risk_summary
        }
    
    def _generate_ultimate_signals(self, 
                                  technical_analysis: Dict,
                                  ml_analysis: Dict,
                                  fundamental_analysis: Dict,
                                  risk_analysis: Dict,
                                  regime_analysis: Dict) -> Dict:
        """Generate ultimate trading signals combining all factors"""
        
        # Get base signals
        technical_signal = technical_analysis['latest_signal']
        ml_signal = ml_analysis['latest_prediction']
        ml_confidence = ml_analysis['latest_confidence']
        
        # Get regime-adapted parameters
        regime_params = regime_analysis['adapted_params']
        entry_threshold = regime_params['entry_threshold']
        
        # Calculate composite signal
        composite_signal = self._calculate_composite_signal(
            technical_signal, ml_signal, ml_confidence, 
            fundamental_analysis, risk_analysis, regime_params
        )
        
        # Apply regime-specific adjustments
        final_signal = self._apply_regime_adjustments(
            composite_signal, regime_params, risk_analysis
        )
        
        return {
            'technical_signal': technical_signal,
            'ml_signal': ml_signal,
            'ml_confidence': ml_confidence,
            'composite_signal': composite_signal,
            'final_signal': final_signal,
            'signal_confidence': self._calculate_signal_confidence(
                technical_analysis, ml_analysis, fundamental_analysis, risk_analysis
            ),
            'regime_adjustments': regime_params
        }
    
    def _calculate_composite_signal(self, 
                                   technical_signal: int,
                                   ml_signal: int,
                                   ml_confidence: float,
                                   fundamental_analysis: Dict,
                                   risk_analysis: Dict,
                                   regime_params: Dict) -> float:
        """Calculate composite signal from all factors"""
        
        # Base weights
        technical_weight = 0.35
        ml_weight = 0.35
        fundamental_weight = 0.20
        risk_weight = 0.10
        
        # Technical signal contribution
        tech_contribution = technical_signal * technical_weight
        
        # ML signal contribution (weighted by confidence)
        ml_contribution = ml_signal * ml_confidence * ml_weight
        
        # Fundamental contribution
        fund_score = fundamental_analysis.get('fundamental_score', 0.5)
        fund_adjustment = fundamental_analysis.get('fundamental_adjustment', 1.0)
        fund_contribution = (fund_score - 0.5) * fundamental_weight * fund_adjustment
        
        # Risk contribution (reduce signal if high risk)
        risk_factor = 1.0 - risk_analysis['risk_summary'].get('total_risk', 0.0)
        risk_contribution = (risk_factor - 0.5) * risk_weight
        
        # Composite signal
        composite = tech_contribution + ml_contribution + fund_contribution + risk_contribution
        
        return composite
    
    def _apply_regime_adjustments(self, 
                                 composite_signal: float,
                                 regime_params: Dict,
                                 risk_analysis: Dict) -> int:
        """Apply regime-specific adjustments to final signal"""
        
        # Get regime parameters
        entry_threshold = regime_params.get('entry_threshold', 0.7)
        risk_multiplier = regime_params.get('risk_multiplier', 1.0)
        
        # Adjust threshold based on risk
        adjusted_threshold = entry_threshold * risk_multiplier
        
        # Generate final signal
        if composite_signal > adjusted_threshold:
            return 1  # Buy
        elif composite_signal < -adjusted_threshold:
            return -1  # Sell
        else:
            return 0  # Hold
    
    def _calculate_position_recommendations(self,
                                          df: pd.DataFrame,
                                          symbol: str,
                                          portfolio_value: float,
                                          risk_analysis: Dict,
                                          regime_analysis: Dict) -> Dict:
        """Calculate optimal position sizing recommendations"""
        
        current_price = df['close'].iloc[-1]
        position_size_analysis = risk_analysis['position_size_analysis']
        regime_params = regime_analysis['adapted_params']
        
        # Apply regime adjustments to position size
        regime_multiplier = regime_params.get('position_size_multiplier', 1.0)
        adjusted_size = position_size_analysis['recommended_size'] * regime_multiplier
        
        # Calculate stop loss levels
        volatility = risk_analysis['volatility']
        atr = df['atr'].iloc[-1] if 'atr' in df.columns else None
        stop_loss_analysis = self.risk_manager.calculate_stop_loss_level(
            current_price, volatility, atr
        )
        
        # Apply regime adjustments to stop loss
        stop_loss_multiplier = regime_params.get('stop_loss_multiplier', 1.0)
        adjusted_stop = stop_loss_analysis['recommended_stop'] * stop_loss_multiplier
        
        return {
            'recommended_size': max(1, int(adjusted_size)),
            'position_size_analysis': position_size_analysis,
            'stop_loss_analysis': stop_loss_analysis,
            'adjusted_stop_loss': adjusted_stop,
            'regime_adjustments': {
                'position_multiplier': regime_multiplier,
                'stop_loss_multiplier': stop_loss_multiplier
            }
        }
    
    def _create_strategy_summary(self, 
                                regime_analysis: Dict,
                                technical_analysis: Dict,
                                ml_analysis: Dict,
                                fundamental_analysis: Dict,
                                risk_analysis: Dict,
                                ultimate_signals: Dict,
                                position_recommendations: Dict) -> Dict:
        """Create comprehensive strategy summary"""
        
        return {
            'timestamp': pd.Timestamp.now().isoformat(),
            'market_regime': regime_analysis['summary'],
            'technical_analysis': {
                'signal': ultimate_signals['technical_signal'],
                'confidence': technical_analysis['technical_confidence'],
                'signal_strength': technical_analysis['signal_strength']
            },
            'ml_analysis': {
                'prediction': ultimate_signals['ml_signal'],
                'confidence': ultimate_signals['ml_confidence'],
                'model_loaded': ml_analysis['model_loaded']
            },
            'fundamental_analysis': {
                'score': fundamental_analysis.get('fundamental_score', 0.5),
                'adjustment': fundamental_analysis.get('fundamental_adjustment', 1.0),
                'available': fundamental_analysis.get('available', False)
            },
            'risk_analysis': {
                'volatility': risk_analysis['volatility'],
                'portfolio_risk': risk_analysis['risk_summary'].get('total_risk', 0.0),
                'risk_level': risk_analysis['risk_summary'].get('risk_level', 'UNKNOWN'),
                'recommendations': risk_analysis['risk_summary'].get('recommendations', [])
            },
            'ultimate_signals': {
                'composite_signal': ultimate_signals['composite_signal'],
                'final_signal': ultimate_signals['final_signal'],
                'signal_confidence': ultimate_signals['signal_confidence']
            },
            'position_recommendations': {
                'recommended_size': position_recommendations['recommended_size'],
                'stop_loss': position_recommendations['adjusted_stop_loss'],
                'kelly_percentage': position_recommendations['position_size_analysis'].get('kelly_pct', 0.0)
            },
            'regime_adaptations': ultimate_signals['regime_adjustments'],
            'overall_confidence': self._calculate_overall_confidence(
                ultimate_signals, risk_analysis, regime_analysis
            )
        }
    
    def _calculate_technical_confidence(self, df: pd.DataFrame) -> float:
        """Calculate technical analysis confidence"""
        confidence = 0.0
        
        # Check indicator alignment
        if 'macd' in df.columns and 'macd_signal' in df.columns:
            macd_diff = abs(df['macd'].iloc[-1] - df['macd_signal'].iloc[-1])
            if macd_diff > 0:
                confidence += 0.2
        
        if 'bb_percent_b' in df.columns:
            bb_pos = df['bb_percent_b'].iloc[-1]
            if bb_pos < 0.2 or bb_pos > 0.8:
                confidence += 0.2
        
        if 'rsi' in df.columns:
            rsi = df['rsi'].iloc[-1]
            if rsi < 30 or rsi > 70:
                confidence += 0.2
        
        if 'volume_momentum' in df.columns:
            vol_mom = df['volume_momentum'].iloc[-1]
            if vol_mom > 0.1:
                confidence += 0.2
        
        return min(1.0, confidence)
    
    def _calculate_signal_strength(self, df: pd.DataFrame, signals: pd.Series) -> float:
        """Calculate signal strength based on indicator convergence"""
        if signals.empty:
            return 0.0
        
        # Count how many indicators agree with the signal
        signal = signals.iloc[-1]
        if signal == 0:
            return 0.0
        
        strength = 0.0
        
        # MACD alignment
        if 'macd' in df.columns and 'macd_signal' in df.columns:
            if (signal == 1 and df['macd'].iloc[-1] > df['macd_signal'].iloc[-1]) or \
               (signal == -1 and df['macd'].iloc[-1] < df['macd_signal'].iloc[-1]):
                strength += 0.25
        
        # RSI alignment
        if 'rsi' in df.columns:
            rsi = df['rsi'].iloc[-1]
            if (signal == 1 and rsi < 40) or (signal == -1 and rsi > 60):
                strength += 0.25
        
        # Bollinger Bands alignment
        if 'bb_percent_b' in df.columns:
            bb_pos = df['bb_percent_b'].iloc[-1]
            if (signal == 1 and bb_pos < 0.3) or (signal == -1 and bb_pos > 0.7):
                strength += 0.25
        
        # Volume confirmation
        if 'volume_momentum' in df.columns:
            vol_mom = df['volume_momentum'].iloc[-1]
            if vol_mom > 0.1:
                strength += 0.25
        
        return strength
    
    def _calculate_signal_confidence(self,
                                    technical_analysis: Dict,
                                    ml_analysis: Dict,
                                    fundamental_analysis: Dict,
                                    risk_analysis: Dict) -> float:
        """Calculate overall signal confidence"""
        
        tech_conf = technical_analysis.get('technical_confidence', 0.0)
        ml_conf = ml_analysis.get('latest_confidence', 0.5)
        fund_conf = fundamental_analysis.get('fundamental_score', 0.5)
        risk_conf = 1.0 - risk_analysis['risk_summary'].get('total_risk', 0.0)
        
        # Weighted average
        confidence = (tech_conf * 0.3) + (ml_conf * 0.3) + (fund_conf * 0.2) + (risk_conf * 0.2)
        
        return max(0.0, min(1.0, confidence))
    
    def _calculate_overall_confidence(self,
                                     ultimate_signals: Dict,
                                     risk_analysis: Dict,
                                     regime_analysis: Dict) -> float:
        """Calculate overall strategy confidence"""
        
        signal_conf = ultimate_signals.get('signal_confidence', 0.0)
        regime_conf = regime_analysis['regime'].get('confidence', 0.0)
        risk_level = risk_analysis['risk_summary'].get('risk_level', 'MEDIUM')
        
        # Risk level adjustment
        risk_multiplier = 1.0
        if risk_level == 'HIGH':
            risk_multiplier = 0.7
        elif risk_level == 'MEDIUM':
            risk_multiplier = 0.9
        
        overall_conf = (signal_conf * 0.6) + (regime_conf * 0.4)
        overall_conf *= risk_multiplier
        
        return max(0.0, min(1.0, overall_conf))
    
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
    
    def _calculate_fundamental_adjustment(self, fundamental_score: float) -> float:
        """Calculate fundamental adjustment factor"""
        if fundamental_score > 0.6:
            return 1.2  # Boost bullish signals
        elif fundamental_score < 0.4:
            return 0.8  # Reduce bearish signals
        else:
            return 1.0  # Neutral
    
    def _calculate_performance_metrics(self, trade_history: List[Dict]) -> Tuple[float, float, float]:
        """Calculate performance metrics from trade history"""
        if not trade_history:
            return 0.5, 0.02, 0.01
        
        wins = [t for t in trade_history if t.get('pnl', 0) > 0]
        losses = [t for t in trade_history if t.get('pnl', 0) < 0]
        
        win_rate = len(wins) / len(trade_history) if trade_history else 0.5
        
        avg_win = np.mean([t.get('pnl_pct', 0.02) for t in wins]) if wins else 0.02
        avg_loss = np.mean([abs(t.get('pnl_pct', 0.01)) for t in losses]) if losses else 0.01
        
        return win_rate, avg_win, avg_loss
    
    def _get_recent_performance(self, trade_history: List[Dict]) -> List[float]:
        """Get recent performance for risk assessment"""
        if not trade_history:
            return []
        
        # Get last 10 trades
        recent_trades = trade_history[-10:]
        return [t.get('pnl_pct', 0.0) for t in recent_trades]
    
    def _is_crypto(self, symbol: str) -> bool:
        """Check if symbol is crypto"""
        return '/' in symbol or symbol.endswith('USD') or symbol.endswith('USDT')

def apply_ultimate_strategy(data: pd.DataFrame, 
                           symbol: str = None,
                           portfolio_value: float = 100000.0,
                           current_positions: Dict = None,
                           trade_history: List[Dict] = None) -> Dict:
    """
    Convenience function to apply the ultimate strategy
    """
    strategy = UltimateStrategy()
    return strategy.apply_ultimate_strategy(
        data, symbol, portfolio_value, current_positions, trade_history
    )
