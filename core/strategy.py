# strategy.py

import pandas as pd
from core.technical_indicators import add_indicators
from core.ml_model import create_features, load_model

def apply_strategy(data) -> pd.DataFrame:
    """
    data: είτε list[dict] είτε pd.DataFrame με lowercase στήλες ['open','high','low','close','volume',…]
    Επιστρέφει DataFrame με στήλες ['open','high','low','close','volume',…,'signal'].
    """
    # 1) Φτιάχνουμε df
    if isinstance(data, pd.DataFrame):
        df = data.copy()
    else:
        # υποθέτουμε list[dict]
        df = pd.DataFrame(data).set_index("t")
        df.rename(columns={
            "o": "open", "h": "high", "l": "low",
            "c": "close", "v": "volume", "vw": "vwap"
        }, inplace=True)

    if df.empty:
        return df  # άδειο

    # 2) Προσθέτουμε indicators (όλα lowercase)
    df = add_indicators(df)

    # 3) Features & πρόβλεψη (αν υπάρχει model)
    try:
        X, _ = create_features(df)
        model = load_model()
        if model is None:
            raise ValueError("No trained model is available")
        df.loc[X.index, "prediction"] = model.predict(X)
    except Exception as e:
        # Αν δεν υπάρχει model ή υπάρχει πρόβλημα, χρησιμοποιούμε μόνο technical indicators
        df["prediction"] = 0
        print(f"Warning: ML model not available, using technical indicators only: {e}")

    # 4) Σήματα long/short
    df["signal"] = 0
    long_cond  = (df["close"] > df["sma_fast"]) & (df["sma_fast"] > df["sma_slow"])
    short_cond = (df["close"] < df["sma_fast"]) & (df["sma_fast"] < df["sma_slow"])
    df.loc[ long_cond, "signal"] =  1
    df.loc[short_cond, "signal"] = -1

    return df







