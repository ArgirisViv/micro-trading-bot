"""
Database Manager for Trading Bot
SQLite and PostgreSQL integration for better data management
"""

import sqlite3
import pandas as pd
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict
import os
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    psycopg2 = None
    RealDictCursor = None

class DatabaseManager:
    """
    Database manager for trading bot with SQLite and PostgreSQL support
    """
    
    def __init__(self, db_type: str = 'sqlite', config: Dict[str, Any] | None = None):
        self.db_type = db_type.lower()
        self.config = config or self._default_config()
        self.connection: Any
        self.cursor: Any
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize database
        self.initialize_database()
        
    def _default_config(self) -> Dict[str, Any]:
        """Default database configuration"""
        return {
            'sqlite': {
                'database': 'trading_bot.db',
                'timeout': 30
            },
            'postgresql': {
                'host': 'localhost',
                'port': 5432,
                'database': 'trading_bot',
                'user': 'postgres',
                'password': '',
                'sslmode': 'prefer'
            }
        }
    
    def initialize_database(self):
        """Initialize database connection and create tables"""
        try:
            if self.db_type == 'sqlite':
                self._init_sqlite()
            elif self.db_type == 'postgresql':
                if POSTGRES_AVAILABLE:
                    self._init_postgresql()
                else:
                    self.logger.warning("PostgreSQL not available, falling back to SQLite")
                    self.db_type = 'sqlite'
                    self._init_sqlite()
            else:
                raise ValueError(f"Unsupported database type: {self.db_type}")
            
            # Create tables
            self._create_tables()
            self.logger.info(f"Database initialized successfully: {self.db_type}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _init_sqlite(self):
        """Initialize SQLite database"""
        db_path = self.config['sqlite']['database']
        
        # Create database directory if it doesn't exist
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        self.connection = sqlite3.connect(
            db_path,
            timeout=self.config['sqlite']['timeout']
        )
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
        
        # Enable foreign keys
        self.cursor.execute("PRAGMA foreign_keys = ON")
        self.connection.commit()
    
    def _init_postgresql(self):
        """Initialize PostgreSQL database"""
        if not POSTGRES_AVAILABLE or psycopg2 is None or RealDictCursor is None:
            raise ImportError("psycopg2 not available for PostgreSQL")
        
        pg_config = self.config['postgresql']
        
        self.connection = psycopg2.connect(
            host=pg_config['host'],
            port=pg_config['port'],
            database=pg_config['database'],
            user=pg_config['user'],
            password=pg_config['password'],
            sslmode=pg_config['sslmode']
        )
        self.cursor = self.connection.cursor(cursor_factory=RealDictCursor)
    
    def _create_tables(self):
        """Create database tables"""
        if self.db_type == 'sqlite':
            self._create_sqlite_tables()
        else:
            self._create_postgresql_tables()
    
    def _create_sqlite_tables(self):
        """Create SQLite tables"""
        tables = {
            'trades': '''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    order_id TEXT,
                    status TEXT DEFAULT 'executed',
                    fees REAL DEFAULT 0.0,
                    strategy TEXT,
                    notes TEXT
                )
            ''',
            'positions': '''
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT UNIQUE NOT NULL,
                    quantity REAL NOT NULL,
                    avg_price REAL NOT NULL,
                    current_price REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            'market_data': '''
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL,
                    UNIQUE(symbol, timestamp)
                )
            ''',
            'risk_metrics': '''
                CREATE TABLE IF NOT EXISTS risk_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    portfolio_value REAL NOT NULL,
                    total_risk REAL,
                    sharpe_ratio REAL,
                    max_drawdown REAL,
                    var_95 REAL,
                    correlation_score REAL
                )
            ''',
            'ml_predictions': '''
                CREATE TABLE IF NOT EXISTS ml_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    prediction INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    features TEXT,
                    model_version TEXT
                )
            ''',
            'performance_metrics': '''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    total_return REAL,
                    daily_pnl REAL,
                    win_rate REAL,
                    avg_win REAL,
                    avg_loss REAL,
                    max_drawdown REAL,
                    sharpe_ratio REAL,
                    UNIQUE(date)
                )
            '''
        }
        
        for table_name, create_sql in tables.items():
            try:
                self.cursor.execute(create_sql)
                self.logger.info(f"Created table: {table_name}")
            except Exception as e:
                self.logger.error(f"Error creating table {table_name}: {e}")
        
        self.connection.commit()
    
    def _create_postgresql_tables(self):
        """Create PostgreSQL tables"""
        tables = {
            'trades': '''
                CREATE TABLE IF NOT EXISTS trades (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(20) NOT NULL,
                    side VARCHAR(10) NOT NULL,
                    quantity DECIMAL(15,6) NOT NULL,
                    price DECIMAL(15,6) NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    order_id VARCHAR(100),
                    status VARCHAR(20) DEFAULT 'executed',
                    fees DECIMAL(15,6) DEFAULT 0.0,
                    strategy VARCHAR(100),
                    notes TEXT
                )
            ''',
            'positions': '''
                CREATE TABLE IF NOT EXISTS positions (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(20) UNIQUE NOT NULL,
                    quantity DECIMAL(15,6) NOT NULL,
                    avg_price DECIMAL(15,6) NOT NULL,
                    current_price DECIMAL(15,6),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            'market_data': '''
                CREATE TABLE IF NOT EXISTS market_data (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(20) NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    open DECIMAL(15,6),
                    high DECIMAL(15,6),
                    low DECIMAL(15,6),
                    close DECIMAL(15,6),
                    volume DECIMAL(20,2),
                    UNIQUE(symbol, timestamp)
                )
            ''',
            'risk_metrics': '''
                CREATE TABLE IF NOT EXISTS risk_metrics (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    portfolio_value DECIMAL(20,2) NOT NULL,
                    total_risk DECIMAL(10,6),
                    sharpe_ratio DECIMAL(10,6),
                    max_drawdown DECIMAL(10,6),
                    var_95 DECIMAL(10,6),
                    correlation_score DECIMAL(10,6)
                )
            ''',
            'ml_predictions': '''
                CREATE TABLE IF NOT EXISTS ml_predictions (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(20) NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    prediction INTEGER NOT NULL,
                    confidence DECIMAL(5,4) NOT NULL,
                    features JSONB,
                    model_version VARCHAR(50)
                )
            ''',
            'performance_metrics': '''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    total_return DECIMAL(10,6),
                    daily_pnl DECIMAL(20,2),
                    win_rate DECIMAL(5,4),
                    avg_win DECIMAL(10,6),
                    avg_loss DECIMAL(10,6),
                    max_drawdown DECIMAL(10,6),
                    sharpe_ratio DECIMAL(10,6),
                    UNIQUE(date)
                )
            '''
        }
        
        for table_name, create_sql in tables.items():
            try:
                self.cursor.execute(create_sql)
                self.logger.info(f"Created table: {table_name}")
            except Exception as e:
                self.logger.error(f"Error creating table {table_name}: {e}")
        
        self.connection.commit()
    
    def insert_trade(self, trade_data: Dict[str, Any]) -> int:
        """Insert trade record"""
        try:
            sql = '''
                INSERT INTO trades (symbol, side, quantity, price, order_id, status, fees, strategy, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            '''
            
            if self.db_type == 'sqlite':
                sql = sql.replace('%s', '?')
                values = (
                    trade_data['symbol'],
                    trade_data['side'],
                    trade_data['quantity'],
                    trade_data['price'],
                    trade_data.get('order_id'),
                    trade_data.get('status', 'executed'),
                    trade_data.get('fees', 0.0),
                    trade_data.get('strategy'),
                    trade_data.get('notes')
                )
            else:
                values = (
                    trade_data['symbol'],
                    trade_data['side'],
                    trade_data['quantity'],
                    trade_data['price'],
                    trade_data.get('order_id'),
                    trade_data.get('status', 'executed'),
                    trade_data.get('fees', 0.0),
                    trade_data.get('strategy'),
                    trade_data.get('notes')
                )
            
            self.cursor.execute(sql, values)
            self.connection.commit()
            
            if self.db_type == 'sqlite':
                trade_id = self.cursor.lastrowid
            else:
                inserted_row = self.cursor.fetchone()
                trade_id = inserted_row[0] if inserted_row is not None else None
            if trade_id is None:
                raise RuntimeError("Database did not return an inserted trade ID")
            self.logger.info(f"Inserted trade: {trade_id}")
            return trade_id
            
        except Exception as e:
            self.logger.error(f"Error inserting trade: {e}")
            self.connection.rollback()
            raise
    
    def update_position(self, position_data: Dict[str, Any]):
        """Update or insert position"""
        try:
            if self.db_type == 'sqlite':
                sql = '''
                    INSERT OR REPLACE INTO positions (symbol, quantity, avg_price, current_price, last_updated)
                    VALUES (?, ?, ?, ?, ?)
                '''
                values = (
                    position_data['symbol'],
                    position_data['quantity'],
                    position_data['avg_price'],
                    position_data.get('current_price'),
                    datetime.now()
                )
            else:
                sql = '''
                    INSERT INTO positions (symbol, quantity, avg_price, current_price, last_updated)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (symbol) DO UPDATE SET
                        quantity = EXCLUDED.quantity,
                        avg_price = EXCLUDED.avg_price,
                        current_price = EXCLUDED.current_price,
                        last_updated = EXCLUDED.last_updated
                '''
                values = (
                    position_data['symbol'],
                    position_data['quantity'],
                    position_data['avg_price'],
                    position_data.get('current_price'),
                    datetime.now()
                )
            
            self.cursor.execute(sql, values)
            self.connection.commit()
            self.logger.info(f"Updated position: {position_data['symbol']}")
            
        except Exception as e:
            self.logger.error(f"Error updating position: {e}")
            self.connection.rollback()
            raise
    
    def insert_market_data(self, market_data: pd.DataFrame):
        """Insert market data"""
        try:
            if self.db_type == 'sqlite':
                sql = '''
                    INSERT OR REPLACE INTO market_data (symbol, timestamp, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                '''
            else:
                sql = '''
                    INSERT INTO market_data (symbol, timestamp, open, high, low, close, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (symbol, timestamp) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume
                '''
            
            for _, row in market_data.iterrows():
                values = (
                    row.name if hasattr(row, 'name') else 'UNKNOWN',
                    row.get('timestamp', datetime.now()),
                    row.get('open'),
                    row.get('high'),
                    row.get('low'),
                    row.get('close'),
                    row.get('volume')
                )
                
                self.cursor.execute(sql, values)
            
            self.connection.commit()
            self.logger.info(f"Inserted {len(market_data)} market data records")
            
        except Exception as e:
            self.logger.error(f"Error inserting market data: {e}")
            self.connection.rollback()
            raise
    
    def insert_risk_metrics(self, risk_data: Dict[str, Any]):
        """Insert risk metrics"""
        try:
            sql = '''
                INSERT INTO risk_metrics (portfolio_value, total_risk, sharpe_ratio, max_drawdown, var_95, correlation_score)
                VALUES (%s, %s, %s, %s, %s, %s)
            '''
            
            if self.db_type == 'sqlite':
                sql = sql.replace('%s', '?')
            
            values = (
                risk_data['portfolio_value'],
                risk_data.get('total_risk'),
                risk_data.get('sharpe_ratio'),
                risk_data.get('max_drawdown'),
                risk_data.get('var_95'),
                risk_data.get('correlation_score')
            )
            
            self.cursor.execute(sql, values)
            self.connection.commit()
            self.logger.info("Inserted risk metrics")
            
        except Exception as e:
            self.logger.error(f"Error inserting risk metrics: {e}")
            self.connection.rollback()
            raise
    
    def insert_ml_prediction(self, prediction_data: Dict[str, Any]):
        """Insert ML prediction"""
        try:
            sql = '''
                INSERT INTO ml_predictions (symbol, prediction, confidence, features, model_version)
                VALUES (%s, %s, %s, %s, %s)
            '''
            
            if self.db_type == 'sqlite':
                sql = sql.replace('%s', '?')
                features = json.dumps(prediction_data.get('features', {}))
            else:
                features = json.dumps(prediction_data.get('features', {}))
            
            values = (
                prediction_data['symbol'],
                prediction_data['prediction'],
                prediction_data['confidence'],
                features,
                prediction_data.get('model_version', '1.0.0')
            )
            
            self.cursor.execute(sql, values)
            self.connection.commit()
            self.logger.info(f"Inserted ML prediction for {prediction_data['symbol']}")
            
        except Exception as e:
            self.logger.error(f"Error inserting ML prediction: {e}")
            self.connection.rollback()
            raise
    
    def insert_performance_metrics(self, performance_data: Dict[str, Any]):
        """Insert performance metrics"""
        try:
            sql = '''
                INSERT INTO performance_metrics (date, total_return, daily_pnl, win_rate, avg_win, avg_loss, max_drawdown, sharpe_ratio)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (date) DO UPDATE SET
                    total_return = EXCLUDED.total_return,
                    daily_pnl = EXCLUDED.daily_pnl,
                    win_rate = EXCLUDED.win_rate,
                    avg_win = EXCLUDED.avg_win,
                    avg_loss = EXCLUDED.avg_loss,
                    max_drawdown = EXCLUDED.max_drawdown,
                    sharpe_ratio = EXCLUDED.sharpe_ratio
            '''
            
            if self.db_type == 'sqlite':
                sql = sql.replace('%s', '?').replace('ON CONFLICT (date) DO UPDATE SET', '')
                sql = sql.replace('total_return = EXCLUDED.total_return,', '')
                sql = sql.replace('daily_pnl = EXCLUDED.daily_pnl,', '')
                sql = sql.replace('win_rate = EXCLUDED.win_rate,', '')
                sql = sql.replace('avg_win = EXCLUDED.avg_win,', '')
                sql = sql.replace('avg_loss = EXCLUDED.avg_loss,', '')
                sql = sql.replace('max_drawdown = EXCLUDED.max_drawdown,', '')
                sql = sql.replace('sharpe_ratio = EXCLUDED.sharpe_ratio', '')
            
            values = (
                performance_data['date'],
                performance_data.get('total_return'),
                performance_data.get('daily_pnl'),
                performance_data.get('win_rate'),
                performance_data.get('avg_win'),
                performance_data.get('avg_loss'),
                performance_data.get('max_drawdown'),
                performance_data.get('sharpe_ratio')
            )
            
            self.cursor.execute(sql, values)
            self.connection.commit()
            self.logger.info(f"Inserted performance metrics for {performance_data['date']}")
            
        except Exception as e:
            self.logger.error(f"Error inserting performance metrics: {e}")
            self.connection.rollback()
            raise
    
    def get_trades(self, symbol: str | None = None, start_date: datetime | None = None, end_date: datetime | None = None) -> pd.DataFrame:
        """Get trades from database"""
        try:
            sql = "SELECT * FROM trades WHERE 1=1"
            values: list[Any] = []
            
            if symbol:
                sql += " AND symbol = %s" if self.db_type != 'sqlite' else " AND symbol = ?"
                values.append(symbol)
            
            if start_date:
                sql += " AND timestamp >= %s" if self.db_type != 'sqlite' else " AND timestamp >= ?"
                values.append(start_date)
            
            if end_date:
                sql += " AND timestamp <= %s" if self.db_type != 'sqlite' else " AND timestamp <= ?"
                values.append(end_date)
            
            sql += " ORDER BY timestamp DESC"
            
            self.cursor.execute(sql, values)
            rows = self.cursor.fetchall()
            
            if self.db_type == 'sqlite':
                columns = [description[0] for description in self.cursor.description]
                df = pd.DataFrame(rows, columns=columns)
            else:
                df = pd.DataFrame(rows)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error getting trades: {e}")
            return pd.DataFrame()
    
    def get_positions(self) -> pd.DataFrame:
        """Get current positions"""
        try:
            sql = "SELECT * FROM positions ORDER BY symbol"
            self.cursor.execute(sql)
            rows = self.cursor.fetchall()
            
            if self.db_type == 'sqlite':
                columns = [description[0] for description in self.cursor.description]
                df = pd.DataFrame(rows, columns=columns)
            else:
                df = pd.DataFrame(rows)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return pd.DataFrame()
    
    def get_market_data(self, symbol: str, start_date: datetime | None = None, end_date: datetime | None = None) -> pd.DataFrame:
        """Get market data from database"""
        try:
            sql = "SELECT * FROM market_data WHERE symbol = %s" if self.db_type != 'sqlite' else "SELECT * FROM market_data WHERE symbol = ?"
            values: list[Any] = [symbol]
            
            if start_date:
                sql += " AND timestamp >= %s" if self.db_type != 'sqlite' else " AND timestamp >= ?"
                values.append(start_date)
            
            if end_date:
                sql += " AND timestamp <= %s" if self.db_type != 'sqlite' else " AND timestamp <= ?"
                values.append(end_date)
            
            sql += " ORDER BY timestamp"
            
            self.cursor.execute(sql, values)
            rows = self.cursor.fetchall()
            
            if self.db_type == 'sqlite':
                columns = [description[0] for description in self.cursor.description]
                df = pd.DataFrame(rows, columns=columns)
            else:
                df = pd.DataFrame(rows)
            
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error getting market data: {e}")
            return pd.DataFrame()
    
    def get_risk_metrics(self, days: int = 30) -> pd.DataFrame:
        """Get risk metrics from database"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            sql = "SELECT * FROM risk_metrics WHERE timestamp >= %s ORDER BY timestamp DESC" if self.db_type != 'sqlite' else "SELECT * FROM risk_metrics WHERE timestamp >= ? ORDER BY timestamp DESC"
            values = [start_date]
            
            self.cursor.execute(sql, values)
            rows = self.cursor.fetchall()
            
            if self.db_type == 'sqlite':
                columns = [description[0] for description in self.cursor.description]
                df = pd.DataFrame(rows, columns=columns)
            else:
                df = pd.DataFrame(rows)
            
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error getting risk metrics: {e}")
            return pd.DataFrame()
    
    def get_performance_metrics(self, start_date: datetime | None = None, end_date: datetime | None = None) -> pd.DataFrame:
        """Get performance metrics from database"""
        try:
            sql = "SELECT * FROM performance_metrics WHERE 1=1"
            values = []
            
            if start_date:
                sql += " AND date >= %s" if self.db_type != 'sqlite' else " AND date >= ?"
                values.append(start_date.date())
            
            if end_date:
                sql += " AND date <= %s" if self.db_type != 'sqlite' else " AND date <= ?"
                values.append(end_date.date())
            
            sql += " ORDER BY date DESC"
            
            self.cursor.execute(sql, values)
            rows = self.cursor.fetchall()
            
            if self.db_type == 'sqlite':
                columns = [description[0] for description in self.cursor.description]
                df = pd.DataFrame(rows, columns=columns)
            else:
                df = pd.DataFrame(rows)
            
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error getting performance metrics: {e}")
            return pd.DataFrame()
    
    def execute_query(self, sql: str, values: tuple[Any, ...] | None = None) -> pd.DataFrame:
        """Execute custom SQL query"""
        try:
            if values:
                self.cursor.execute(sql, values)
            else:
                self.cursor.execute(sql)
            
            rows = self.cursor.fetchall()
            
            if self.db_type == 'sqlite':
                columns = [description[0] for description in self.cursor.description]
                df = pd.DataFrame(rows, columns=columns)
            else:
                df = pd.DataFrame(rows)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error executing query: {e}")
            return pd.DataFrame()
    
    def backup_database(self, backup_path: str):
        """Backup database"""
        try:
            if self.db_type == 'sqlite':
                import shutil
                shutil.copy2(self.config['sqlite']['database'], backup_path)
                self.logger.info(f"SQLite database backed up to {backup_path}")
            else:
                # For PostgreSQL, you might want to use pg_dump
                self.logger.warning("PostgreSQL backup not implemented. Use pg_dump instead.")
                
        except Exception as e:
            self.logger.error(f"Error backing up database: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
            self.logger.info("Database connection closed")
        except Exception as e:
            self.logger.error(f"Error closing database: {e}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

class DatabaseMigrator:
    """Database migration utility"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
    
    def migrate_from_files(self, data_dir: str = '.'):
        """Migrate data from CSV/JSON files to database"""
        try:
            # Migrate trade log
            trade_log_path = os.path.join(data_dir, 'trade_log.csv')
            if os.path.exists(trade_log_path):
                self._migrate_trade_log(trade_log_path)
            
            # Migrate market data
            market_data_path = os.path.join(data_dir, 'data/historical.csv')
            if os.path.exists(market_data_path):
                self._migrate_market_data(market_data_path)
            
            # Migrate state
            state_path = os.path.join(data_dir, 'state.json')
            if os.path.exists(state_path):
                self._migrate_state(state_path)
            
            self.logger.info("Data migration completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during data migration: {e}")
            raise
    
    def _migrate_trade_log(self, file_path: str):
        """Migrate trade log to database"""
        try:
            df = pd.read_csv(file_path)
            if not df.empty:
                for _, row in df.iterrows():
                    trade_data = {
                        'symbol': row.get('symbol', 'UNKNOWN'),
                        'side': row.get('side', 'buy'),
                        'quantity': row.get('quantity', 0),
                        'price': row.get('price', 0),
                        'order_id': row.get('order_id'),
                        'strategy': row.get('strategy'),
                        'notes': row.get('notes')
                    }
                    self.db_manager.insert_trade(trade_data)
                
                self.logger.info(f"Migrated {len(df)} trades from {file_path}")
            
        except Exception as e:
            self.logger.error(f"Error migrating trade log: {e}")
    
    def _migrate_market_data(self, file_path: str):
        """Migrate market data to database"""
        try:
            df = pd.read_csv(file_path)
            if not df.empty:
                self.db_manager.insert_market_data(df)
                self.logger.info(f"Migrated market data from {file_path}")
            
        except Exception as e:
            self.logger.error(f"Error migrating market data: {e}")
    
    def _migrate_state(self, file_path: str):
        """Migrate state to database"""
        try:
            with open(file_path, 'r') as f:
                state = json.load(f)
            
            # Migrate positions
            if 'positions' in state:
                for symbol, pos in state['positions'].items():
                    position_data = {
                        'symbol': symbol,
                        'quantity': pos.get('quantity', 0),
                        'avg_price': pos.get('avg_price', 0),
                        'current_price': pos.get('current_price', 0)
                    }
                    self.db_manager.update_position(position_data)
            
            self.logger.info(f"Migrated state from {file_path}")
            
        except Exception as e:
            self.logger.error(f"Error migrating state: {e}")

# Utility functions
def create_database_manager(db_type: str = 'sqlite', config: Dict[str, Any] | None = None) -> DatabaseManager:
    """Factory function to create database manager"""
    return DatabaseManager(db_type, config)

def migrate_data_to_database(db_type: str = 'sqlite', config: Dict[str, Any] | None = None, data_dir: str = '.'):
    """Utility function to migrate data to database"""
    with create_database_manager(db_type, config) as db_manager:
        migrator = DatabaseMigrator(db_manager)
        migrator.migrate_from_files(data_dir)
