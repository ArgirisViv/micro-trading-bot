# src/main.py
# Main Application Entry Point for Micro Trading Bot

import os
import sys
import logging
import argparse
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from .application.services import TradingBotService, ServiceFactory
from .infrastructure.services import InfrastructureServiceFactory
from .presentation.services import TradingBotDashboard, TradingBotCLI
from .domain.entities import Portfolio
from .domain.services import (
    ConcreteRiskManagementService as DomainRiskManagementService,
    ConcreteStrategyService,
)
from .domain.repositories import (
    TradingRepository, DataRepository, NotificationRepository,
    ConfigurationRepository, PerformanceRepository, PortfolioRepository
)


class TradingBotApplication:
    """Main trading bot application class"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = self._setup_logging()
        self.trading_bot_service = None
        self.infrastructure_factory = None
        
    def _setup_logging(self) -> logging.Logger:
        """Setup application logging"""
        logger = logging.getLogger("trading_bot")
        logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler
        log_file = self.config.get("log_file", "trading_bot.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    def initialize_services(self) -> bool:
        """Initialize all services and dependencies"""
        try:
            self.logger.info("🚀 Initializing Micro Trading Bot services...")
            
            # Initialize infrastructure services
            self.infrastructure_factory = InfrastructureServiceFactory()
            self.infrastructure_factory.configure(self.config)
            
            # Create infrastructure services
            data_provider = self.infrastructure_factory.create_data_provider("alpaca")
            trading_api = self.infrastructure_factory.create_trading_api("alpaca")
            notification_service = self.infrastructure_factory.create_notification_service("telegram")
            database_service = self.infrastructure_factory.create_database_service("sqlite")
            
            # Create in-memory repositories (for now)
            trading_repo = InMemoryTradingRepository()
            data_repo = InMemoryDataRepository()
            notification_repo = InMemoryNotificationRepository()
            config_repo = InMemoryConfigurationRepository()
            
            # Initialize application services
            service_factory = ServiceFactory()
            
            # Create use cases (simplified for now)
            from .application.use_cases import (
                ConcreteTradingUseCase, ConcretePortfolioUseCase, ConcreteRiskManagementUseCase
            )

            domain_risk_service = DomainRiskManagementService()
            trading_use_case = ConcreteTradingUseCase(
                trading_repo,
                data_repo,
                ConcreteStrategyService(data_repo),
                domain_risk_service,
            )
            portfolio_use_case = ConcretePortfolioUseCase(
                trading_repo
            )
            risk_use_case = ConcreteRiskManagementUseCase(
                trading_repo, domain_risk_service
            )
            
            # Create application services
            from .application.services import (
                ConcreteTradingService, ConcretePortfolioService, ConcreteRiskManagementService
            )
            
            service_factory.register_service("ConcreteTradingService", ConcreteTradingService)
            service_factory.register_service("ConcretePortfolioService", ConcretePortfolioService)
            service_factory.register_service("ConcreteRiskManagementService", ConcreteRiskManagementService)

            trading_service = service_factory.create_service(
                "ConcreteTradingService",
                trading_use_case=trading_use_case
            )
            portfolio_service = service_factory.create_service(
                "ConcretePortfolioService",
                portfolio_use_case=portfolio_use_case
            )
            risk_service = service_factory.create_service(
                "ConcreteRiskManagementService",
                risk_use_case=risk_use_case
            )
            
            # Create main trading bot service
            self.trading_bot_service = TradingBotService(
                trading_service=trading_service,
                portfolio_service=portfolio_service,
                risk_service=risk_service
            )
            
            self.logger.info("✅ All services initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize services: {e}")
            return False
    
    def run_dashboard(self) -> None:
        """Run the Streamlit dashboard"""
        try:
            self.logger.info("📊 Starting Streamlit dashboard...")
            
            if not self.trading_bot_service:
                self.logger.error("❌ Trading bot service not initialized")
                return
            
            dashboard = TradingBotDashboard(self.trading_bot_service)
            dashboard.run()
            
        except Exception as e:
            self.logger.error(f"❌ Dashboard error: {e}")
    
    def run_cli(self) -> None:
        """Run the command-line interface"""
        try:
            self.logger.info("💻 Starting CLI interface...")
            
            if not self.trading_bot_service:
                self.logger.error("❌ Trading bot service not initialized")
                return
            
            cli = TradingBotCLI(self.trading_bot_service)
            cli.run()
            
        except Exception as e:
            self.logger.error(f"❌ CLI error: {e}")
    
    def run_trading_loop(self) -> None:
        """Run the main trading loop"""
        try:
            self.logger.info("🔄 Starting trading loop...")
            
            if not self.trading_bot_service:
                self.logger.error("❌ Trading bot service not initialized")
                return
            
            # Start trading session
            session_info = self.trading_bot_service.start_trading_session()
            self.logger.info(f"Trading session started: {session_info}")
            
            # Run continuous trading loop
            while True:
                try:
                    # Get system status
                    status = self.trading_bot_service.get_system_status()
                    self.logger.info(f"System status: {status.get('system_status', 'Unknown')}")
                    
                    # Execute trading strategy (if configured)
                    if self.config.get("auto_trading", False):
                        strategy_config = self.config.get("strategy", {})
                        results = self.trading_bot_service.execute_trading_strategy(strategy_config)
                        self.logger.info(f"Strategy execution results: {results}")
                    
                    # Wait for next iteration
                    import time
                    time.sleep(self.config.get("loop_interval", 60))  # Default: 1 minute
                    
                except KeyboardInterrupt:
                    self.logger.info("🛑 Trading loop interrupted by user")
                    break
                except Exception as e:
                    self.logger.error(f"❌ Trading loop error: {e}")
                    time.sleep(30)  # Wait before retrying
            
        except Exception as e:
            self.logger.error(f"❌ Trading loop error: {e}")
    
    def run(self, mode: str) -> None:
        """Run the application in specified mode"""
        try:
            # Initialize services
            if not self.initialize_services():
                self.logger.error("❌ Failed to initialize services. Exiting.")
                return
            
            # Run based on mode
            if mode == "dashboard":
                self.run_dashboard()
            elif mode == "cli":
                self.run_cli()
            elif mode == "trading":
                self.run_trading_loop()
            else:
                self.logger.error(f"❌ Unknown mode: {mode}")
                
        except Exception as e:
            self.logger.error(f"❌ Application error: {e}")


# In-Memory Repository Implementations (for development/testing)
class InMemoryTradingRepository(TradingRepository):
    """In-memory implementation of trading repository"""
    
    def __init__(self):
        self.orders = {}
        self.positions = {}
        self.portfolios: dict[str, Portfolio] = {}
        self._default_portfolio_id: str | None = None
        self.logger = logging.getLogger(__name__)

    def get_portfolio(self, portfolio_id: str) -> Portfolio | None:
        if portfolio_id == "default" and self._default_portfolio_id is not None:
            portfolio_id = self._default_portfolio_id
        return self.portfolios.get(portfolio_id)

    def save_portfolio(self, portfolio: Portfolio) -> bool:
        self.portfolios[portfolio.id] = portfolio
        if self._default_portfolio_id is None:
            self._default_portfolio_id = portfolio.id
        return True
    
    def save_order(self, order: Any) -> bool:
        """Save order to in-memory storage"""
        try:
            self.orders[order.id] = order
            return True
        except Exception as e:
            self.logger.error(f"Failed to save order: {e}")
            return False
    
    def get_order(self, order_id: str) -> Optional[Any]:
        """Get order by ID"""
        return self.orders.get(order_id)
    
    def get_orders_by_symbol(self, symbol: str) -> List[Any]:
        """Get all orders for a symbol"""
        return [order for order in self.orders.values() if order.symbol == symbol]
    
    def get_open_orders(self) -> List[Any]:
        """Get all open orders"""
        return [order for order in self.orders.values() if order.status == "pending"]
    
    def get_filled_orders(self, start_date: Optional[datetime] = None, 
                         end_date: Optional[datetime] = None) -> List[Any]:
        """Get filled orders within date range"""
        return [order for order in self.orders.values() if order.status == "filled"]
    
    def update_order_status(self, order_id: str, status: str, 
                          filled_price: Optional[float] = None,
                          filled_quantity: Optional[int] = None) -> bool:
        """Update order status"""
        if order_id in self.orders:
            order = self.orders[order_id]
            order.status = status
            if filled_price is not None:
                order.filled_price = filled_price
            if filled_quantity is not None:
                order.filled_quantity = filled_quantity
            return True
        return False
    
    def save_position(self, position: Any) -> bool:
        """Save position to in-memory storage"""
        try:
            self.positions[position.symbol] = position
            return True
        except Exception as e:
            self.logger.error(f"Failed to save position: {e}")
            return False
    
    def get_position(self, symbol: str) -> Optional[Any]:
        """Get position by symbol"""
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> List[Any]:
        """Get all positions"""
        return list(self.positions.values())
    
    def update_position_price(self, symbol: str, new_price: float) -> bool:
        """Update position current price"""
        if symbol in self.positions:
            self.positions[symbol].current_price = new_price
            return True
        return False
    
    def close_position(self, symbol: str) -> bool:
        """Close position (remove from repository)"""
        if symbol in self.positions:
            del self.positions[symbol]
            return True
        return False
    
    def get_position_history(self, symbol: str, 
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> List[Any]:
        """Get position history for symbol"""
        # For in-memory, just return current position if exists
        position = self.positions.get(symbol)
        return [position] if position else []


class InMemoryDataRepository(DataRepository):
    """In-memory implementation of data repository"""
    
    def __init__(self):
        self.market_data = {}
        self.logger = logging.getLogger(__name__)
    
    def save_market_data(self, symbol: str, data: Any, 
                        timestamp: Optional[datetime] = None) -> bool:
        """Save market data"""
        try:
            self.market_data[symbol] = data
            return True
        except Exception as e:
            self.logger.error(f"Failed to save market data: {e}")
            return False
    
    def get_market_data(self, symbol: str, 
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None,
                       limit: Optional[int] = None) -> Optional[Any]:
        """Get market data"""
        return self.market_data.get(symbol)
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest price for symbol"""
        data = self.market_data.get(symbol)
        if data is not None and hasattr(data, 'iloc'):
            return data['close'].iloc[-1] if 'close' in data.columns else None
        return None
    
    def get_symbols(self) -> List[str]:
        """Get all available symbols"""
        return list(self.market_data.keys())
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get symbol information"""
        return {"symbol": symbol, "name": symbol, "exchange": "UNKNOWN"}
    
    def save_technical_indicators(self, symbol: str, indicators: Dict[str, Any],
                                timestamp: Optional[datetime] = None) -> bool:
        """Save technical indicators for symbol"""
        try:
            if symbol not in self.market_data:
                self.market_data[symbol] = {}
            self.market_data[symbol]['indicators'] = indicators
            return True
        except Exception as e:
            self.logger.error(f"Failed to save technical indicators: {e}")
            return False
    
    def get_technical_indicators(self, symbol: str,
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """Get technical indicators for symbol"""
        data = self.market_data.get(symbol, {})
        return data.get('indicators')


class InMemoryNotificationRepository(NotificationRepository):
    """In-memory implementation of notification repository"""
    
    def __init__(self):
        self.notifications = []
        self.logger = logging.getLogger(__name__)
    
    def save_notification(self, notification: Any) -> bool:
        """Save notification"""
        try:
            self.notifications.append(notification)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save notification: {e}")
            return False
    
    def get_notifications(self, limit: int = 100, 
                         notification_type: Optional[str] = None) -> List[Any]:
        """Get recent notifications"""
        notifications = self.notifications[-limit:] if limit > 0 else self.notifications
        if notification_type:
            notifications = [n for n in notifications if n.get('type') == notification_type]
        return notifications
    
    def mark_as_read(self, notification_id: str) -> bool:
        """Mark notification as read"""
        for notification in self.notifications:
            if notification.get('id') == notification_id:
                notification['read'] = True
                return True
        return False
    
    def get_unread_count(self) -> int:
        """Get count of unread notifications"""
        return len([n for n in self.notifications if not n.get('read', False)])
    
    def delete_notification(self, notification_id: str) -> bool:
        """Delete notification"""
        self.notifications = [n for n in self.notifications if n.get('id') != notification_id]
        return True


class InMemoryConfigurationRepository(ConfigurationRepository):
    """In-memory implementation of configuration repository"""
    
    def __init__(self):
        self.config = {}
        self.logger = logging.getLogger(__name__)
    
    def save_configuration(self, key: str, value: Any) -> bool:
        """Save configuration"""
        try:
            self.config[key] = value
            return True
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            return False
    
    def get_configuration(self, key: str, default: Any = None) -> Any:
        """Get configuration"""
        return self.config.get(key, default)
    
    def get_all_configurations(self) -> Dict[str, Any]:
        """Get all configuration values"""
        return self.config.copy()
    
    def delete_configuration(self, key: str) -> bool:
        """Delete configuration"""
        if key in self.config:
            del self.config[key]
            return True
        return False
    
    def has_configuration(self, key: str) -> bool:
        """Check if configuration exists"""
        return key in self.config
    
    def get_configuration_keys(self) -> List[str]:
        """Get all configuration keys"""
        return list(self.config.keys())


class InMemoryPerformanceRepository(PerformanceRepository):
    """In-memory implementation of performance repository"""
    
    def __init__(self):
        self.metrics = {}
        self.logger = logging.getLogger(__name__)
    
    def save_performance_metric(self, metric_name: str, value: float, 
                               timestamp: Optional[datetime] = None,
                               metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Save performance metric"""
        try:
            if metric_name not in self.metrics:
                self.metrics[metric_name] = []
            
            self.metrics[metric_name].append({
                "value": value,
                "timestamp": timestamp or datetime.now(),
                "metadata": metadata or {}
            })
            return True
        except Exception as e:
            self.logger.error(f"Failed to save performance metric: {e}")
            return False
    
    def get_performance_metrics(self, metric_name: str, 
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None,
                               limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get performance metrics"""
        metrics = self.metrics.get(metric_name, [])
        
        # Apply date filters
        if start_date:
            metrics = [m for m in metrics if m['timestamp'] >= start_date]
        if end_date:
            metrics = [m for m in metrics if m['timestamp'] <= end_date]
        
        # Apply limit
        if limit:
            metrics = metrics[-limit:]
        
        return metrics
    
    def get_latest_metric(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """Get latest value for metric"""
        metrics = self.metrics.get(metric_name, [])
        return metrics[-1] if metrics else None
    
    def get_metric_names(self) -> List[str]:
        """Get all available metric names"""
        return list(self.metrics.keys())
    
    def calculate_average(self, metric_name: str,
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None) -> Optional[float]:
        """Calculate average for metric"""
        metrics = self.get_performance_metrics(metric_name, start_date, end_date)
        if not metrics:
            return None
        
        values = [m['value'] for m in metrics]
        return sum(values) / len(values)
    
    def calculate_sum(self, metric_name: str,
                     start_date: Optional[datetime] = None,
                     end_date: Optional[datetime] = None) -> Optional[float]:
        """Calculate sum for metric"""
        metrics = self.get_performance_metrics(metric_name, start_date, end_date)
        if not metrics:
            return None
        
        values = [m['value'] for m in metrics]
        return sum(values)
    
    def get_metric_statistics(self, metric_name: str,
                            start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None) -> Optional[Dict[str, float]]:
        """Get statistical summary for metric"""
        metrics = self.get_performance_metrics(metric_name, start_date, end_date)
        if not metrics:
            return None
        
        values = [m['value'] for m in metrics]
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "std": (sum((x - sum(values)/len(values))**2 for x in values) / len(values))**0.5
        }


class InMemoryPortfolioRepository(PortfolioRepository):
    """In-memory implementation of portfolio repository"""
    
    def __init__(self):
        self.portfolios = {}
        self.logger = logging.getLogger(__name__)
    
    def save_portfolio(self, portfolio: Any) -> bool:
        """Save portfolio to repository"""
        try:
            self.portfolios[portfolio.id] = portfolio
            return True
        except Exception as e:
            self.logger.error(f"Failed to save portfolio: {e}")
            return False
    
    def get_portfolio(self, portfolio_id: str) -> Optional[Any]:
        """Get portfolio by ID"""
        return self.portfolios.get(portfolio_id)
    
    def get_portfolio_by_name(self, name: str) -> Optional[Any]:
        """Get portfolio by name"""
        for portfolio in self.portfolios.values():
            if portfolio.name == name:
                return portfolio
        return None
    
    def get_all_portfolios(self) -> List[Any]:
        """Get all portfolios"""
        return list(self.portfolios.values())
    
    def update_portfolio_cash(self, portfolio_id: str, new_cash: float) -> bool:
        """Update portfolio cash balance"""
        if portfolio_id in self.portfolios:
            self.portfolios[portfolio_id].cash = new_cash
            return True
        return False
    
    def add_portfolio_position(self, portfolio_id: str, position: Any) -> bool:
        """Add position to portfolio"""
        if portfolio_id in self.portfolios:
            self.portfolios[portfolio_id].add_position(position)
            return True
        return False
    
    def remove_portfolio_position(self, portfolio_id: str, symbol: str) -> bool:
        """Remove position from portfolio"""
        if portfolio_id in self.portfolios:
            self.portfolios[portfolio_id].remove_position(symbol)
            return True
        return False
    
    def add_portfolio_order(self, portfolio_id: str, order: Any) -> bool:
        """Add order to portfolio"""
        if portfolio_id in self.portfolios:
            self.portfolios[portfolio_id].add_order(order)
            return True
        return False
    
    def get_portfolio_positions(self, portfolio_id: str) -> List[Any]:
        """Get all positions for portfolio"""
        portfolio = self.portfolios.get(portfolio_id)
        return portfolio.positions if portfolio else []
    
    def get_portfolio_orders(self, portfolio_id: str) -> List[Any]:
        """Get all orders for portfolio"""
        portfolio = self.portfolios.get(portfolio_id)
        return portfolio.orders if portfolio else []
    
    def delete_portfolio(self, portfolio_id: str) -> bool:
        """Delete portfolio"""
        if portfolio_id in self.portfolios:
            del self.portfolios[portfolio_id]
            return True
        return False


def load_configuration() -> Dict[str, Any]:
    """Load configuration from environment and config files"""
    config = {
        # Default configuration
        "log_file": "trading_bot.log",
        "loop_interval": 60,
        "auto_trading": False,
        "strategy": {
            "symbols": ["AAPL", "GOOGL", "MSFT"],
            "risk_per_trade": 0.02,
            "max_positions": 5
        }
    }
    
    # Load from environment variables
    config.update({
        "alpaca_api_key": os.getenv("ALPACA_API_KEY"),
        "alpaca_secret_key": os.getenv("ALPACA_SECRET_KEY"),
        "alpaca_base_url": os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets"),
        "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
        "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID"),
        "sqlite_db_path": os.getenv("SQLITE_DB_PATH", "trading_bot.db")
    })
    
    # Load from config file if exists
    config_file = os.getenv("CONFIG_FILE", "config.py")
    if os.path.exists(config_file):
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("config", config_file)
            if spec is None or spec.loader is None:
                raise ImportError(f"Unable to load configuration module from {config_file}")
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            
            # Update config with file values
            for key in dir(config_module):
                if not key.startswith("_") and key.isupper():
                    config[key.lower()] = getattr(config_module, key)
                    
        except Exception as e:
            print(f"Warning: Failed to load config file {config_file}: {e}")
    
    return config


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Micro Trading Bot")
    parser.add_argument(
        "mode",
        choices=["dashboard", "cli", "trading"],
        help="Application mode to run"
    )
    parser.add_argument(
        "--config",
        help="Configuration file path"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Load configuration
    if args.config:
        os.environ["CONFIG_FILE"] = args.config
    
    config = load_configuration()
    
    # Create and run application
    app = TradingBotApplication(config)
    app.run(args.mode)


if __name__ == "__main__":
    main()
