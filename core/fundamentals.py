# core/fundamentals.py

import math
import time
from typing import Dict, List, Optional, Tuple
# yfinance removed - using mock data instead

def _safe(val, default=None):
    try:
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return default
        return float(val)
    except Exception:
        return default

def fetch_fundamentals(ticker: str) -> Dict[str, Optional[float]]:
    """Mock fundamentals data - yfinance removed for stability."""
    # Return empty fundamentals to avoid errors
    return {
        "market_cap": None,
        "pe": None,
        "pb": None,
        "roe": None,
        "profit_margin": None,
        "debt_to_equity": None,
        "fcf_yield": None,
    }

def _zscore(x: Optional[float], series: List[Optional[float]], reverse: bool = False) -> float:
    """Απλός z-score κανονικοποίησης για σύγκριση (με reverse για 'μικρότερο=καλύτερο')."""
    vals = [v for v in series if v is not None]
    if len(vals) < 5 or x is None:
        return 0.0
    mu = sum(vals)/len(vals)
    var = sum((v-mu)**2 for v in vals)/len(vals)
    sd = math.sqrt(var) if var>0 else 1.0
    z = (x - mu) / sd
    return -z if reverse else z

def _build_matrix(
    raw: Dict[str, Dict[str, Optional[float]]]
) -> Dict[str, List[Optional[float]]]:
    """Φτιάχνει ‘πίνακα’ τιμών ανά metric για κανονικοποίηση."""
    keys = list(raw.keys())
    cols = ["pe","pb","roe","fcf_yield","debt_to_equity","profit_margin"]
    series = {c: [] for c in cols}
    for k in keys:
        d = raw[k]
        for c in cols:
            series[c].append(d.get(c))
    return series

def score_tickers(tickers: List[str], weights: Dict[str, float], min_mcap: float) -> List[Tuple[str, float, Dict]]:
    """Υπολογίζει composite score ανά ticker με βάρη (τύπου Buffett)."""
    # 1) Fetch με λίγη ευγένεια (για να μην μας κόψει το rate limiting)
    raw: Dict[str, Dict[str, Optional[float]]] = {}
    for i, tk in enumerate(tickers):
        d = fetch_fundamentals(tk)
        market_cap = d.get("market_cap")
        if market_cap is not None and market_cap >= min_mcap:
            raw[tk] = d
        # μικρό sleep
        if i % 8 == 7:
            time.sleep(0.8)

    if not raw:
        return []

    # 2) Κανονικοποίηση
    series = _build_matrix(raw)
    scored: List[Tuple[str, float, Dict]] = []
    for tk, d in raw.items():
        s = 0.0
        # Προκαθορίζουμε ποια μετρικά είναι “μικρότερο=καλύτερο”
        s += weights.get("pe",0.0)              * _zscore(d.get("pe"),   series["pe"],   reverse=True)
        s += weights.get("pb",0.0)              * _zscore(d.get("pb"),   series["pb"],   reverse=True)
        s += weights.get("roe",0.0)             * _zscore(d.get("roe"),  series["roe"])
        s += weights.get("fcf_yield",0.0)       * _zscore(d.get("fcf_yield"), series["fcf_yield"])
        s += weights.get("debt_to_equity",0.0)  * _zscore(d.get("debt_to_equity"), series["debt_to_equity"], reverse=True)
        s += weights.get("profit_margin",0.0)   * _zscore(d.get("profit_margin"), series["profit_margin"])
        scored.append((tk, s, d))

    # 3) Ταξινόμηση κατά score φθίνουσα
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored

def build_value_universe(all_stock_tickers: List[str], top_n: int, min_mcap: float, weights: Dict[str, float]) -> List[str]:
    ranked = score_tickers(all_stock_tickers, weights, min_mcap)
    return [tk for (tk, _, _) in ranked[:top_n]]
