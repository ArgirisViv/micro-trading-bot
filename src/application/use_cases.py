# src/application/use_cases.py
# Use Cases - Application Business Logic

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime

from ..domain.entities import (
    TradingSignal,
    Position,
    Order,
    Portfolio,
    PositionSide,
    SignalType,
)
from ..domain.services import StrategyService, RiskManagementService
from ..domain.repositories import TradingRepository, DataRepository
from ..domain.value_objects import Money, Percentage, RiskLevel
from .dto import (
    TradingAction, TradingRequest, TradingResponse, PortfolioUpdate,
    SignalRequest, SignalResponse,
    RiskAssessmentRequest, RiskAssessmentResponse
)


class TradingUseCase(ABC):
    """Abstract trading use case"""
    
    @abstractmethod
    def execute_trade(self, request: TradingRequest) -> TradingResponse:
        """Execute a trading operation"""
        pass
    
    @abstractmethod
    def get_portfolio_status(self, portfolio_id: str) -> Dict[str, Any]:
        """Get current portfolio status"""
        pass
    
    @abstractmethod
    def close_position(self, portfolio_id: str, symbol: str) -> TradingResponse:
        """Close a specific position"""
        pass


class PortfolioUseCase(ABC):
    """Abstract portfolio use case"""
    
    @abstractmethod
    def create_portfolio(self, name: str, initial_cash: float) -> Portfolio:
        """Create a new portfolio"""
        pass
    
    @abstractmethod
    def update_portfolio(self, portfolio_id: str, update: PortfolioUpdate) -> bool:
        """Update portfolio with changes"""
        pass
    
    @abstractmethod
    def get_portfolio_summary(self, portfolio_id: str) -> Dict[str, Any]:
        """Get portfolio summary information"""
        pass


class RiskManagementUseCase(ABC):
    """Abstract risk management use case"""
    
    @abstractmethod
    def assess_portfolio_risk(self, request: RiskAssessmentRequest) -> RiskAssessmentResponse:
        """Assess portfolio risk level"""
        pass
    
    @abstractmethod
    def validate_trade_risk(self, portfolio_id: str, trade_request: TradingRequest) -> bool:
        """Validate if trade meets risk criteria"""
        pass
    
    @abstractmethod
    def get_risk_recommendations(self, portfolio_id: str) -> List[str]:
        """Get risk management recommendations"""
        pass


class ConcreteTradingUseCase(TradingUseCase):
    """Concrete implementation of trading use case"""
    
    def __init__(self, 
                 trading_repository: TradingRepository,
                 data_repository: DataRepository,
                 strategy_service: StrategyService,
                 risk_service: RiskManagementService):
        self.trading_repository = trading_repository
        self.data_repository = data_repository
        self.strategy_service = strategy_service
        self.risk_service = risk_service
    
    def execute_trade(self, request: TradingRequest) -> TradingResponse:
        """Execute a trading operation with full validation"""
        try:
            # Get portfolio (assuming single portfolio for now)
            portfolio = self._get_default_portfolio()
            if not portfolio:
                return TradingResponse(
                    success=False,
                    message="Portfolio not found",
                    error_code="PORTFOLIO_NOT_FOUND"
                )
            
            # Validate trade request
            if not self._validate_trade_request(request, portfolio):
                return TradingResponse(
                    success=False,
                    message="Trade validation failed",
                    error_code="TRADE_VALIDATION_FAILED"
                )
            
            # Execute trade based on action
            if request.action.value == "buy":
                return self._execute_buy_order(request, portfolio)
            elif request.action.value == "sell":
                return self._execute_sell_order(request, portfolio)
            elif request.action.value == "close":
                return self._execute_close_position(request, portfolio)
            else:
                return TradingResponse(
                    success=False,
                    message=f"Unsupported action: {request.action.value}",
                    error_code="UNSUPPORTED_ACTION"
                )
                
        except Exception as e:
            return TradingResponse(
                success=False,
                message=f"Trade execution failed: {str(e)}",
                error_code="EXECUTION_ERROR"
            )
    
    def get_portfolio_status(self, portfolio_id: str) -> Dict[str, Any]:
        """Get current portfolio status"""
        try:
            portfolio = self.trading_repository.get_portfolio(portfolio_id)
            if not portfolio:
                return {"error": "Portfolio not found"}
            
            return portfolio.to_dict()
            
        except Exception as e:
            return {"error": f"Failed to get portfolio status: {str(e)}"}
    
    def close_position(self, portfolio_id: str, symbol: str) -> TradingResponse:
        """Close a specific position"""
        try:
            portfolio = self.trading_repository.get_portfolio(portfolio_id)
            if not portfolio:
                return TradingResponse(
                    success=False,
                    message="Portfolio not found",
                    error_code="PORTFOLIO_NOT_FOUND"
                )
            
            position = portfolio.get_position_by_symbol(symbol)
            if not position:
                return TradingResponse(
                    success=False,
                    message=f"No position found for {symbol}",
                    error_code="POSITION_NOT_FOUND"
                )
            
            # Create close order
            close_request = TradingRequest(
                symbol=symbol,
                action=TradingAction.CLOSE,
                quantity=position.quantity,
                price=float(position.current_price.amount)
            )
            
            return self._execute_close_position(close_request, portfolio)
            
        except Exception as e:
            return TradingResponse(
                success=False,
                message=f"Failed to close position: {str(e)}",
                error_code="CLOSE_ERROR"
            )
    
    def _get_default_portfolio(self) -> Optional[Portfolio]:
        """Get default portfolio (simplified)"""
        # In a real implementation, you'd get this from user context
        portfolios = self.trading_repository.get_portfolio("default")
        return portfolios
    
    def _validate_trade_request(self, request: TradingRequest, portfolio: Portfolio) -> bool:
        """Validate trade request against portfolio"""
        if (request.action.value in ["buy", "sell"] and request.quantity is None
                and request.risk_per_trade is None):
            return False
        price = self._resolve_request_price(request)
        if request.action.value in ["buy", "sell"] and (price is None or price <= 0):
            return False
        
        # Check if we have enough cash for buy orders
        if request.action.value == "buy":
            required_cash = (request.quantity or 0) * (price or 0)
            if required_cash > float(portfolio.cash.amount):
                return False
        
        # Check if we have position for sell orders
        if request.action.value == "sell":
            position = portfolio.get_position_by_symbol(request.symbol)
            if (not position or request.quantity is None
                    or position.quantity < request.quantity):
                return False
        
        return True

    def _resolve_request_price(self, request: TradingRequest) -> float | None:
        if request.price is not None:
            return request.price
        return self.data_repository.get_latest_price(request.symbol)
    
    def _execute_buy_order(self, request: TradingRequest, portfolio: Portfolio) -> TradingResponse:
        """Execute buy order"""
        try:
            price = self._resolve_request_price(request)
            if price is None or price <= 0:
                return TradingResponse(
                    success=False,
                    message="A valid execution price is unavailable",
                    error_code="PRICE_UNAVAILABLE"
                )

            quantity = request.quantity
            if quantity is None and request.risk_per_trade is not None:
                signal = TradingSignal(
                    symbol=request.symbol,
                    signal_type=SignalType.BUY,
                    confidence=0.8,
                    price=Money.from_float(price)
                )
                quantity = self.risk_service.calculate_position_size(
                    portfolio,
                    signal,
                    pd.DataFrame({"close": [price]}),
                    request.risk_per_trade
                )
            
            if quantity is None or quantity <= 0:
                return TradingResponse(
                    success=False,
                    message="Invalid quantity for buy order",
                    error_code="INVALID_QUANTITY"
                )
            if quantity * price > float(portfolio.cash.amount):
                return TradingResponse(
                    success=False,
                    message="Insufficient cash for buy order",
                    error_code="INSUFFICIENT_CASH"
                )
            
            # Create order
            order = Order(
                symbol=request.symbol,
                side=PositionSide.LONG,
                quantity=quantity,
                price=Money.from_float(price),
                order_type=request.order_type.value
            )
            
            # Add order to portfolio
            portfolio.add_order(order)
            
            # Update cash
            order_value = quantity * price
            portfolio.update_cash(Money.from_float(-order_value))
            
            # Save portfolio
            self.trading_repository.save_portfolio(portfolio)
            
            return TradingResponse(
                success=True,
                order_id=order.id,
                message=f"Buy order submitted for {quantity} {request.symbol}",
                execution_price=price,
                execution_quantity=quantity
            )
            
        except Exception as e:
            return TradingResponse(
                success=False,
                message=f"Buy order execution failed: {str(e)}",
                error_code="BUY_EXECUTION_ERROR"
            )
    
    def _execute_sell_order(self, request: TradingRequest, portfolio: Portfolio) -> TradingResponse:
        """Execute sell order"""
        try:
            # Check if we have position to sell
            position = portfolio.get_position_by_symbol(request.symbol)
            quantity = request.quantity
            price = self._resolve_request_price(request)
            if (not position or quantity is None or quantity <= 0
                    or position.quantity < quantity or price is None or price <= 0):
                return TradingResponse(
                    success=False,
                    message=f"Insufficient position for {request.symbol}",
                    error_code="INSUFFICIENT_POSITION"
                )
            
            # Create order
            order = Order(
                symbol=request.symbol,
                side=PositionSide.SHORT,
                quantity=quantity,
                price=Money.from_float(price),
                order_type=request.order_type.value
            )
            
            # Add order to portfolio
            portfolio.add_order(order)
            portfolio.update_cash(Money.from_float(quantity * price))
            position.current_price = Money.from_float(price)
            position.quantity -= quantity
            if position.quantity == 0:
                portfolio.remove_position(position.id)
            
            # Save portfolio
            self.trading_repository.save_portfolio(portfolio)
            
            return TradingResponse(
                success=True,
                order_id=order.id,
                message=f"Sell order submitted for {quantity} {request.symbol}",
                execution_price=price,
                execution_quantity=quantity
            )
            
        except Exception as e:
            return TradingResponse(
                success=False,
                message=f"Sell order execution failed: {str(e)}",
                error_code="SELL_EXECUTION_ERROR"
            )
    
    def _execute_close_position(self, request: TradingRequest, portfolio: Portfolio) -> TradingResponse:
        """Execute position close"""
        try:
            position = portfolio.get_position_by_symbol(request.symbol)
            if not position:
                return TradingResponse(
                    success=False,
                    message=f"No position found for {request.symbol}",
                    error_code="NO_POSITION"
                )
            
            # Remove position
            portfolio.remove_position(position.id)
            
            # Update cash (simplified - in reality you'd get market price)
            position_value = position.market_value.amount
            portfolio.update_cash(Money.from_float(float(position_value)))
            
            # Save portfolio
            self.trading_repository.save_portfolio(portfolio)
            
            return TradingResponse(
                success=True,
                message=f"Position closed for {request.symbol}",
                execution_price=float(position.current_price.amount),
                execution_quantity=position.quantity
            )
            
        except Exception as e:
            return TradingResponse(
                success=False,
                message=f"Position close failed: {str(e)}",
                error_code="CLOSE_ERROR"
            )


class ConcretePortfolioUseCase(PortfolioUseCase):
    """Concrete implementation of portfolio use case"""
    
    def __init__(self, trading_repository: TradingRepository):
        self.trading_repository = trading_repository
    
    def create_portfolio(self, name: str, initial_cash: float) -> Portfolio:
        """Create a new portfolio"""
        try:
            portfolio = Portfolio(
                name=name,
                cash=Money.from_float(initial_cash)
            )
            
            # Save portfolio
            self.trading_repository.save_portfolio(portfolio)
            
            return portfolio
            
        except Exception as e:
            raise ValueError(f"Failed to create portfolio: {str(e)}")
    
    def update_portfolio(self, portfolio_id: str, update: PortfolioUpdate) -> bool:
        """Update portfolio with changes"""
        try:
            portfolio = self.trading_repository.get_portfolio(portfolio_id)
            if not portfolio:
                return False
            
            # Apply cash change
            if update.cash_change != 0:
                portfolio.update_cash(Money.from_float(update.cash_change))
            
            # Apply position changes
            for pos_data in update.positions_added:
                # In a real implementation, you'd create Position objects
                pass
            
            for pos_id in update.positions_removed:
                portfolio.remove_position(pos_id)
            
            # Apply order changes
            for order_data in update.orders_added:
                # In a real implementation, you'd create Order objects
                pass
            
            # Save updated portfolio
            return self.trading_repository.save_portfolio(portfolio)
            
        except Exception as e:
            return False
    
    def get_portfolio_summary(self, portfolio_id: str) -> Dict[str, Any]:
        """Get portfolio summary information"""
        try:
            portfolio = self.trading_repository.get_portfolio(portfolio_id)
            if not portfolio:
                return {"error": "Portfolio not found"}
            
            # Calculate summary metrics
            summary = {
                "id": portfolio.id,
                "name": portfolio.name,
                "total_value": float(portfolio.total_value.amount),
                "cash": float(portfolio.cash.amount),
                "positions_value": float(portfolio.total_positions_value.amount),
                "position_count": portfolio.position_count,
                "open_orders": portfolio.open_orders_count,
                "unrealized_pnl": float(portfolio.total_unrealized_pnl.amount),
                "unrealized_pnl_pct": float(portfolio.total_unrealized_pnl_percentage.value),
                "last_update": portfolio.last_update.isoformat()
            }
            
            return summary
            
        except Exception as e:
            return {"error": f"Failed to get portfolio summary: {str(e)}"}


class ConcreteRiskManagementUseCase(RiskManagementUseCase):
    """Concrete implementation of risk management use case"""
    
    def __init__(self, 
                 trading_repository: TradingRepository,
                 risk_service: RiskManagementService):
        self.trading_repository = trading_repository
        self.risk_service = risk_service
    
    def assess_portfolio_risk(self, request: RiskAssessmentRequest) -> RiskAssessmentResponse:
        """Assess portfolio risk level"""
        try:
            portfolio = self.trading_repository.get_portfolio(request.portfolio_id)
            if not portfolio:
                return RiskAssessmentResponse(
                    portfolio_id=request.portfolio_id,
                    overall_risk_level="unknown",
                    risk_score=1.0,
                    risk_alerts=["Portfolio not found"],
                    recommendations=["Create portfolio first"]
                )
            
            # Get risk assessment from the domain service.
            service_metrics = self.risk_service.calculate_portfolio_risk(portfolio)
            risk_level = RiskLevel(service_metrics.get("overall_risk", RiskLevel.MEDIUM.value))
            
            # Calculate risk metrics
            risk_metrics = self._calculate_risk_metrics(portfolio, request.risk_metrics)
            
            # Generate risk alerts
            risk_alerts = self._generate_risk_alerts(portfolio, risk_metrics)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(portfolio, risk_metrics)
            
            return RiskAssessmentResponse(
                portfolio_id=request.portfolio_id,
                overall_risk_level=risk_level.value,
                risk_score=float(service_metrics.get("risk_score", 0.0)),
                risk_metrics=risk_metrics,
                risk_alerts=risk_alerts,
                recommendations=recommendations
            )
            
        except Exception as e:
            return RiskAssessmentResponse(
                portfolio_id=request.portfolio_id,
                overall_risk_level="error",
                risk_score=1.0,
                risk_alerts=[f"Risk assessment failed: {str(e)}"],
                recommendations=["Check system logs for details"]
            )
    
    def validate_trade_risk(self, portfolio_id: str, trade_request: TradingRequest) -> bool:
        """Validate if trade meets risk criteria"""
        try:
            portfolio = self.trading_repository.get_portfolio(portfolio_id)
            price = trade_request.price
            quantity = trade_request.quantity
            if not portfolio or price is None or quantity is None:
                return False
            
            # Create trading signal for validation
            signal = TradingSignal(
                symbol=trade_request.symbol,
                signal_type=SignalType.BUY if trade_request.action.value == "buy" else SignalType.SELL,
                confidence=0.8,  # Default confidence
                price=Money.from_float(price)
            )
            
            # Validate trade using risk service
            is_valid, _reason = self.risk_service.validate_trade(
                portfolio, signal, quantity, Money.from_float(price)
            )
            return is_valid
            
        except Exception as e:
            return False
    
    def get_risk_recommendations(self, portfolio_id: str) -> List[str]:
        """Get risk management recommendations"""
        try:
            portfolio = self.trading_repository.get_portfolio(portfolio_id)
            if not portfolio:
                return ["Create portfolio first"]
            
            recommendations = []
            
            # Check position concentration
            if portfolio.position_count > 0:
                max_position_value = max(pos.market_value.amount for pos in portfolio.positions)
                concentration = max_position_value / portfolio.total_value.amount
                
                if concentration > 0.2:
                    recommendations.append("Reduce position concentration - no single position should exceed 20%")
            
            # Check diversification
            if portfolio.position_count < 3:
                recommendations.append("Increase portfolio diversification - aim for at least 3-5 positions")
            
            # Check cash allocation
            cash_ratio = portfolio.cash.amount / portfolio.total_value.amount
            if cash_ratio < 0.1:
                recommendations.append("Maintain adequate cash reserves - aim for at least 10%")
            elif cash_ratio > 0.5:
                recommendations.append("Consider deploying excess cash - current allocation may be too conservative")
            
            # Check P&L
            if portfolio.total_unrealized_pnl.amount < 0:
                pnl_pct = abs(portfolio.total_unrealized_pnl_percentage.value)
                if pnl_pct > 5:
                    recommendations.append(f"Monitor losses - current unrealized loss is {pnl_pct:.1f}%")
            
            if not recommendations:
                recommendations.append("Portfolio risk profile looks healthy")
            
            return recommendations
            
        except Exception as e:
            return [f"Failed to generate recommendations: {str(e)}"]
    
    def _calculate_risk_metrics(self, portfolio: Portfolio, requested_metrics: List[str]) -> Dict[str, Any]:
        """Calculate requested risk metrics"""
        metrics = {}
        
        for metric in requested_metrics:
            if metric == "var":
                metrics["var"] = self._calculate_var(portfolio)
            elif metric == "sharpe":
                metrics["sharpe"] = self._calculate_sharpe(portfolio)
            elif metric == "drawdown":
                metrics["drawdown"] = self._calculate_drawdown(portfolio)
            elif metric == "volatility":
                metrics["volatility"] = self._calculate_volatility(portfolio)
            elif metric == "correlation":
                metrics["correlation"] = self._calculate_correlation(portfolio)
            elif metric == "concentration":
                metrics["concentration"] = self._calculate_concentration(portfolio)
        
        return metrics
    
    def _calculate_var(self, portfolio: Portfolio) -> float:
        """Calculate Value at Risk (simplified)"""
        # Simplified VaR calculation
        if portfolio.total_value.amount == 0:
            return 0.0
        
        # Assume normal distribution with 2% daily volatility
        daily_vol = 0.02
        var_95 = float(portfolio.total_value.amount) * daily_vol * 1.645
        return float(var_95)
    
    def _calculate_sharpe(self, portfolio: Portfolio) -> float:
        """Calculate Sharpe ratio (simplified)"""
        # Simplified Sharpe calculation
        if portfolio.total_value.amount == 0:
            return 0.0
        
        # Assume risk-free rate of 2% annually
        risk_free_rate = 0.02 / 252  # Daily rate
        
        # Calculate daily return (simplified)
        daily_return = (float(portfolio.total_unrealized_pnl.amount) /
                        float(portfolio.total_value.amount) / 30)  # Assume 30 days
        
        # Calculate Sharpe ratio
        excess_return = daily_return - risk_free_rate
        volatility = 0.02  # Assume 2% daily volatility
        
        if volatility == 0:
            return 0.0
        
        return excess_return / volatility
    
    def _calculate_drawdown(self, portfolio: Portfolio) -> float:
        """Calculate current drawdown"""
        if portfolio.total_value.amount == 0:
            return 0.0
        
        # Simplified drawdown calculation
        if portfolio.total_unrealized_pnl.amount < 0:
            return float(abs(portfolio.total_unrealized_pnl_percentage.value) / 100)
        return 0.0
    
    def _calculate_volatility(self, portfolio: Portfolio) -> float:
        """Calculate portfolio volatility (simplified)"""
        # Simplified volatility based on position count
        if portfolio.position_count <= 1:
            return 0.8  # High volatility for single position
        elif portfolio.position_count <= 3:
            return 0.6  # Medium-high volatility
        elif portfolio.position_count <= 10:
            return 0.4  # Medium volatility
        else:
            return 0.2  # Low volatility for well-diversified portfolio
    
    def _calculate_correlation(self, portfolio: Portfolio) -> float:
        """Calculate portfolio correlation (simplified)"""
        # Simplified correlation calculation
        if portfolio.position_count <= 1:
            return 1.0  # Perfect correlation for single position
        
        # Assume lower correlation for more positions
        return max(0.1, 1.0 - (portfolio.position_count * 0.1))
    
    def _calculate_concentration(self, portfolio: Portfolio) -> float:
        """Calculate position concentration"""
        if portfolio.total_value.amount == 0:
            return 0.0
        
        # Find largest position
        max_position_value = 0.0
        for position in portfolio.positions:
            position_value = float(position.market_value.amount)
            if position_value > max_position_value:
                max_position_value = position_value
        
        return max_position_value / float(portfolio.total_value.amount)
    
    def _generate_risk_alerts(self, portfolio: Portfolio, risk_metrics: Dict[str, Any]) -> List[str]:
        """Generate risk alerts based on metrics"""
        alerts = []
        
        # Check VaR
        if ("var" in risk_metrics
                and risk_metrics["var"] > float(portfolio.total_value.amount) * 0.05):
            alerts.append("High Value at Risk - consider reducing position sizes")
        
        # Check concentration
        if "concentration" in risk_metrics and risk_metrics["concentration"] > 0.3:
            alerts.append("High position concentration - consider diversifying")
        
        # Check drawdown
        if "drawdown" in risk_metrics and risk_metrics["drawdown"] > 0.1:
            alerts.append("Significant drawdown detected - review risk management")
        
        return alerts
    
    def _generate_recommendations(self, portfolio: Portfolio, risk_metrics: Dict[str, Any]) -> List[str]:
        """Generate risk management recommendations"""
        recommendations = []
        
        # Based on volatility
        if "volatility" in risk_metrics and risk_metrics["volatility"] > 0.6:
            recommendations.append("Consider adding defensive positions to reduce volatility")
        
        # Based on correlation
        if "correlation" in risk_metrics and risk_metrics["correlation"] > 0.7:
            recommendations.append("Add uncorrelated assets to improve diversification")
        
        # Based on concentration
        if "concentration" in risk_metrics and risk_metrics["concentration"] > 0.2:
            recommendations.append("Reduce largest position to improve risk distribution")
        
        return recommendations
