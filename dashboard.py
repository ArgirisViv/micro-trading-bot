# dashboard.py - Micro Trading Bot Dashboard
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os
import json

# Page config
st.set_page_config(
    page_title="Micro Trading Bot Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .status-online {
        color: #28a745;
        font-weight: bold;
    }
    .status-offline {
        color: #dc3545;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">🤖 Micro Trading Bot Dashboard</h1>', unsafe_allow_html=True)

# Sidebar
st.sidebar.title("🎛️ Control Panel")
st.sidebar.markdown("---")

# Bot Status
st.sidebar.subheader("📊 Bot Status")
bot_status = st.sidebar.selectbox(
    "Bot Status",
    ["🟢 Online", "🔴 Offline", "🟡 Maintenance"],
    index=0
)

# Trading Mode
trading_mode = st.sidebar.selectbox(
    "Trading Mode",
    ["📈 Paper Trading", "💰 Live Trading", "🧪 Backtesting"],
    index=0
)

# Risk Settings
st.sidebar.subheader("⚠️ Risk Management")
risk_per_trade = st.sidebar.slider("Risk per Trade (%)", 0.1, 5.0, 1.0, 0.1)
stop_loss = st.sidebar.slider("Stop Loss (%)", 1.0, 10.0, 2.0, 0.5)
take_profit = st.sidebar.slider("Take Profit (%)", 2.0, 20.0, 4.0, 0.5)

# Main Content
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="💰 Portfolio Value",
        value="$125,430.50",
        delta="+$2,340.25 (+1.9%)"
    )

with col2:
    st.metric(
        label="📈 Daily P&L",
        value="$1,245.80",
        delta="+$89.45 (+7.7%)"
    )

with col3:
    st.metric(
        label="🎯 Win Rate",
        value="68.5%",
        delta="+2.1%"
    )

with col4:
    st.metric(
        label="📊 Sharpe Ratio",
        value="1.87",
        delta="+0.15"
    )

# Trading Activity
st.markdown("---")
st.subheader("📊 Trading Activity")

# Recent Trades
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🔄 Recent Trades")
    
    # Mock data for recent trades
    trades_data = {
        'Symbol': ['AAPL', 'TSLA', 'GOOGL', 'MSFT', 'NVDA'],
        'Side': ['BUY', 'SELL', 'BUY', 'SELL', 'BUY'],
        'Quantity': [100, 50, 75, 200, 25],
        'Price': [175.50, 245.80, 142.30, 380.90, 890.25],
        'P&L': [1250.50, -450.80, 890.30, -120.90, 2340.25],
        'Time': ['10:30 AM', '11:15 AM', '12:00 PM', '12:45 PM', '01:30 PM']
    }
    
    trades_df = pd.DataFrame(trades_data)
    st.dataframe(trades_df, width="stretch")

with col2:
    st.subheader("📈 Position Summary")
    
    positions_data = {
        'Symbol': ['AAPL', 'GOOGL', 'NVDA'],
        'Side': ['LONG', 'LONG', 'LONG'],
        'Quantity': [100, 75, 25],
        'Avg Price': [175.50, 142.30, 890.25],
        'Current P&L': [1250.50, 890.30, 2340.25]
    }
    
    positions_df = pd.DataFrame(positions_data)
    st.dataframe(positions_df, width="stretch")

# Performance Charts
st.markdown("---")
st.subheader("📈 Performance Analytics")

# Equity Curve
col1, col2 = st.columns(2)

with col1:
    st.subheader("💰 Equity Curve")
    
    # Mock equity curve data
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    equity_values = [100000 + i * 100 + (i % 30) * 50 for i in range(len(dates))]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=equity_values,
        mode='lines',
        name='Portfolio Value',
        line=dict(color='#1f77b4', width=2)
    ))
    
    fig.update_layout(
        title="Portfolio Performance Over Time",
        xaxis_title="Date",
        yaxis_title="Portfolio Value ($)",
        height=400
    )
    
    st.plotly_chart(fig, width="stretch")

with col2:
    st.subheader("📊 Drawdown Analysis")
    
    # Mock drawdown data
    drawdown_values = [0] + [-max(0, (max(equity_values[:i+1]) - equity_values[i]) / max(equity_values[:i+1]) * 100) for i in range(1, len(equity_values))]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=drawdown_values,
        mode='lines',
        name='Drawdown %',
        line=dict(color='#ff7f0e', width=2),
        fill='tonexty'
    ))
    
    fig.update_layout(
        title="Maximum Drawdown",
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        height=400
    )
    
    st.plotly_chart(fig, width="stretch")

# Risk Metrics
st.markdown("---")
st.subheader("⚠️ Risk Metrics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Maximum Drawdown", "-8.5%", "-0.3%")
    
with col2:
    st.metric("Volatility (Annual)", "12.3%", "-0.8%")
    
with col3:
    st.metric("VaR (95%)", "-2.1%", "+0.2%")
    
with col4:
    st.metric("Beta", "0.95", "-0.05")

# System Status
st.markdown("---")
st.subheader("🔧 System Status")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📡 API Connections")
    
    # Mock API status
    apis = {
        'Alpaca Trading': '🟢 Connected',
        'Alpaca Data': '🟢 Connected',
        'Yahoo Finance': '🟢 Connected',
        'Telegram Bot': '🟢 Connected'
    }
    
    for api, status in apis.items():
        st.write(f"{api}: {status}")

with col2:
    st.subheader("📊 Data Quality")
    
    # Mock data quality metrics
    quality_metrics = {
        'Data Completeness': '98.5%',
        'Data Accuracy': '99.2%',
        'Update Frequency': '5 min',
        'Last Update': '2 min ago'
    }
    
    for metric, value in quality_metrics.items():
        st.write(f"{metric}: {value}")

with col3:
    st.subheader("🚨 Alerts")
    
    # Mock alerts
    alerts = [
        "⚠️ High volatility detected",
        "📈 Take profit triggered for AAPL",
        "🔄 Position rebalanced",
        "✅ Daily target reached"
    ]
    
    for alert in alerts:
        st.write(alert)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <p>🤖 Micro Trading Bot Dashboard | Last updated: {}</p>
        <p>Built with ❤️ using Streamlit & Plotly</p>
    </div>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    unsafe_allow_html=True
)

# Auto-refresh
if st.button("🔄 Refresh Data"):
    st.rerun()

# Auto-refresh every 30 seconds
st.markdown("""
<script>
    setTimeout(function(){
        window.location.reload();
    }, 30000);
</script>
""", unsafe_allow_html=True)
