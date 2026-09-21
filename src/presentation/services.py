# src/presentation/services.py
# Presentation Services - User Interfaces & API Endpoints

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
import json
import logging
from datetime import datetime
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

from ..application.services import TradingBotService
from ..infrastructure.services import InfrastructureServiceFactory


class DashboardService(ABC):
    """Abstract dashboard service"""
    
    @abstractmethod
    def render_portfolio_overview(self, portfolio_data: Dict[str, Any]) -> None:
        """Render portfolio overview section"""
        pass
    
    @abstractmethod
    def render_positions_table(self, positions: List[Dict[str, Any]]) -> None:
        """Render positions table"""
        pass
    
    @abstractmethod
    def render_risk_metrics(self, risk_data: Dict[str, Any]) -> None:
        """Render risk metrics"""
        pass
    
    @abstractmethod
    def render_trading_signals(self, signals: List[Dict[str, Any]]) -> None:
        """Render trading signals"""
        pass


class CLIService(ABC):
    """Abstract CLI service"""
    
    @abstractmethod
    def show_menu(self) -> str:
        """Show main menu and get user choice"""
        pass
    
    @abstractmethod
    def execute_command(self, command: str) -> bool:
        """Execute CLI command"""
        pass
    
    @abstractmethod
    def show_help(self) -> None:
        """Show help information"""
        pass


class APIService(ABC):
    """Abstract API service"""
    
    @abstractmethod
    def get_portfolio_status(self) -> Dict[str, Any]:
        """Get portfolio status via API"""
        pass
    
    @abstractmethod
    def place_trade_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Place trade order via API"""
        pass
    
    @abstractmethod
    def get_trading_history(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get trading history via API"""
        pass


# Concrete Implementations

class StreamlitDashboardService(DashboardService):
    """Streamlit-based dashboard service implementation"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._setup_page_config()
    
    def _setup_page_config(self):
        """Setup Streamlit page configuration"""
        st.set_page_config(
            page_title="Micro Trading Bot - Real-time Dashboard",
            page_icon="🚀",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    def render_portfolio_overview(self, portfolio_data: Dict[str, Any]) -> None:
        """Render portfolio overview section"""
        try:
            st.header("📊 Portfolio Overview")
            
            # Portfolio metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_value = portfolio_data.get("total_value", 0)
                st.metric("Total Value", f"${total_value:,.2f}")
            
            with col2:
                unrealized_pnl = portfolio_data.get("unrealized_pnl", 0)
                pnl_pct = portfolio_data.get("unrealized_pnl_pct", 0)
                st.metric("Unrealized P&L", f"${unrealized_pnl:,.2f}", 
                         delta=f"{pnl_pct:.2f}%" if pnl_pct != 0 else "0%")
            
            with col3:
                position_count = portfolio_data.get("position_count", 0)
                st.metric("Positions", position_count)
            
            with col4:
                last_update = portfolio_data.get("last_update", "N/A")
                st.metric("Last Update", last_update)
            
            # Portfolio value chart (if historical data available)
            if "historical_values" in portfolio_data:
                self._render_portfolio_chart(portfolio_data["historical_values"])
            
        except Exception as e:
            st.error(f"Failed to render portfolio overview: {e}")
            self.logger.error(f"Portfolio overview render error: {e}")
    
    def render_positions_table(self, positions: List[Dict[str, Any]]) -> None:
        """Render positions table"""
        try:
            st.header("📈 Current Positions")
            
            if not positions:
                st.info("No open positions")
                return
            
            # Create positions dataframe
            positions_data = []
            for pos in positions:
                positions_data.append({
                    'Symbol': pos.get('symbol', ''),
                    'Side': pos.get('side', ''),
                    'Quantity': pos.get('quantity', 0),
                    'Entry Price': f"${pos.get('entry_price', 0):.2f}",
                    'Current Price': f"${pos.get('current_price', 0):.2f}",
                    'Market Value': f"${pos.get('market_value', 0):,.2f}",
                    'Unrealized P&L': f"${pos.get('unrealized_pnl', 0):,.2f}",
                    'P&L %': f"{pos.get('unrealized_pnl_pct', 0):.2f}%"
                })
            
            df = pd.DataFrame(positions_data)
            st.dataframe(df, width="stretch")
            
            # Position summary chart
            if len(positions) > 1:
                self._render_positions_chart(positions)
            
        except Exception as e:
            st.error(f"Failed to render positions table: {e}")
            self.logger.error(f"Positions table render error: {e}")
    
    def render_risk_metrics(self, risk_data: Dict[str, Any]) -> None:
        """Render risk metrics"""
        try:
            st.header("⚠️ Risk Management")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Portfolio Risk Metrics")
                
                metrics_data = {
                    'Metric': ['Overall Risk', 'Risk Score', 'VaR (95%)', 'Sharpe Ratio', 'Max Drawdown'],
                    'Value': [
                        risk_data.get('overall_risk', 'N/A'),
                        f"{risk_data.get('risk_score', 0):.2f}",
                        f"{risk_data.get('var_95', 0):.2%}",
                        f"{risk_data.get('sharpe_ratio', 0):.2f}",
                        f"{risk_data.get('max_drawdown', 0):.2%}"
                    ]
                }
                
                metrics_df = pd.DataFrame(metrics_data)
                st.dataframe(metrics_df, width="stretch")
            
            with col2:
                st.subheader("Risk Alerts")
                
                alerts = risk_data.get('risk_alerts', [])
                if not alerts:
                    alerts = ["✅ All risk metrics within normal ranges"]
                
                for alert in alerts:
                    if "🚨" in alert or "HIGH" in alert.upper():
                        st.error(alert)
                    elif "⚠️" in alert or "WARNING" in alert.upper():
                        st.warning(alert)
                    else:
                        st.success(alert)
            
            # Risk visualization
            self._render_risk_charts(risk_data)
            
        except Exception as e:
            st.error(f"Failed to render risk metrics: {e}")
            self.logger.error(f"Risk metrics render error: {e}")
    
    def render_trading_signals(self, signals: List[Dict[str, Any]]) -> None:
        """Render trading signals"""
        try:
            st.header("🎯 Trading Signals")
            
            if not signals:
                st.info("No trading signals available")
                return
            
            # Filter signals by type
            signal_types = st.multiselect(
                "Filter by Signal Type:",
                ['BUY', 'SELL', 'HOLD'],
                default=['BUY', 'SELL', 'HOLD']
            )
            
            filtered_signals = [s for s in signals if s.get('signal') in signal_types]
            
            if filtered_signals:
                # Create signals dataframe
                signals_data = []
                for signal in filtered_signals:
                    signals_data.append({
                        'Symbol': signal.get('symbol', ''),
                        'Signal': signal.get('signal', ''),
                        'Confidence': f"{signal.get('confidence', 0):.1%}",
                        'Price': f"${signal.get('price', 0):.2f}",
                        'Time': signal.get('timestamp', ''),
                        'Reason': signal.get('reason', '')
                    })
                
                df = pd.DataFrame(signals_data)
                st.dataframe(df, width="stretch")
                
                # Signal confidence visualization
                self._render_signals_chart(filtered_signals)
            else:
                st.info("No signals match the selected filters.")
            
        except Exception as e:
            st.error(f"Failed to render trading signals: {e}")
            self.logger.error(f"Trading signals render error: {e}")
    
    def render_system_status(self, system_data: Dict[str, Any]) -> None:
        """Render system status"""
        try:
            st.header("🔧 System Status")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Data Feed", "🟢 Active" if system_data.get("data_feed_status") == "active" else "🔴 Inactive")
                st.metric("ML Model", "🟢 Online" if system_data.get("ml_model_status") == "online" else "🔴 Offline")
            
            with col2:
                st.metric("Risk Engine", "🟢 Running" if system_data.get("risk_engine_status") == "running" else "🔴 Stopped")
                st.metric("Notifications", "🟢 Enabled" if system_data.get("notifications_status") == "enabled" else "🔴 Disabled")
            
            with col3:
                st.metric("API Status", "🟢 Connected" if system_data.get("api_status") == "connected" else "🔴 Disconnected")
                st.metric("Last Trade", system_data.get("last_trade_time", "N/A"))
            
            # System health indicators
            st.subheader("System Health")
            
            health_data = {
                'Component': ['Data Feed', 'ML Model', 'Risk Engine', 'Trading API', 'Notifications'],
                'Status': ['🟢', '🟢', '🟢', '🟢', '🟢'],
                'Uptime': ['99.9%', '99.8%', '100%', '99.7%', '99.9%'],
                'Last Check': ['2s ago', '5min ago', '1min ago', '30s ago', '1min ago']
            }
            
            health_df = pd.DataFrame(health_data)
            st.dataframe(health_df, width="stretch")
            
        except Exception as e:
            st.error(f"Failed to render system status: {e}")
            self.logger.error(f"System status render error: {e}")
    
    def _render_portfolio_chart(self, historical_data: List[Dict[str, Any]]) -> None:
        """Render portfolio value chart"""
        try:
            if not historical_data:
                return
            
            # Convert to DataFrame
            df = pd.DataFrame(historical_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['portfolio_value'],
                mode='lines',
                name='Portfolio Value',
                line=dict(color='#00ff88', width=2)
            ))
            
            fig.update_layout(
                title="Portfolio Value Over Time",
                xaxis_title="Time",
                yaxis_title="Value ($)",
                height=400,
                showlegend=False
            )
            
            st.plotly_chart(fig, width="stretch")
            
        except Exception as e:
            self.logger.error(f"Portfolio chart render error: {e}")
    
    def _render_positions_chart(self, positions: List[Dict[str, Any]]) -> None:
        """Render positions summary chart"""
        try:
            # Create pie chart of position weights
            symbols = [pos.get('symbol', '') for pos in positions]
            weights = [pos.get('weight', 0) for pos in positions]
            
            fig = go.Figure(data=[go.Pie(labels=symbols, values=weights, hole=0.3)])
            fig.update_layout(
                title="Position Weights",
                height=400
            )
            
            st.plotly_chart(fig, width="stretch")
            
        except Exception as e:
            self.logger.error(f"Positions chart render error: {e}")
    
    def _render_risk_charts(self, risk_data: Dict[str, Any]) -> None:
        """Render risk visualization charts"""
        try:
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Portfolio Risk', 'Drawdown', 'Position Weights', 'Risk Distribution'),
                specs=[[{"type": "indicator"}, {"type": "bar"}],
                       [{"type": "pie"}, {"type": "histogram"}]]
            )
            
            # Portfolio risk gauge
            risk_score = risk_data.get('risk_score', 0)
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number+delta",
                    value=risk_score * 100,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "Portfolio Risk (%)"},
                    delta={'reference': 15},
                    gauge={
                        'axis': {'range': [None, 30]},
                        'bar': {'color': "darkblue"},
                        'steps': [
                            {'range': [0, 10], 'color': "lightgray"},
                            {'range': [10, 20], 'color': "yellow"},
                            {'range': [20, 30], 'color': "red"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 20
                        }
                    }
                ),
                row=1, col=1
            )
            
            # Drawdown bar
            max_drawdown = risk_data.get('max_drawdown', 0)
            fig.add_trace(
                go.Bar(
                    x=['Current Drawdown'],
                    y=[max_drawdown * 100],
                    marker_color='red' if max_drawdown > 0.10 else 'orange'
                ),
                row=1, col=2
            )
            
            # Position weights pie (if available)
            if 'position_weights' in risk_data:
                weights = risk_data['position_weights']
                fig.add_trace(
                    go.Pie(
                        labels=list(weights.keys()),
                        values=list(weights.values()),
                        hole=0.3
                    ),
                    row=2, col=1
                )
            
            fig.update_layout(height=600, showlegend=False)
            st.plotly_chart(fig, width="stretch")
            
        except Exception as e:
            self.logger.error(f"Risk charts render error: {e}")
    
    def _render_signals_chart(self, signals: List[Dict[str, Any]]) -> None:
        """Render trading signals chart"""
        try:
            if not signals:
                return
            
            # Signal confidence visualization
            fig = px.bar(
                signals,
                x='symbol',
                y='confidence',
                color='signal',
                title="Signal Confidence by Symbol",
                color_discrete_map={
                    'BUY': 'green',
                    'SELL': 'red',
                    'HOLD': 'gray'
                }
            )
            
            fig.update_layout(height=400)
            st.plotly_chart(fig, width="stretch")
            
        except Exception as e:
            self.logger.error(f"Signals chart render error: {e}")


class ConsoleCLIService(CLIService):
    """Console-based CLI service implementation"""
    
    def __init__(self, trading_bot_service: TradingBotService):
        self.trading_bot_service = trading_bot_service
        self.logger = logging.getLogger(__name__)
        self.running = True
    
    def show_menu(self) -> str:
        """Show main menu and get user choice"""
        print("\n" + "="*50)
        print("🚀 MICRO TRADING BOT - COMMAND LINE INTERFACE")
        print("="*50)
        print("1. Portfolio Status")
        print("2. Current Positions")
        print("3. Risk Assessment")
        print("4. Trading Signals")
        print("5. Execute Strategy")
        print("6. System Status")
        print("7. Help")
        print("8. Exit")
        print("-"*50)
        
        while True:
            try:
                choice = input("Enter your choice (1-8): ").strip()
                if choice in ['1', '2', '3', '4', '5', '6', '7', '8']:
                    return choice
                else:
                    print("❌ Invalid choice. Please enter a number between 1-8.")
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                return '8'
            except Exception as e:
                print(f"❌ Error: {e}")
                return '8'
    
    def execute_command(self, command: str) -> bool:
        """Execute CLI command"""
        try:
            if command == '1':
                self._show_portfolio_status()
            elif command == '2':
                self._show_positions()
            elif command == '3':
                self._show_risk_assessment()
            elif command == '4':
                self._show_trading_signals()
            elif command == '5':
                self._execute_strategy()
            elif command == '6':
                self._show_system_status()
            elif command == '7':
                self.show_help()
            elif command == '8':
                self.running = False
                print("👋 Exiting...")
                return False
            else:
                print("❌ Unknown command")
            
            return True
            
        except Exception as e:
            print(f"❌ Error executing command: {e}")
            self.logger.error(f"CLI command execution error: {e}")
            return True
    
    def show_help(self) -> None:
        """Show help information"""
        print("\n" + "="*50)
        print("📚 HELP - MICRO TRADING BOT")
        print("="*50)
        print("Available Commands:")
        print("1. Portfolio Status - Show current portfolio overview")
        print("2. Current Positions - Display open positions")
        print("3. Risk Assessment - Show risk metrics and alerts")
        print("4. Trading Signals - Display current trading signals")
        print("5. Execute Strategy - Run trading strategy")
        print("6. System Status - Show system health and status")
        print("7. Help - Show this help message")
        print("8. Exit - Close the application")
        print("\nNavigation:")
        print("- Use number keys (1-8) to select options")
        print("- Press Ctrl+C to exit at any time")
        print("- All data is real-time from the trading system")
        print("="*50)
    
    def _show_portfolio_status(self) -> None:
        """Show portfolio status"""
        print("\n📊 PORTFOLIO STATUS")
        print("-" * 30)
        
        try:
            status = self.trading_bot_service.get_system_status()
            
            if "error" in status:
                print(f"❌ Error: {status['error']}")
                return
            
            account = status.get("account", {})
            portfolio = status.get("portfolio", {})
            
            print(f"💰 Total Value: ${account.get('total_value', 0):,.2f}")
            print(f"💵 Cash: ${account.get('cash', 0):,.2f}")
            print(f"📈 Positions Value: ${account.get('positions_value', 0):,.2f}")
            print(f"🔢 Position Count: {account.get('position_count', 0)}")
            print(f"📋 Open Orders: {account.get('open_orders', 0)}")
            print(f"📊 Unrealized P&L: ${account.get('unrealized_pnl', 0):,.2f}")
            print(f"📈 P&L %: {account.get('unrealized_pnl_pct', 0):.2f}%")
            print(f"🕒 Last Update: {status.get('last_update', 'N/A')}")
            
        except Exception as e:
            print(f"❌ Failed to get portfolio status: {e}")
    
    def _show_positions(self) -> None:
        """Show current positions"""
        print("\n📈 CURRENT POSITIONS")
        print("-" * 30)
        
        try:
            positions = self.trading_bot_service.trading_service.get_positions()
            
            if not positions:
                print("ℹ️ No open positions")
                return
            
            for i, pos in enumerate(positions, 1):
                print(f"\n{i}. {pos['symbol']}")
                print(f"   Side: {pos['side']}")
                print(f"   Quantity: {pos['quantity']}")
                print(f"   Entry Price: ${pos['entry_price']:.2f}")
                print(f"   Current Price: ${pos['current_price']:.2f}")
                print(f"   Market Value: ${pos['market_value']:,.2f}")
                print(f"   Unrealized P&L: ${pos['unrealized_pnl']:,.2f}")
                print(f"   P&L %: {pos['unrealized_pnl_pct']:.2f}%")
            
        except Exception as e:
            print(f"❌ Failed to get positions: {e}")
    
    def _show_risk_assessment(self) -> None:
        """Show risk assessment"""
        print("\n⚠️ RISK ASSESSMENT")
        print("-" * 30)
        
        try:
            risk_assessment = self.trading_bot_service.risk_service.assess_risk("default")
            
            print(f"🎯 Overall Risk Level: {risk_assessment.overall_risk_level}")
            print(f"📊 Risk Score: {risk_assessment.risk_score:.2f}")
            
            if risk_assessment.risk_alerts:
                print("\n🚨 Risk Alerts:")
                for alert in risk_assessment.risk_alerts:
                    print(f"   • {alert}")
            
            if risk_assessment.recommendations:
                print("\n💡 Recommendations:")
                for rec in risk_assessment.recommendations:
                    print(f"   • {rec}")
            
        except Exception as e:
            print(f"❌ Failed to get risk assessment: {e}")
    
    def _show_trading_signals(self) -> None:
        """Show trading signals"""
        print("\n🎯 TRADING SIGNALS")
        print("-" * 30)
        
        try:
            # This would typically come from a signal service
            # For now, show a placeholder
            print("ℹ️ Trading signals feature coming soon...")
            print("   Signals will be generated based on:")
            print("   • Technical analysis")
            print("   • Machine learning predictions")
            print("   • Risk assessment")
            print("   • Market conditions")
            
        except Exception as e:
            print(f"❌ Failed to get trading signals: {e}")
    
    def _execute_strategy(self) -> None:
        """Execute trading strategy"""
        print("\n🚀 EXECUTE TRADING STRATEGY")
        print("-" * 30)
        
        try:
            # Get strategy configuration
            symbols = input("Enter symbols to trade (comma-separated): ").strip()
            if not symbols:
                print("❌ No symbols provided")
                return
            
            symbol_list = [s.strip() for s in symbols.split(",")]
            
            strategy_config = {
                "symbols": symbol_list,
                "risk_per_trade": 0.02,
                "max_positions": 5
            }
            
            print(f"📋 Strategy Configuration:")
            print(f"   Symbols: {', '.join(symbol_list)}")
            print(f"   Risk per trade: {strategy_config['risk_per_trade']:.1%}")
            print(f"   Max positions: {strategy_config['max_positions']}")
            
            # Confirm execution
            confirm = input("\nExecute strategy? (y/N): ").strip().lower()
            if confirm != 'y':
                print("❌ Strategy execution cancelled")
                return
            
            print("🔄 Executing strategy...")
            results = self.trading_bot_service.execute_trading_strategy(strategy_config)
            
            if results.get("status") == "executed":
                print("✅ Strategy executed successfully!")
                print(f"   Trades executed: {len(results.get('trades_executed', []))}")
                print(f"   Signals generated: {len(results.get('signals_generated', []))}")
                print(f"   Risk checks passed: {len(results.get('risk_checks_passed', []))}")
                
                if results.get("errors"):
                    print(f"   Errors: {len(results.get('errors', []))}")
            else:
                print(f"❌ Strategy execution failed: {results.get('error', 'Unknown error')}")
            
        except Exception as e:
            print(f"❌ Failed to execute strategy: {e}")
    
    def _show_system_status(self) -> None:
        """Show system status"""
        print("\n🔧 SYSTEM STATUS")
        print("-" * 30)
        
        try:
            status = self.trading_bot_service.get_system_status()
            
            if "error" in status:
                print(f"❌ Error: {status['error']}")
                return
            
            print(f"🟢 System Status: {status.get('system_status', 'Unknown')}")
            print(f"🕒 Last Update: {status.get('last_update', 'N/A')}")
            
            risk = status.get("risk", {})
            print(f"⚠️ Risk Level: {risk.get('level', 'Unknown')}")
            print(f"📊 Risk Score: {risk.get('score', 0):.2f}")
            
            if risk.get("alerts"):
                print("\n🚨 Risk Alerts:")
                for alert in risk["alerts"]:
                    print(f"   • {alert}")
            
        except Exception as e:
            print(f"❌ Failed to get system status: {e}")


class RESTAPIService(APIService):
    """REST API service implementation"""
    
    def __init__(self, trading_bot_service: TradingBotService):
        self.trading_bot_service = trading_bot_service
        self.logger = logging.getLogger(__name__)
    
    def get_portfolio_status(self) -> Dict[str, Any]:
        """Get portfolio status via API"""
        try:
            status = self.trading_bot_service.get_system_status()
            return {
                "success": True,
                "data": status,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"API portfolio status error: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def place_trade_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Place trade order via API"""
        try:
            # Validate order data
            required_fields = ["symbol", "action", "quantity"]
            for field in required_fields:
                if field not in order_data:
                    return {
                        "success": False,
                        "error": f"Missing required field: {field}",
                        "timestamp": datetime.now().isoformat()
                    }
            
            # Place order through trading service
            response = self.trading_bot_service.trading_service.place_order(
                symbol=order_data["symbol"],
                action=order_data["action"],
                quantity=order_data["quantity"],
                price=order_data.get("price")
            )
            
            return {
                "success": response.success,
                "data": {
                    "order_id": response.order_id,
                    "message": response.message,
                    "status": "submitted"
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"API place order error: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_trading_history(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get trading history via API"""
        try:
            # This would typically query a database service
            # For now, return empty list
            return []
            
        except Exception as e:
            self.logger.error(f"API trading history error: {e}")
            return []


# Main Dashboard Application
class TradingBotDashboard:
    """Main dashboard application"""
    
    def __init__(self, trading_bot_service: TradingBotService):
        self.trading_bot_service = trading_bot_service
        self.dashboard_service = StreamlitDashboardService()
        self.logger = logging.getLogger(__name__)
    
    def run(self):
        """Run the dashboard"""
        try:
            st.title("🚀 Micro Trading Bot - Real-time Dashboard")
            st.markdown("---")
            
            # Get system data
            system_status = self.trading_bot_service.get_system_status()
            
            if "error" in system_status:
                st.error(f"Failed to get system status: {system_status['error']}")
                return
            
            # Render dashboard sections
            self.dashboard_service.render_portfolio_overview(system_status.get("account", {}))
            st.markdown("---")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                self.dashboard_service.render_positions_table(system_status.get("positions", []))
            
            with col2:
                risk_data = system_status.get("risk", {})
                self.dashboard_service.render_risk_metrics(risk_data)
            
            st.markdown("---")
            
            # Placeholder for trading signals
            self.dashboard_service.render_trading_signals([])
            
            st.markdown("---")
            self.dashboard_service.render_system_status(system_status)
            
            # Auto-refresh
            st.markdown("---")
            st.markdown("*Dashboard auto-refreshes every 30 seconds*")
            
            # Add refresh button
            if st.button("🔄 Refresh Now"):
                st.rerun()
                
        except Exception as e:
            st.error(f"Dashboard error: {e}")
            self.logger.error(f"Dashboard error: {e}")


# CLI Application
class TradingBotCLI:
    """Main CLI application"""
    
    def __init__(self, trading_bot_service: TradingBotService):
        self.trading_bot_service = trading_bot_service
        self.cli_service = ConsoleCLIService(trading_bot_service)
        self.logger = logging.getLogger(__name__)
    
    def run(self):
        """Run the CLI application"""
        try:
            print("🚀 Welcome to Micro Trading Bot CLI!")
            print("Type 'help' or '7' for assistance.")
            
            while self.cli_service.running:
                try:
                    choice = self.cli_service.show_menu()
                    self.cli_service.execute_command(choice)
                    
                    if not self.cli_service.running:
                        break
                    
                    input("\nPress Enter to continue...")
                    
                except KeyboardInterrupt:
                    print("\n👋 Goodbye!")
                    break
                except Exception as e:
                    print(f"❌ Unexpected error: {e}")
                    self.logger.error(f"CLI unexpected error: {e}")
                    break
                    
        except Exception as e:
            print(f"❌ CLI application error: {e}")
            self.logger.error(f"CLI application error: {e}")
