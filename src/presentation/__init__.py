# src/presentation/__init__.py
# Presentation Layer - User Interfaces & API Endpoints
# 
# This layer contains:
# - Dashboard Services (Streamlit, Web UI)
# - CLI Services (Command Line Interface)
# - API Services (REST API, GraphQL)
# - User Interface Components

from .services import (
    DashboardService, CLIService, APIService,
    StreamlitDashboardService, ConsoleCLIService, RESTAPIService,
    TradingBotDashboard, TradingBotCLI
)

__all__ = [
    # Abstract Services
    "DashboardService",
    "CLIService", 
    "APIService",
    
    # Concrete Implementations
    "StreamlitDashboardService",
    "ConsoleCLIService",
    "RESTAPIService",
    
    # Main Applications
    "TradingBotDashboard",
    "TradingBotCLI"
]
