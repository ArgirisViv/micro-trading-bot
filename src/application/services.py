# src/application/services.py
# Application Services - High-level Business Operations

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime

from .use_cases import TradingUseCase, PortfolioUseCase, RiskManagementUseCase
from .dto import (
    TradingRequest, TradingResponse, PortfolioUpdate,
    SignalRequest, SignalResponse,
    RiskAssessmentRequest, RiskAssessmentResponse
)


class TradingService(ABC):
    """Abstract trading service"""
    
    @abstractmethod
    def place_order(self, symbol: str, action: str, quantity: int, 
                   price: Optional[float] = None, **kwargs) -> TradingResponse:
        """Place a trading order"""
        pass
    
    @abstractmethod
    def get_account_summary(self) -> Dict[str, Any]:
        """Get account summary"""
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions"""
        pass
    
    @abstractmethod
    def close_position(self, symbol: str) -> TradingResponse:
        """Close a specific position"""
        pass


class PortfolioService(ABC):
    """Abstract portfolio service"""
    
    @abstractmethod
    def create_portfolio(self, name: str, initial_cash: float) -> Dict[str, Any]:
        """Create a new portfolio"""
        pass
    
    @abstractmethod
    def get_portfolio_summary(self, portfolio_id: str) -> Dict[str, Any]:
        """Get portfolio summary"""
        pass
    
    @abstractmethod
    def update_portfolio(self, portfolio_id: str, updates: Dict[str, Any]) -> bool:
        """Update portfolio"""
        pass


class RiskManagementService(ABC):
    """Abstract risk management service"""
    
    @abstractmethod
    def assess_risk(self, portfolio_id: str) -> RiskAssessmentResponse:
        """Assess portfolio risk"""
        pass
    
    @abstractmethod
    def validate_trade(self, portfolio_id: str, trade_request: TradingRequest) -> bool:
        """Validate trade risk"""
        pass
    
    @abstractmethod
    def get_recommendations(self, portfolio_id: str) -> List[str]:
        """Get risk recommendations"""
        pass


class ConcreteTradingService(TradingService):
    """Concrete implementation of trading service"""
    
    def __init__(self, trading_use_case: TradingUseCase):
        self.trading_use_case = trading_use_case
    
    def place_order(self, symbol: str, action: str, quantity: int, 
                   price: Optional[float] = None, **kwargs) -> TradingResponse:
        """Place a trading order with validation"""
        try:
            # Create trading request
            request = TradingRequest(
                symbol=symbol,
                action=action,
                quantity=quantity,
                price=price,
                **kwargs
            )
            
            # Execute trade through use case
            response = self.trading_use_case.execute_trade(request)
            
            return response
            
        except Exception as e:
            return TradingResponse(
                success=False,
                message=f"Failed to place order: {str(e)}",
                error_code="ORDER_PLACEMENT_ERROR"
            )
    
    def get_account_summary(self) -> Dict[str, Any]:
        """Get account summary"""
        try:
            # Get portfolio status (assuming default portfolio)
            portfolio_status = self.trading_use_case.get_portfolio_status("default")
            
            if "error" in portfolio_status:
                return portfolio_status
            
            # Format account summary
            summary = {
                "total_value": portfolio_status.get("total_value", 0),
                "cash": portfolio_status.get("cash", 0),
                "positions_value": portfolio_status.get("total_positions_value", 0),
                "position_count": portfolio_status.get("position_count", 0),
                "open_orders": portfolio_status.get("open_orders_count", 0),
                "unrealized_pnl": portfolio_status.get("total_unrealized_pnl", 0),
                "unrealized_pnl_pct": portfolio_status.get("total_unrealized_pnl_percentage", 0),
                "last_update": portfolio_status.get("last_update", ""),
                "status": "active"
            }
            
            return summary
            
        except Exception as e:
            return {
                "error": f"Failed to get account summary: {str(e)}",
                "status": "error"
            }
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions"""
        try:
            # Get portfolio status
            portfolio_status = self.trading_use_case.get_portfolio_status("default")
            
            if "error" in portfolio_status:
                return []
            
            # Extract positions
            positions = portfolio_status.get("positions", [])
            
            # Format positions
            formatted_positions = []
            for pos in positions:
                formatted_pos = {
                    "symbol": pos.get("symbol", ""),
                    "side": pos.get("side", ""),
                    "quantity": pos.get("quantity", 0),
                    "entry_price": pos.get("entry_price", 0),
                    "current_price": pos.get("current_price", 0),
                    "market_value": pos.get("market_value", 0),
                    "unrealized_pnl": pos.get("unrealized_pnl", 0),
                    "unrealized_pnl_pct": pos.get("unrealized_pnl_percentage", 0),
                    "entry_timestamp": pos.get("entry_timestamp", ""),
                    "last_update": pos.get("last_update", "")
                }
                formatted_positions.append(formatted_pos)
            
            return formatted_positions
            
        except Exception as e:
            return []
    
    def close_position(self, symbol: str) -> TradingResponse:
        """Close a specific position"""
        try:
            # Close position through use case
            response = self.trading_use_case.close_position("default", symbol)
            
            return response
            
        except Exception as e:
            return TradingResponse(
                success=False,
                message=f"Failed to close position: {str(e)}",
                error_code="POSITION_CLOSE_ERROR"
            )


class ConcretePortfolioService(PortfolioService):
    """Concrete implementation of portfolio service"""
    
    def __init__(self, portfolio_use_case: PortfolioUseCase):
        self.portfolio_use_case = portfolio_use_case
    
    def create_portfolio(self, name: str, initial_cash: float) -> Dict[str, Any]:
        """Create a new portfolio"""
        try:
            portfolio = self.portfolio_use_case.create_portfolio(name, initial_cash)
            
            return {
                "success": True,
                "portfolio_id": portfolio.id,
                "name": portfolio.name,
                "initial_cash": float(portfolio.cash.amount),
                "created_at": portfolio.created_at.isoformat(),
                "message": f"Portfolio '{name}' created successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create portfolio: {str(e)}"
            }
    
    def get_portfolio_summary(self, portfolio_id: str) -> Dict[str, Any]:
        """Get portfolio summary"""
        try:
            summary = self.portfolio_use_case.get_portfolio_summary(portfolio_id)
            
            if "error" in summary:
                return summary
            
            return {
                "success": True,
                "portfolio": summary
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get portfolio summary: {str(e)}"
            }
    
    def update_portfolio(self, portfolio_id: str, updates: Dict[str, Any]) -> bool:
        """Update portfolio"""
        try:
            # Create portfolio update DTO
            portfolio_update = PortfolioUpdate(
                portfolio_id=portfolio_id,
                cash_change=updates.get("cash_change", 0),
                positions_added=updates.get("positions_added", []),
                positions_removed=updates.get("positions_removed", []),
                orders_added=updates.get("orders_added", []),
                orders_updated=updates.get("orders_updated", [])
            )
            
            # Update portfolio through use case
            success = self.portfolio_use_case.update_portfolio(portfolio_id, portfolio_update)
            
            return success
            
        except Exception as e:
            return False


class ConcreteRiskManagementService(RiskManagementService):
    """Concrete implementation of risk management service"""
    
    def __init__(self, risk_use_case: RiskManagementUseCase):
        self.risk_use_case = risk_use_case
    
    def assess_risk(self, portfolio_id: str) -> RiskAssessmentResponse:
        """Assess portfolio risk"""
        try:
            # Create risk assessment request
            request = RiskAssessmentRequest(
                portfolio_id=portfolio_id,
                include_positions=True,
                include_orders=True,
                include_historical=False,
                risk_metrics=["var", "sharpe", "drawdown", "volatility", "correlation", "concentration"]
            )
            
            # Assess risk through use case
            response = self.risk_use_case.assess_portfolio_risk(request)
            
            return response
            
        except Exception as e:
            return RiskAssessmentResponse(
                portfolio_id=portfolio_id,
                overall_risk_level="error",
                risk_score=1.0,
                risk_alerts=[f"Risk assessment failed: {str(e)}"],
                recommendations=["Check system logs for details"]
            )
    
    def validate_trade(self, portfolio_id: str, trade_request: TradingRequest) -> bool:
        """Validate trade risk"""
        try:
            # Validate trade through use case
            is_valid = self.risk_use_case.validate_trade_risk(portfolio_id, trade_request)
            
            return is_valid
            
        except Exception as e:
            return False
    
    def get_recommendations(self, portfolio_id: str) -> List[str]:
        """Get risk recommendations"""
        try:
            # Get recommendations through use case
            recommendations = self.risk_use_case.get_risk_recommendations(portfolio_id)
            
            return recommendations
            
        except Exception as e:
            return [f"Failed to get recommendations: {str(e)}"]


# Service Factory for dependency injection
class ServiceFactory:
    """Factory for creating service instances"""
    
    def __init__(self):
        self._services = {}
    
    def register_service(self, name: str, service_class: type):
        """Register a service class"""
        self._services[name] = service_class
    
    def create_service(self, name: str, **kwargs) -> Any:
        """Create service instance"""
        if name not in self._services:
            raise ValueError(f"Unknown service: {name}")
        
        service_class = self._services[name]
        return service_class(**kwargs)
    
    def get_available_services(self) -> List[str]:
        """Get list of available service names"""
        return list(self._services.keys())


# Trading Bot Service - Main orchestration service
class TradingBotService:
    """Main trading bot service that orchestrates all operations"""
    
    def __init__(self,
                 trading_service: TradingService,
                 portfolio_service: PortfolioService,
                 risk_service: RiskManagementService):
        self.trading_service = trading_service
        self.portfolio_service = portfolio_service
        self.risk_service = risk_service
    
    def start_trading_session(self) -> Dict[str, Any]:
        """Start a new trading session"""
        try:
            # Get account summary
            account_summary = self.trading_service.get_account_summary()
            
            # Assess current risk
            risk_assessment = self.risk_service.assess_risk("default")
            
            # Get recommendations
            recommendations = self.risk_service.get_recommendations("default")
            
            session_info = {
                "status": "started",
                "timestamp": datetime.now().isoformat(),
                "account_summary": account_summary,
                "risk_assessment": {
                    "overall_risk": risk_assessment.overall_risk_level,
                    "risk_score": risk_assessment.risk_score,
                    "alerts": risk_assessment.risk_alerts
                },
                "recommendations": recommendations,
                "message": "Trading session started successfully"
            }
            
            return session_info
            
        except Exception as e:
            return {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": f"Failed to start trading session: {str(e)}"
            }
    
    def execute_trading_strategy(self, strategy_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trading strategy based on configuration"""
        try:
            results = {
                "status": "executed",
                "timestamp": datetime.now().isoformat(),
                "trades_executed": [],
                "signals_generated": [],
                "risk_checks_passed": [],
                "errors": []
            }
            
            # Get symbols to trade
            symbols = strategy_config.get("symbols", [])
            
            for symbol in symbols:
                try:
                    # Generate trading signal (simplified)
                    signal = self._generate_trading_signal(symbol, strategy_config)
                    
                    if signal:
                        # Validate trade risk
                        trade_request = TradingRequest(
                            symbol=symbol,
                            action=signal["action"],
                            quantity=signal["quantity"],
                            price=signal["price"]
                        )
                        
                        is_valid = self.risk_service.validate_trade("default", trade_request)
                        
                        if is_valid:
                            # Execute trade
                            trade_response = self.trading_service.place_order(
                                symbol=symbol,
                                action=signal["action"],
                                quantity=signal["quantity"],
                                price=signal["price"]
                            )
                            
                            if trade_response.success:
                                results["trades_executed"].append({
                                    "symbol": symbol,
                                    "action": signal["action"],
                                    "quantity": signal["quantity"],
                                    "order_id": trade_response.order_id
                                })
                            else:
                                results["errors"].append({
                                    "symbol": symbol,
                                    "error": trade_response.message
                                })
                        else:
                            results["risk_checks_passed"].append({
                                "symbol": symbol,
                                "status": "rejected",
                                "reason": "Risk validation failed"
                            })
                    
                    results["signals_generated"].append({
                        "symbol": symbol,
                        "signal": signal
                    })
                    
                except Exception as e:
                    results["errors"].append({
                        "symbol": symbol,
                        "error": str(e)
                    })
            
            return results
            
        except Exception as e:
            return {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": f"Strategy execution failed: {str(e)}"
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        try:
            # Get account status
            account_summary = self.trading_service.get_account_summary()
            
            # Get positions
            positions = self.trading_service.get_positions()
            
            # Get risk assessment
            risk_assessment = self.risk_service.assess_risk("default")
            
            # Get portfolio summary
            portfolio_summary = self.portfolio_service.get_portfolio_summary("default")
            
            status = {
                "timestamp": datetime.now().isoformat(),
                "system_status": "operational",
                "account": account_summary,
                "positions": positions,
                "risk": {
                    "level": risk_assessment.overall_risk_level,
                    "score": risk_assessment.risk_score,
                    "alerts": risk_assessment.risk_alerts
                },
                "portfolio": portfolio_summary.get("portfolio", {}) if portfolio_summary.get("success") else {},
                "last_update": datetime.now().isoformat()
            }
            
            return status
            
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "system_status": "error",
                "error": f"Failed to get system status: {str(e)}"
            }
    
    def _generate_trading_signal(self, symbol: str, strategy_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate trading signal for symbol (simplified)"""
        try:
            # This is a simplified signal generation
            # In a real implementation, you'd use the strategy service
            
            # Random signal generation for demonstration
            import random
            
            signal_type = random.choice(["buy", "sell", "hold"])
            
            if signal_type == "hold":
                return None
            
            # Generate random quantity and price
            quantity = random.randint(1, 100)
            price = random.uniform(10.0, 1000.0)
            
            return {
                "action": signal_type,
                "quantity": quantity,
                "price": round(price, 2),
                "confidence": random.uniform(0.6, 0.9),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return None
