# src/__init__.py
# Clean Architecture Implementation for Micro Trading Bot
# 
# Layers:
# - domain/     : Business logic & entities
# - application/: Use cases & application services  
# - infrastructure/: External interfaces (APIs, DB, etc.)
# - presentation/: UI, CLI, API endpoints

__version__ = "2.0.0"
__author__ = "Micro Trading Bot Team"

# Public API
__all__ = [
    "TradingBot",
    "StrategyService", 
    "RiskManagementService",
    "DataService",
    "NotificationService"
]
