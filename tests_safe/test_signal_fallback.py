import pandas as pd

from core.enhanced_strategy import EnhancedStrategy


def test_technical_buy_can_proceed_when_ml_artifact_is_missing():
    strategy = EnhancedStrategy()
    frame = pd.DataFrame({
        "technical_signal": [1, -1],
        "ml_prediction": [0, 0],
        "ml_confidence": [0.0, 0.0],
        "ml_available": [False, False],
        "fundamental_score": [0.5, 0.5],
        "regime_signal_boost": [1.0, 1.0],
    })
    signals = strategy._generate_final_signals(frame)["signal"].tolist()
    assert signals == [1, -1]
