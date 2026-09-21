from decimal import Decimal

import pandas as pd
import pytest

from src.domain.entities import SignalType, TradingSignal
from src.domain.entities import Position, PositionSide
from src.domain.value_objects import Money
import scripts.paper_trading.multi_asset_loop as paper_loop
from scripts.paper_trading.multi_asset_loop import _atr_last, _position_size_from_atr


def test_trading_signal_rejects_invalid_confidence():
    with pytest.raises(ValueError):
        TradingSignal(symbol="AAPL", signal_type=SignalType.BUY, confidence=1.01)


def test_money_supports_losses():
    loss = Money(Decimal("10")) - Money(Decimal("12"))
    assert loss.amount == Decimal("-2")


def test_losing_position_has_negative_pnl():
    position = Position(
        symbol="AAPL",
        side=PositionSide.LONG,
        quantity=2,
        entry_price=Money(Decimal("100")),
        current_price=Money(Decimal("90")),
    )
    assert position.unrealized_pnl.amount == Decimal("-20")


def test_atr_uses_true_range():
    frame = pd.DataFrame(
        {
            "high": [11, 13, 14],
            "low": [9, 10, 12],
            "close": [10, 12, 13],
        }
    )
    assert _atr_last(frame, 2) == pytest.approx(2.5)


def test_position_size_is_capped_by_cash():
    qty = _position_size_from_atr(equity=100_000, cash=1_000, price=200, atr_val=1)
    assert qty == 5.0


@pytest.mark.parametrize(
    "equity,cash,price",
    [(0, 1000, 100), (1000, 0, 100), (1000, 1000, 0), (1000, 1000, -1)],
)
def test_position_size_rejects_invalid_account_values(equity, cash, price):
    assert _position_size_from_atr(equity, cash, price, 1) == 0.0


def test_trade_event_log_does_not_pretend_submission_is_fill(tmp_path, monkeypatch):
    trade_log = tmp_path / "trade_log.csv"
    monkeypatch.setattr(paper_loop, "TRADE_LOG_FILE", str(trade_log))

    paper_loop.append_trade_event("AAPL", "close", 105, 2, "trailing_stop", 0.05)

    recorded = pd.read_csv(trade_log)
    assert recorded.loc[0, "event_type"] == "order_submitted"
    assert recorded.loc[0, "symbol"] == "AAPL"
    assert pd.isna(recorded.loc[0, "pnl_pct"])
