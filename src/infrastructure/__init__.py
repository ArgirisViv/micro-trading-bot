# src/infrastructure/__init__.py
# Infrastructure Layer - External Interfaces & Data Access
# 
# This layer contains:
# - Data Providers (Alpaca, Yahoo Finance)
# - Trading APIs (Alpaca Trading API)
# - Notification Services (Telegram, Email, Slack)
# - Database Services (SQLite, PostgreSQL)
# - External Service Implementations

from .services import (
    DataProviderService, TradingAPIService, NotificationService, DatabaseService,
    AlpacaDataProvider, AlpacaTradingAPI, TelegramNotificationService, 
    SQLiteDatabaseService, InfrastructureServiceFactory
)

__all__ = [
    # Abstract Services
    "DataProviderService",
    "TradingAPIService", 
    "NotificationService",
    "DatabaseService",
    
    # Concrete Implementations
    "AlpacaDataProvider",
    "AlpacaTradingAPI",
    "TelegramNotificationService",
    "SQLiteDatabaseService",
    
    # Factories
    "InfrastructureServiceFactory"
]
