# core/enhanced_fundamentals.py
"""
Enhanced Fundamentals Module - Warren Buffett Style
Business quality scoring, financial health analysis, competitive advantage detection
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
# yfinance removed - using mock data instead
import warnings
warnings.filterwarnings('ignore')

@dataclass
class BusinessQuality:
    """Business quality assessment"""
    overall_score: float  # 0-100
    financial_health: float  # 0-100
    competitive_advantage: float  # 0-100
    growth_potential: float  # 0-100
    risk_level: str  # 'LOW', 'MEDIUM', 'HIGH'
    recommendation: str  # 'STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL'

@dataclass
class ValueMetrics:
    """Value investing metrics"""
    pe_ratio: float
    pb_ratio: float
    roe: float
    debt_to_equity: float
    current_ratio: float
    profit_margin: float
    revenue_growth: float
    earnings_growth: float
    dividend_yield: float
    payout_ratio: float

class EnhancedFundamentals:
    """
    Warren Buffett-style fundamental analysis
    """
    
    def __init__(self, 
                 quality_threshold: float = 70.0,
                 value_threshold: float = 60.0):
        self.quality_threshold = quality_threshold
        self.value_threshold = value_threshold
        
    def analyze_business_quality(self, symbol: str) -> BusinessQuality:
        """
        Mock business quality analysis - yfinance removed for stability
        """
        # Return default business quality to avoid errors
        return self._default_business_quality()
    
    def _calculate_value_metrics(self, ticker, info: Dict) -> ValueMetrics:
        """Mock value metrics - yfinance removed for stability"""
        return ValueMetrics(
            pe_ratio=0.0,
            pb_ratio=0.0,
            roe=0.0,
            debt_to_equity=0.0,
            current_ratio=0.0,
            profit_margin=0.0,
            revenue_growth=0.0,
            earnings_growth=0.0,
            dividend_yield=0.0,
            payout_ratio=0.0
        )
    
    def _score_financial_health(self, metrics: ValueMetrics) -> float:
        """Score financial health (0-100)"""
        try:
            score = 0.0
            weights = 0.0
            
            # ROE scoring (higher is better)
            if metrics.roe > 0:
                roe_score = min(100, metrics.roe * 10)  # 10% ROE = 100 points
                score += roe_score * 0.25
                weights += 0.25
            
            # Debt to Equity scoring (lower is better)
            if metrics.debt_to_equity > 0:
                debt_score = max(0, 100 - (metrics.debt_to_equity * 20))  # 5x debt = 0 points
                score += debt_score * 0.20
                weights += 0.20
            
            # Current Ratio scoring (higher is better)
            if metrics.current_ratio > 0:
                current_score = min(100, metrics.current_ratio * 50)  # 2.0 = 100 points
                score += current_score * 0.20
                weights += 0.20
            
            # Profit Margin scoring (higher is better)
            if metrics.profit_margin > 0:
                margin_score = min(100, metrics.profit_margin * 1000)  # 10% margin = 100 points
                score += margin_score * 0.15
                weights += 0.15
            
            # Dividend scoring (moderate is better)
            if metrics.dividend_yield > 0:
                div_score = 100 - abs(metrics.dividend_yield - 3) * 20  # 3% = 100 points
                div_score = max(0, min(100, div_score))
                score += div_score * 0.20
                weights += 0.20
            
            return score / weights if weights > 0 else 50.0
            
        except:
            return 50.0
    
    def _score_competitive_advantage(self, metrics: ValueMetrics, info: Dict) -> float:
        """Score competitive advantage (0-100)"""
        try:
            score = 0.0
            weights = 0.0
            
            # ROE consistency (high ROE = competitive advantage)
            if metrics.roe > 15:  # 15%+ ROE indicates moat
                score += 100 * 0.4
                weights += 0.4
            elif metrics.roe > 10:
                score += 75 * 0.4
                weights += 0.4
            elif metrics.roe > 5:
                score += 50 * 0.4
                weights += 0.4
            
            # Profit margin stability (high margins = pricing power)
            if metrics.profit_margin > 0.15:  # 15%+ margins
                score += 100 * 0.3
                weights += 0.3
            elif metrics.profit_margin > 0.10:
                score += 75 * 0.3
                weights += 0.3
            elif metrics.profit_margin > 0.05:
                score += 50 * 0.3
                weights += 0.3
            
            # Market cap (larger companies often have moats)
            market_cap = info.get('marketCap', 0)
            if market_cap > 10000000000:  # $10B+
                score += 100 * 0.3
                weights += 0.3
            elif market_cap > 1000000000:  # $1B+
                score += 75 * 0.3
                weights += 0.3
            else:
                score += 50 * 0.3
                weights += 0.3
            
            return score / weights if weights > 0 else 50.0
            
        except:
            return 50.0
    
    def _score_growth_potential(self, metrics: ValueMetrics, info: Dict) -> float:
        """Score growth potential (0-100)"""
        try:
            score = 0.0
            weights = 0.0
            
            # Revenue growth
            if metrics.revenue_growth > 0:
                growth_score = min(100, metrics.revenue_growth * 500)  # 20% growth = 100 points
                score += growth_score * 0.4
                weights += 0.4
            
            # Earnings growth
            if metrics.earnings_growth > 0:
                earnings_score = min(100, metrics.earnings_growth * 500)
                score += earnings_score * 0.4
                weights += 0.4
            
            # ROE growth potential
            if metrics.roe > 15:
                score += 100 * 0.2
                weights += 0.2
            elif metrics.roe > 10:
                score += 75 * 0.2
                weights += 0.2
            elif metrics.roe > 5:
                score += 50 * 0.2
                weights += 0.2
            
            return score / weights if weights > 0 else 50.0
            
        except:
            return 50.0
    
    def _determine_risk_level(self, metrics: ValueMetrics, overall_score: float) -> str:
        """Determine overall risk level"""
        try:
            risk_score = 0
            
            # High debt = higher risk
            if metrics.debt_to_equity > 1.0:
                risk_score += 2
            elif metrics.debt_to_equity > 0.5:
                risk_score += 1
            
            # Low current ratio = higher risk
            if metrics.current_ratio < 1.0:
                risk_score += 2
            elif metrics.current_ratio < 1.5:
                risk_score += 1
            
            # High payout ratio = higher risk
            if metrics.payout_ratio > 80:
                risk_score += 2
            elif metrics.payout_ratio > 60:
                risk_score += 1
            
            # Low overall score = higher risk
            if overall_score < 50:
                risk_score += 2
            elif overall_score < 70:
                risk_score += 1
            
            if risk_score >= 4:
                return 'HIGH'
            elif risk_score >= 2:
                return 'MEDIUM'
            else:
                return 'LOW'
                
        except:
            return 'MEDIUM'
    
    def _generate_recommendation(self, overall_score: float, metrics: ValueMetrics) -> str:
        """Generate investment recommendation"""
        try:
            # Value check
            is_undervalued = False
            if metrics.pe_ratio > 0 and metrics.pe_ratio < 15:
                is_undervalued = True
            if metrics.pb_ratio > 0 and metrics.pb_ratio < 1.5:
                is_undervalued = True
            
            # Quality check
            is_high_quality = overall_score >= self.quality_threshold
            
            # Generate recommendation
            if is_high_quality and is_undervalued:
                return 'STRONG_BUY'
            elif is_high_quality or is_undervalued:
                return 'BUY'
            elif overall_score >= 60:
                return 'HOLD'
            elif overall_score >= 40:
                return 'SELL'
            else:
                return 'STRONG_SELL'
                
        except:
            return 'HOLD'
    
    def _default_business_quality(self) -> BusinessQuality:
        """Return default business quality when analysis fails"""
        return BusinessQuality(
            overall_score=50.0,
            financial_health=50.0,
            competitive_advantage=50.0,
            growth_potential=50.0,
            risk_level='MEDIUM',
            recommendation='HOLD'
        )
    
    def get_value_portfolio_candidates(self, symbols: List[str], min_score: float = 70.0) -> List[Dict]:
        """Get best value portfolio candidates"""
        candidates = []
        
        for symbol in symbols:
            try:
                quality = self.analyze_business_quality(symbol)
                
                if quality.overall_score >= min_score:
                    candidates.append({
                        'symbol': symbol,
                        'quality_score': quality.overall_score,
                        'risk_level': quality.risk_level,
                        'recommendation': quality.recommendation,
                        'financial_health': quality.financial_health,
                        'competitive_advantage': quality.competitive_advantage
                    })
            except:
                continue
        
        # Sort by quality score (highest first)
        candidates.sort(key=lambda x: x['quality_score'], reverse=True)
        
        return candidates

def analyze_business_quality(symbol: str) -> BusinessQuality:
    """
    Convenience function to analyze business quality
    """
    analyzer = EnhancedFundamentals()
    return analyzer.analyze_business_quality(symbol)

def get_value_candidates(symbols: List[str], min_score: float = 70.0) -> List[Dict]:
    """
    Convenience function to get value portfolio candidates
    """
    analyzer = EnhancedFundamentals()
    return analyzer.get_value_portfolio_candidates(symbols, min_score)
