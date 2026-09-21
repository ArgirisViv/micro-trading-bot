# src/domain/services.py
# Domain Services - Core Business Logic

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from .entities import TradingSignal, Position, Order, Portfolio
from .value_objects import Money, Percentage, RiskLevel, Confidence
from .repositories import TradingRepository, DataRepository, RiskRepository


class StrategyService(ABC):
    """Abstract strategy service for generating trading signals"""
    
    @abstractmethod
    def generate_signal(self, symbol: str, market_data: pd.DataFrame) -> TradingSignal:
        """Generate trading signal for symbol based on market data"""
        pass
    
    @abstractmethod
    def calculate_technical_indicators(self, market_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate technical indicators from market data"""
        pass
    
    @abstractmethod
    def validate_signal(self, signal: TradingSignal, market_data: pd.DataFrame) -> bool:
        """Validate trading signal against market conditions"""
        pass
    
    @abstractmethod
    def get_signal_confidence(self, signal: TradingSignal, market_data: pd.DataFrame) -> Confidence:
        """Calculate confidence level for trading signal"""
        pass


class RiskManagementService(ABC):
    """Abstract risk management service"""
    
    @abstractmethod
    def assess_position_risk(self, position: Position, market_data: pd.DataFrame) -> RiskLevel:
        """Assess risk level for a position"""
        pass
    
    @abstractmethod
    def calculate_position_size(self, portfolio: Portfolio, signal: TradingSignal, 
                              market_data: pd.DataFrame) -> int:
        """Calculate optimal position size based on risk management rules"""
        pass
    
    @abstractmethod
    def validate_trade(self, portfolio: Portfolio, signal: TradingSignal, 
                      quantity: int, price: Money) -> Tuple[bool, str]:
        """Validate if trade meets risk management criteria"""
        pass
    
    @abstractmethod
    def calculate_portfolio_risk(self, portfolio: Portfolio) -> Dict[str, Any]:
        """Calculate overall portfolio risk metrics"""
        pass
    
    @abstractmethod
    def should_close_position(self, position: Position, market_data: pd.DataFrame) -> bool:
        """Determine if position should be closed based on risk rules"""
        pass


class ConcreteStrategyService(StrategyService):
    """Concrete implementation of strategy service"""
    
    def __init__(self, data_repository: DataRepository):
        self.data_repository = data_repository
    
    def generate_signal(self, symbol: str, market_data: pd.DataFrame) -> TradingSignal:
        """Generate trading signal using technical analysis and ML"""
        if market_data.empty:
            return TradingSignal(
                symbol=symbol,
                signal_type="HOLD",
                confidence=0.0,
                risk_level=RiskLevel.HIGH
            )
        
        # Calculate technical indicators
        indicators = self.calculate_technical_indicators(market_data)
        
        # Generate signal based on indicators
        signal_type = self._determine_signal_type(indicators)
        confidence = self._calculate_signal_confidence(indicators)
        risk_level = self._assess_signal_risk(indicators)
        
        # Get latest price
        latest_price = market_data['close'].iloc[-1] if 'close' in market_data.columns else 0
        
        return TradingSignal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            price=Money.from_float(latest_price) if latest_price > 0 else None,
            technical_score=indicators.get('technical_score', 0.5),
            ml_score=indicators.get('ml_score', 0.5),
            fundamental_score=indicators.get('fundamental_score', 0.5),
            risk_level=risk_level
        )
    
    def calculate_technical_indicators(self, market_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate comprehensive technical indicators"""
        if market_data.empty:
            return {}
        
        indicators = {}
        
        try:
            # Basic price indicators
            if 'close' in market_data.columns:
                close_prices = market_data['close']
                
                # Moving averages
                indicators['sma_20'] = close_prices.rolling(20).mean().iloc[-1]
                indicators['sma_50'] = close_prices.rolling(50).mean().iloc[-1]
                indicators['ema_12'] = close_prices.ewm(span=12).mean().iloc[-1]
                indicators['ema_26'] = close_prices.ewm(span=26).mean().iloc[-1]
                
                # MACD
                ema_12 = close_prices.ewm(span=12).mean()
                ema_26 = close_prices.ewm(span=26).mean()
                macd_line = ema_12 - ema_26
                signal_line = macd_line.ewm(span=9).mean()
                indicators['macd'] = macd_line.iloc[-1]
                indicators['macd_signal'] = signal_line.iloc[-1]
                indicators['macd_histogram'] = macd_line.iloc[-1] - signal_line.iloc[-1]
                
                # RSI
                delta = close_prices.diff()
                gain = delta.where(delta > 0, 0.0)
                loss = -delta.where(delta < 0, 0.0)
                avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
                avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
                rs = avg_gain / avg_loss
                indicators['rsi'] = 100 - (100 / (1 + rs.iloc[-1]))
                
                # Bollinger Bands
                sma_20 = close_prices.rolling(20).mean()
                std_20 = close_prices.rolling(20).std()
                indicators['bb_upper'] = sma_20.iloc[-1] + (std_20.iloc[-1] * 2)
                indicators['bb_middle'] = sma_20.iloc[-1]
                indicators['bb_lower'] = sma_20.iloc[-1] - (std_20.iloc[-1] * 2)
                indicators['bb_position'] = (close_prices.iloc[-1] - indicators['bb_lower']) / (indicators['bb_upper'] - indicators['bb_lower'])
            
            # Volume indicators
            if 'volume' in market_data.columns:
                volume = market_data['volume']
                if 'close' in market_data.columns:
                    # Volume Weighted Average Price
                    vwap = (close_prices * volume).rolling(20).sum() / volume.rolling(20).sum()
                    indicators['vwap'] = vwap.iloc[-1]
                    
                    # Volume trend
                    indicators['volume_sma'] = volume.rolling(20).mean().iloc[-1]
                    indicators['volume_ratio'] = volume.iloc[-1] / indicators['volume_sma']
            
            # Volatility indicators
            if 'high' in market_data.columns and 'low' in market_data.columns:
                high = market_data['high']
                low = market_data['low']
                close = market_data['close']
                
                # Average True Range (ATR)
                tr1 = high - low
                tr2 = abs(high - close.shift())
                tr3 = abs(low - close.shift())
                true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                indicators['atr'] = true_range.rolling(14).mean().iloc[-1]
                
                # Volatility ratio
                indicators['volatility'] = true_range.rolling(20).std().iloc[-1]
            
            # Trend indicators
            if 'close' in market_data.columns:
                # ADX (Average Directional Index)
                close_diff = close_prices.diff()
                indicators['trend_strength'] = abs(close_diff).rolling(14).mean().iloc[-1]
                
                # Price momentum
                indicators['momentum'] = close_prices.iloc[-1] / close_prices.iloc[-5] - 1 if len(close_prices) >= 5 else 0
            
            # Calculate composite technical score
            technical_score = self._calculate_composite_score(indicators)
            indicators['technical_score'] = technical_score
            
            # Add ML and fundamental scores (placeholder for now)
            indicators['ml_score'] = 0.5  # Placeholder
            indicators['fundamental_score'] = 0.5  # Placeholder
            
        except Exception as e:
            # Log error and return default values
            indicators = {
                'technical_score': 0.5,
                'ml_score': 0.5,
                'fundamental_score': 0.5
            }
        
        return indicators
    
    def validate_signal(self, signal: TradingSignal, market_data: pd.DataFrame) -> bool:
        """Validate trading signal against market conditions"""
        if market_data.empty:
            return False
        
        # Basic validation
        if signal.confidence < 0.3:
            return False
        
        if signal.risk_level == RiskLevel.EXTREME:
            return False
        
        # Market data validation
        if 'close' in market_data.columns:
            latest_price = market_data['close'].iloc[-1]
            if latest_price <= 0:
                return False
        
        return True
    
    def get_signal_confidence(self, signal: TradingSignal, market_data: pd.DataFrame) -> Confidence:
        """Calculate confidence level for trading signal"""
        if market_data.empty:
            return Confidence.zero()
        
        # Base confidence from signal
        base_confidence = signal.confidence
        
        # Adjust based on market conditions
        market_confidence = self._calculate_market_confidence(market_data)
        
        # Combine confidences
        final_confidence = min(base_confidence + market_confidence, 1.0)
        
        return Confidence.from_float(final_confidence)
    
    def _determine_signal_type(self, indicators: Dict[str, float]) -> str:
        """Determine signal type based on technical indicators"""
        if not indicators:
            return "HOLD"
        
        # Simple signal generation logic
        technical_score = indicators.get('technical_score', 0.5)
        
        if technical_score > 0.7:
            return "BUY"
        elif technical_score < 0.3:
            return "SELL"
        else:
            return "HOLD"
    
    def _calculate_signal_confidence(self, indicators: Dict[str, float]) -> float:
        """Calculate signal confidence based on indicator strength"""
        if not indicators:
            return 0.5
        
        # Calculate confidence based on indicator consistency
        confidence_factors = []
        
        # RSI confidence
        if 'rsi' in indicators:
            rsi = indicators['rsi']
            if 30 <= rsi <= 70:
                confidence_factors.append(0.8)  # Neutral zone
            elif rsi < 30 or rsi > 70:
                confidence_factors.append(0.9)  # Extreme zone
            else:
                confidence_factors.append(0.5)
        
        # MACD confidence
        if 'macd_histogram' in indicators:
            macd_hist = indicators['macd_histogram']
            if abs(macd_hist) > 0:
                confidence_factors.append(0.8)
            else:
                confidence_factors.append(0.4)
        
        # Volume confidence
        if 'volume_ratio' in indicators:
            vol_ratio = indicators['volume_ratio']
            if vol_ratio > 1.5:
                confidence_factors.append(0.9)
            elif vol_ratio > 1.0:
                confidence_factors.append(0.7)
            else:
                confidence_factors.append(0.5)
        
        # Return average confidence
        if confidence_factors:
            return sum(confidence_factors) / len(confidence_factors)
        else:
            return 0.5
    
    def _assess_signal_risk(self, indicators: Dict[str, float]) -> RiskLevel:
        """Assess risk level for signal"""
        if not indicators:
            return RiskLevel.MEDIUM
        
        risk_score = 0
        
        # Volatility risk
        if 'atr' in indicators and 'close' in indicators:
            atr = indicators['atr']
            close = indicators.get('close', 100)
            volatility = atr / close if close > 0 else 0
            if volatility > 0.05:  # High volatility
                risk_score += 2
            elif volatility > 0.02:  # Medium volatility
                risk_score += 1
        
        # Trend risk
        if 'trend_strength' in indicators:
            trend_strength = indicators['trend_strength']
            if trend_strength < 0.01:  # Weak trend
                risk_score += 1
        
        # Volume risk
        if 'volume_ratio' in indicators:
            vol_ratio = indicators['volume_ratio']
            if vol_ratio < 0.5:  # Low volume
                risk_score += 1
        
        # Determine risk level
        if risk_score >= 3:
            return RiskLevel.HIGH
        elif risk_score >= 1:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _calculate_composite_score(self, indicators: Dict[str, float]) -> float:
        """Calculate composite technical score"""
        if not indicators:
            return 0.5
        
        scores = []
        
        # RSI score
        if 'rsi' in indicators:
            rsi = indicators['rsi']
            if rsi < 30:
                scores.append(0.9)  # Oversold - buy signal
            elif rsi > 70:
                scores.append(0.1)  # Overbought - sell signal
            else:
                scores.append(0.5)  # Neutral
        
        # MACD score
        if 'macd_histogram' in indicators:
            macd_hist = indicators['macd_histogram']
            if macd_hist > 0:
                scores.append(0.7)  # Bullish
            else:
                scores.append(0.3)  # Bearish
        
        # Moving average score
        if 'sma_20' in indicators and 'sma_50' in indicators:
            sma_20 = indicators['sma_20']
            sma_50 = indicators['sma_50']
            if sma_20 > sma_50:
                scores.append(0.7)  # Bullish
            else:
                scores.append(0.3)  # Bearish
        
        # Bollinger Bands score
        if 'bb_position' in indicators:
            bb_pos = indicators['bb_position']
            if bb_pos < 0.2:
                scores.append(0.8)  # Near lower band - buy
            elif bb_pos > 0.8:
                scores.append(0.2)  # Near upper band - sell
            else:
                scores.append(0.5)  # Middle
        
        # Return average score
        if scores:
            return sum(scores) / len(scores)
        else:
            return 0.5
    
    def _calculate_market_confidence(self, market_data: pd.DataFrame) -> float:
        """Calculate market confidence based on data quality and conditions"""
        if market_data.empty:
            return 0.0
        
        confidence = 0.5  # Base confidence
        
        # Data quality confidence
        if len(market_data) >= 50:
            confidence += 0.2  # Sufficient data
        
        # Volume confidence
        if 'volume' in market_data.columns:
            recent_volume = market_data['volume'].tail(5).mean()
            avg_volume = market_data['volume'].mean()
            if recent_volume > avg_volume:
                confidence += 0.1  # Above average volume
        
        # Price stability confidence
        if 'close' in market_data.columns:
            close_prices = market_data['close']
            price_volatility = close_prices.pct_change().std()
            if price_volatility < 0.02:  # Low volatility
                confidence += 0.1
            elif price_volatility > 0.05:  # High volatility
                confidence -= 0.1
        
        return min(confidence, 1.0)


class ConcreteRiskManagementService(RiskManagementService):
    """Concrete implementation of risk management service"""
    
    def __init__(self, risk_repository: RiskRepository):
        self.risk_repository = risk_repository
    
    def assess_position_risk(self, position: Position, market_data: pd.DataFrame) -> RiskLevel:
        """Assess risk level for a position"""
        if market_data.empty:
            return RiskLevel.HIGH
        
        risk_score = 0
        
        # Position size risk
        if position.quantity > 1000:  # Large position
            risk_score += 2
        
        # Price movement risk
        if 'close' in market_data.columns:
            close_prices = market_data['close']
            recent_volatility = close_prices.pct_change().tail(10).std()
            if recent_volatility > 0.03:  # High volatility
                risk_score += 2
            elif recent_volatility > 0.015:  # Medium volatility
                risk_score += 1
        
        # Unrealized P&L risk
        pnl_pct = position.unrealized_pnl_percentage.value
        if pnl_pct < -0.10:  # Large loss
            risk_score += 2
        elif pnl_pct < -0.05:  # Medium loss
            risk_score += 1
        
        # Determine risk level
        if risk_score >= 4:
            return RiskLevel.EXTREME
        elif risk_score >= 2:
            return RiskLevel.HIGH
        elif risk_score >= 1:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def calculate_position_size(self, portfolio: Portfolio, signal: TradingSignal, 
                              market_data: pd.DataFrame) -> int:
        """Calculate optimal position size based on risk management rules"""
        if market_data.empty:
            return 1
        
        # Get portfolio cash
        available_cash = portfolio.cash.amount
        
        # Risk per trade (2% of portfolio)
        risk_per_trade = available_cash * 0.02
        
        # Get latest price
        if 'close' in market_data.columns:
            latest_price = market_data['close'].iloc[-1]
        else:
            return 1
        
        if latest_price <= 0:
            return 1
        
        # Calculate position size based on risk
        position_size = int(risk_per_trade / latest_price)
        
        # Ensure minimum size
        position_size = max(1, position_size)
        
        # Ensure we don't exceed available cash
        max_size = int(available_cash / latest_price)
        position_size = min(position_size, max_size)
        
        return position_size
    
    def validate_trade(self, portfolio: Portfolio, signal: TradingSignal, 
                      quantity: int, price: Money) -> Tuple[bool, str]:
        """Validate if trade meets risk management criteria"""
        # Check if we have enough cash
        required_cash = price.amount * quantity
        if required_cash > portfolio.cash.amount:
            return False, "Insufficient cash"
        
        # Check position limits
        if len(portfolio.positions) >= 10:  # Max 10 positions
            return False, "Maximum positions reached"
        
        # Check risk level
        if signal.risk_level == RiskLevel.EXTREME:
            return False, "Signal risk level too high"
        
        # Check confidence
        if signal.confidence < 0.4:
            return False, "Signal confidence too low"
        
        # Check portfolio concentration
        portfolio_value = portfolio.total_value.amount
        trade_value = required_cash
        concentration = trade_value / portfolio_value if portfolio_value > 0 else 0
        
        if concentration > 0.25:  # Max 25% in single position
            return False, "Position size too large for portfolio"
        
        return True, "Trade validated"
    
    def calculate_portfolio_risk(self, portfolio: Portfolio) -> Dict[str, Any]:
        """Calculate overall portfolio risk metrics"""
        if not portfolio.positions:
            return {
                "overall_risk": RiskLevel.LOW.value,
                "risk_score": 0.0,
                "var_95": 0.0,
                "expected_shortfall": 0.0,
                "beta": 1.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "concentration_risk": 0.0
            }
        
        # Calculate basic risk metrics
        total_value = portfolio.total_value.amount
        total_pnl = portfolio.total_unrealized_pnl.amount
        
        # Value at Risk (simplified)
        if total_value > 0:
            var_95 = -total_value * 0.02  # 2% daily VaR
        else:
            var_95 = 0.0
        
        # Expected Shortfall
        expected_shortfall = var_95 * 1.5
        
        # Portfolio beta (simplified)
        beta = 1.0  # Placeholder
        
        # Sharpe ratio (simplified)
        if total_value > 0:
            returns = total_pnl / total_value
            volatility = 0.02  # Placeholder
            sharpe_ratio = returns / volatility if volatility > 0 else 0
        else:
            sharpe_ratio = 0.0
        
        # Maximum drawdown
        max_drawdown = abs(min(0, total_pnl / total_value)) if total_value > 0 else 0
        
        # Concentration risk
        if portfolio.positions:
            position_values = [pos.market_value.amount for pos in portfolio.positions]
            max_position_value = max(position_values)
            concentration_risk = max_position_value / total_value if total_value > 0 else 0
        else:
            concentration_risk = 0.0
        
        # Overall risk score
        risk_score = 0.0
        if max_drawdown > 0.10:
            risk_score += 0.4
        if concentration_risk > 0.20:
            risk_score += 0.3
        if abs(total_pnl / total_value) > 0.05:
            risk_score += 0.3
        
        # Determine overall risk level
        if risk_score >= 0.7:
            overall_risk = RiskLevel.HIGH
        elif risk_score >= 0.4:
            overall_risk = RiskLevel.MEDIUM
        else:
            overall_risk = RiskLevel.LOW
        
        return {
            "overall_risk": overall_risk.value,
            "risk_score": risk_score,
            "var_95": var_95,
            "expected_shortfall": expected_shortfall,
            "beta": beta,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "concentration_risk": concentration_risk
        }
    
    def should_close_position(self, position: Position, market_data: pd.DataFrame) -> bool:
        """Determine if position should be closed based on risk rules"""
        # Stop loss check
        if position.stop_loss:
            current_price = position.current_price.amount
            stop_price = position.stop_loss.amount
            
            if position.side.value == "long" and current_price <= stop_price:
                return True
            elif position.side.value == "short" and current_price >= stop_price:
                return True
        
        # Take profit check
        if position.take_profit:
            current_price = position.current_price.amount
            take_profit_price = position.take_profit.amount
            
            if position.side.value == "long" and current_price >= take_profit_price:
                return True
            elif position.side.value == "short" and current_price <= take_profit_price:
                return True
        
        # Trailing stop check
        if position.trailing_stop:
            current_price = position.current_price.amount
            trailing_stop_price = position.trailing_stop.amount
            
            if position.side.value == "long" and current_price <= trailing_stop_price:
                return True
            elif position.side.value == "short" and current_price >= trailing_stop_price:
                return True
        
        # Time-based exit (optional)
        # if position.entry_timestamp < datetime.now() - timedelta(days=30):
        #     return True
        
        return False
