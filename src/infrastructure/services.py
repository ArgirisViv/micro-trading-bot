# src/infrastructure/services.py
# Infrastructure Services - External Interfaces & Data Access

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
import pandas as pd
import requests
import json
import logging
from datetime import datetime, timedelta
import time

from ..domain.repositories import (
    TradingRepository, DataRepository, NotificationRepository,
    ConfigurationRepository, PerformanceRepository
)
from ..domain.entities import Order, Position, TradingSignal
from ..domain.value_objects import Money, Percentage


class DataProviderService(ABC):
    """Abstract data provider service"""
    
    @abstractmethod
    def get_market_data(self, symbol: str, timeframe: str, 
                       start_date: Optional[str] = None, 
                       end_date: Optional[str] = None) -> pd.DataFrame:
        """Get market data for symbol"""
        pass
    
    @abstractmethod
    def get_real_time_price(self, symbol: str) -> float:
        """Get real-time price for symbol"""
        pass
    
    @abstractmethod
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get symbol information"""
        pass


class TradingAPIService(ABC):
    """Abstract trading API service"""
    
    @abstractmethod
    def place_order(self, order: Order) -> Dict[str, Any]:
        """Place order through API"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel order through API"""
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status from API"""
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions from API"""
        pass
    
    @abstractmethod
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information from API"""
        pass


class NotificationService(ABC):
    """Abstract notification service"""
    
    @abstractmethod
    def send_notification(self, message: str, level: str = "info", 
                         channels: Optional[List[str]] = None) -> bool:
        """Send notification through configured channels"""
        pass
    
    @abstractmethod
    def send_alert(self, alert_type: str, message: str, 
                   data: Optional[Dict[str, Any]] = None) -> bool:
        """Send alert notification"""
        pass


class DatabaseService(ABC):
    """Abstract database service"""
    
    @abstractmethod
    def save_trade(self, trade_data: Dict[str, Any]) -> bool:
        """Save trade data to database"""
        pass
    
    @abstractmethod
    def get_trade_history(self, symbol: str, 
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get trade history from database"""
        pass
    
    @abstractmethod
    def save_performance_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Save performance metrics to database"""
        pass


# Concrete Implementations

class AlpacaDataProvider(DataProviderService):
    """Alpaca market data provider implementation"""
    
    def __init__(self, api_key: str, secret_key: str, base_url: str = "https://paper-api.alpaca.markets"):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key
        })
        self.logger = logging.getLogger(__name__)
    
    def get_market_data(self, symbol: str, timeframe: str, 
                       start_date: Optional[str] = None, 
                       end_date: Optional[str] = None) -> pd.DataFrame:
        """Get market data from Alpaca"""
        try:
            # Convert timeframe to Alpaca format
            alpaca_timeframe = self._convert_timeframe(timeframe)
            
            # Build URL
            url = f"{self.base_url}/v2/stocks/{symbol}/bars"
            params = {
                "timeframe": alpaca_timeframe,
                "limit": 1000  # Max limit
            }
            
            if start_date:
                params["start"] = start_date
            if end_date:
                params["end"] = end_date
            
            # Make request
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get("bars"):
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(data["bars"])
            
            # Rename columns to match expected format
            column_mapping = {
                "t": "timestamp",
                "o": "open",
                "h": "high",
                "l": "low",
                "c": "close",
                "v": "volume"
            }
            
            df = df.rename(columns=column_mapping)
            
            # Convert timestamp to datetime
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.set_index("timestamp")
            
            # Convert to numeric
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Failed to get market data for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_real_time_price(self, symbol: str) -> float:
        """Get real-time price from Alpaca"""
        try:
            url = f"{self.base_url}/v2/stocks/{symbol}/trades/latest"
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            return float(data["trade"]["p"])
            
        except Exception as e:
            self.logger.error(f"Failed to get real-time price for {symbol}: {e}")
            return 0.0
    
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get symbol information from Alpaca"""
        try:
            url = f"{self.base_url}/v2/assets/{symbol}"
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                "symbol": data["symbol"],
                "name": data.get("name", ""),
                "exchange": data.get("exchange", ""),
                "asset_class": data.get("class", ""),
                "status": data.get("status", ""),
                "tradable": data.get("tradable", False),
                "marginable": data.get("marginable", False),
                "shortable": data.get("shortable", False),
                "easy_to_borrow": data.get("easy_to_borrow", False)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get symbol info for {symbol}: {e}")
            return {}
    
    def _convert_timeframe(self, timeframe: str) -> str:
        """Convert internal timeframe to Alpaca format"""
        mapping = {
            "1min": "1Min",
            "5min": "5Min",
            "15min": "15Min",
            "30min": "30Min",
            "1h": "1Hour",
            "1d": "1Day"
        }
        return mapping.get(timeframe, "1Min")


class AlpacaTradingAPI(TradingAPIService):
    """Alpaca trading API implementation"""
    
    def __init__(self, api_key: str, secret_key: str, base_url: str = "https://paper-api.alpaca.markets"):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key,
            "Content-Type": "application/json"
        })
        self.logger = logging.getLogger(__name__)
    
    def place_order(self, order: Order) -> Dict[str, Any]:
        """Place order through Alpaca API"""
        try:
            url = f"{self.base_url}/v2/orders"
            
            # Convert order to Alpaca format
            order_data = {
                "symbol": order.symbol,
                "qty": str(order.quantity),
                "side": order.side.value,
                "type": order.order_type,
                "time_in_force": "day"
            }
            
            # Add price for limit orders
            if order.order_type == "limit" and order.price:
                order_data["limit_price"] = str(float(order.price.amount))
            
            # Add stop loss and take profit
            if order.stop_loss:
                order_data["stop_loss"] = {
                    "stop_price": str(float(order.stop_loss.amount))
                }
            
            if order.take_profit:
                order_data["take_profit"] = {
                    "limit_price": str(float(order.take_profit.amount))
                }
            
            # Make request
            response = self.session.post(url, json=order_data)
            response.raise_for_status()
            
            result = response.json()
            
            return {
                "success": True,
                "order_id": result["id"],
                "status": result["status"],
                "filled_at": result.get("filled_at"),
                "filled_qty": result.get("filled_qty"),
                "filled_avg_price": result.get("filled_avg_price")
            }
            
        except Exception as e:
            self.logger.error(f"Failed to place order: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel order through Alpaca API"""
        try:
            url = f"{self.base_url}/v2/orders/{order_id}"
            response = self.session.delete(url)
            response.raise_for_status()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status from Alpaca API"""
        try:
            url = f"{self.base_url}/v2/orders/{order_id}"
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                "order_id": data["id"],
                "symbol": data["symbol"],
                "side": data["side"],
                "quantity": data["qty"],
                "status": data["status"],
                "order_type": data["type"],
                "created_at": data["created_at"],
                "filled_at": data.get("filled_at"),
                "filled_qty": data.get("filled_qty"),
                "filled_avg_price": data.get("filled_avg_price")
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get order status for {order_id}: {e}")
            return {}
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions from Alpaca API"""
        try:
            url = f"{self.base_url}/v2/positions"
            response = self.session.get(url)
            response.raise_for_status()
            
            positions = response.json()
            
            formatted_positions = []
            for pos in positions:
                formatted_pos = {
                    "symbol": pos["symbol"],
                    "side": pos["side"],
                    "quantity": pos["qty"],
                    "entry_price": pos["avg_entry_price"],
                    "current_price": pos["current_price"],
                    "market_value": pos["market_value"],
                    "unrealized_pnl": pos["unrealized_pl"],
                    "unrealized_pnl_pct": pos["unrealized_plpc"],
                    "entry_timestamp": pos.get("created_at", ""),
                    "last_update": pos.get("updated_at", "")
                }
                formatted_positions.append(formatted_pos)
            
            return formatted_positions
            
        except Exception as e:
            self.logger.error(f"Failed to get positions: {e}")
            return []
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information from Alpaca API"""
        try:
            url = f"{self.base_url}/v2/account"
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                "account_id": data["id"],
                "status": data["status"],
                "currency": data["currency"],
                "cash": data["cash"],
                "portfolio_value": data["portfolio_value"],
                "pattern_day_trader": data["pattern_day_trader"],
                "trading_blocked": data["trading_blocked"],
                "transfers_blocked": data["transfers_blocked"],
                "account_blocked": data["account_blocked"],
                "created_at": data["created_at"],
                "trade_suspended_by_user": data["trade_suspended_by_user"],
                "multiplier": data["multiplier"],
                "shorting_enabled": data["shorting_enabled"],
                "equity": data["equity"],
                "last_equity": data["last_equity"],
                "long_market_value": data["long_market_value"],
                "short_market_value": data["short_market_value"],
                "initial_margin": data["initial_margin"],
                "maintenance_margin": data["maintenance_margin"],
                "last_maintenance_margin": data["last_maintenance_margin"],
                "sma": data["sma"],
                "daytrade_count": data["daytrade_count"]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get account info: {e}")
            return {}


class TelegramNotificationService(NotificationService):
    """Telegram notification service implementation"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.logger = logging.getLogger(__name__)
    
    def send_notification(self, message: str, level: str = "info", 
                         channels: Optional[List[str]] = None) -> bool:
        """Send notification through Telegram"""
        try:
            # Add level emoji
            level_emojis = {
                "info": "ℹ️",
                "warning": "⚠️",
                "error": "❌",
                "success": "✅",
                "alert": "🚨"
            }
            
            emoji = level_emojis.get(level, "ℹ️")
            formatted_message = f"{emoji} {message}"
            
            # Send to Telegram
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": formatted_message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, json=data)
            response.raise_for_status()
            
            self.logger.info(f"Telegram notification sent: {message}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send Telegram notification: {e}")
            return False
    
    def send_alert(self, alert_type: str, message: str, 
                   data: Optional[Dict[str, Any]] = None) -> bool:
        """Send alert notification"""
        try:
            # Format alert message
            alert_emojis = {
                "trade": "💰",
                "risk": "⚠️",
                "system": "🔧",
                "performance": "📊",
                "error": "🚨"
            }
            
            emoji = alert_emojis.get(alert_type, "🔔")
            
            if data:
                # Add data details
                details = "\n".join([f"• {k}: {v}" for k, v in data.items()])
                formatted_message = f"{emoji} <b>{alert_type.upper()} ALERT</b>\n\n{message}\n\n<code>{details}</code>"
            else:
                formatted_message = f"{emoji} <b>{alert_type.upper()} ALERT</b>\n\n{message}"
            
            # Send alert
            return self.send_notification(formatted_message, level="alert")
            
        except Exception as e:
            self.logger.error(f"Failed to send alert: {e}")
            return False


class SQLiteDatabaseService(DatabaseService):
    """SQLite database service implementation"""
    
    def __init__(self, db_path: str = "trading_bot.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables"""
        try:
            import sqlite3
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create trades table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT UNIQUE,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            
            # Create performance_metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    metadata TEXT
                )
            """)
            
            conn.commit()
            conn.close()
            
            self.logger.info("Database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
    
    def save_trade(self, trade_data: Dict[str, Any]) -> bool:
        """Save trade data to database"""
        try:
            import sqlite3
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO trades 
                (order_id, symbol, side, quantity, price, timestamp, status, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_data.get("order_id", ""),
                trade_data.get("symbol", ""),
                trade_data.get("side", ""),
                trade_data.get("quantity", 0),
                trade_data.get("price", 0.0),
                trade_data.get("timestamp", ""),
                trade_data.get("status", ""),
                json.dumps(trade_data.get("metadata", {}))
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Trade saved: {trade_data.get('order_id')}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save trade: {e}")
            return False
    
    def get_trade_history(self, symbol: str, 
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get trade history from database"""
        try:
            import sqlite3
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT * FROM trades WHERE symbol = ?"
            params = [symbol]
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date)
            
            query += " ORDER BY timestamp DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            trades = []
            for row in rows:
                trade = {
                    "id": row[0],
                    "order_id": row[1],
                    "symbol": row[2],
                    "side": row[3],
                    "quantity": row[4],
                    "price": row[5],
                    "timestamp": row[6],
                    "status": row[7],
                    "metadata": json.loads(row[8]) if row[8] else {}
                }
                trades.append(trade)
            
            conn.close()
            return trades
            
        except Exception as e:
            self.logger.error(f"Failed to get trade history: {e}")
            return []
    
    def save_performance_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Save performance metrics to database"""
        try:
            import sqlite3
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            timestamp = metrics.get("timestamp", datetime.now().isoformat())
            
            for metric_name, metric_value in metrics.items():
                if metric_name == "timestamp":
                    continue
                
                if isinstance(metric_value, (int, float)):
                    cursor.execute("""
                        INSERT INTO performance_metrics 
                        (timestamp, metric_name, metric_value, metadata)
                        VALUES (?, ?, ?, ?)
                    """, (
                        timestamp,
                        metric_name,
                        metric_value,
                        json.dumps(metrics.get("metadata", {}))
                    ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Performance metrics saved: {len(metrics)} metrics")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save performance metrics: {e}")
            return False


# Service Factory for Infrastructure
class InfrastructureServiceFactory:
    """Factory for creating infrastructure services"""
    
    def __init__(self):
        self._services = {}
        self._config = {}
    
    def configure(self, config: Dict[str, Any]):
        """Configure service factory with settings"""
        self._config = config
    
    def register_service(self, name: str, service_class: type):
        """Register a service class"""
        self._services[name] = service_class
    
    def create_data_provider(self, provider_type: str = "alpaca") -> DataProviderService:
        """Create data provider service"""
        if provider_type == "alpaca":
            api_key = self._config.get("alpaca_api_key")
            secret_key = self._config.get("alpaca_secret_key")
            base_url = self._config.get("alpaca_base_url", "https://paper-api.alpaca.markets")
            
            if not api_key or not secret_key:
                raise ValueError("Alpaca API credentials not configured")
            
            return AlpacaDataProvider(api_key, secret_key, base_url)
        else:
            raise ValueError(f"Unknown data provider type: {provider_type}")
    
    def create_trading_api(self, api_type: str = "alpaca") -> TradingAPIService:
        """Create trading API service"""
        if api_type == "alpaca":
            api_key = self._config.get("alpaca_api_key")
            secret_key = self._config.get("alpaca_secret_key")
            base_url = self._config.get("alpaca_base_url", "https://paper-api.alpaca.markets")
            
            if not api_key or not secret_key:
                raise ValueError("Alpaca API credentials not configured")
            
            return AlpacaTradingAPI(api_key, secret_key, base_url)
        else:
            raise ValueError(f"Unknown trading API type: {api_type}")
    
    def create_notification_service(self, service_type: str = "telegram") -> NotificationService:
        """Create notification service"""
        if service_type == "telegram":
            bot_token = self._config.get("telegram_bot_token")
            chat_id = self._config.get("telegram_chat_id")
            
            if not bot_token or not chat_id:
                raise ValueError("Telegram credentials not configured")
            
            return TelegramNotificationService(bot_token, chat_id)
        else:
            raise ValueError(f"Unknown notification service type: {service_type}")
    
    def create_database_service(self, db_type: str = "sqlite") -> DatabaseService:
        """Create database service"""
        if db_type == "sqlite":
            db_path = self._config.get("sqlite_db_path", "trading_bot.db")
            return SQLiteDatabaseService(db_path)
        else:
            raise ValueError(f"Unknown database type: {db_type}")
    
    def get_available_services(self) -> List[str]:
        """Get list of available service types"""
        return list(self._services.keys())
