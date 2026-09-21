"""Execute the actual loop with entirely fake broker/feed/clock, never network."""
import json
from datetime import datetime, timezone
from types import SimpleNamespace
import pandas as pd
import pytest
from scripts.paper_trading import multi_asset_loop as loop
from core.execution_runtime import refresh_execution


class EndCycle(BaseException): pass


def setup_loop(tmp_path, monkeypatch, *, approved=False, position=None, outcome='accepted'):
    now = datetime(2026,9,16,15,0,tzinfo=timezone.utc)
    state_path = tmp_path/'state.json'
    monkeypatch.setattr(loop,'STATE_FILE',str(state_path))
    monkeypatch.setattr(loop,'TRADE_LOG_FILE',str(tmp_path/'trades.csv'))
    monkeypatch.setattr(loop,'PAPER_EQUITY_CSV',str(tmp_path/'equity.csv'))
    monkeypatch.setattr(loop,'ASSET_CLASSES',['stocks'])
    monkeypatch.setattr(loop,'STOCK_WATCHLIST',['AAPL','MSFT'])
    monkeypatch.setattr(loop,'TIMEFRAME','5min')
    monkeypatch.setattr(loop,'utcnow',lambda: now)
    monkeypatch.setattr(loop,'notify',lambda *args:None)
    monkeypatch.setattr(loop,'entries_enabled',lambda:True)
    monkeypatch.setenv('PAPER_ENTRIES_APPROVED','true' if approved else 'false')
    monkeypatch.setattr(loop,'is_stock_market_open',lambda:True)
    monkeypatch.setattr(loop,'get_account',lambda:SimpleNamespace(equity='100000',cash='1000'))
    monkeypatch.setattr(loop,'get_open_positions_count',lambda: 1 if position else 0)
    monkeypatch.setattr(loop,'get_open_orders_count',lambda:0)
    monkeypatch.setattr(loop,'get_position',lambda symbol:position)
    monkeypatch.setattr(loop,'get_latest_stock_price',lambda symbol:100.)
    bars = pd.DataFrame(dict(open=[100]*40, high=[101]*40,low=[99]*40,
        close=[100]*40, volume=[10]*40),index=pd.date_range('2026-09-16T11:40Z',periods=40,freq='5min'))
    monkeypatch.setattr(loop,'get_live_data',lambda symbol:bars.copy())
    monkeypatch.setattr(loop,'apply_enhanced_strategy',lambda df,symbol:df.assign(signal=1,confidence_score=.8))
    monkeypatch.setattr(loop,'should_send_daily_report',lambda state:False)
    monkeypatch.setattr(loop,'should_send_weekly_report',lambda state:False)
    def end_cycle(tf): raise EndCycle()
    monkeypatch.setattr(loop,'_sleep_until_next_bar',end_cycle)
    orders=[]
    acknowledgments={}
    class FakeBroker:
        def get_account(self):return {'id':'offline-paper-account'}
        def get_positions(self):
            return [dict(symbol='AAPL',qty='5')] if position else []
        def get_order(self,order_id):
            return acknowledgments.get(order_id)
        def get_order_by_client_order_id(self,client_id):
            return next((ack for ack in acknowledgments.values()
                         if ack['client_order_id']==client_id),None)
    monkeypatch.setattr(loop,'refresh_execution',lambda ledger:refresh_execution(ledger,broker=FakeBroker()))
    def submit(**params):
        # The durable uncertainty flag and same ID MUST predate broker mutation.
        disk=json.loads(state_path.read_text())
        assert disk['execution_uncertain'] is True
        assert disk['last_order_intent']['client_order_id'] == params['client_order_id']
        orders.append(params)
        if outcome == 'timeout': raise TimeoutError('simulated uncertainty')
        ack=dict(id='fake-order-1',client_order_id=params['client_order_id'],symbol=params['symbol'],
                 side='buy',qty=str(params['qty']),filled_qty='0',filled_avg_price=None,
                 status='new',legs=[])
        acknowledgments[ack['id']]=ack
        return ack
    monkeypatch.setattr(loop,'submit_order',submit)
    return state_path,orders


def cycle():
    with pytest.raises(EndCycle): loop._run_multi_asset_loop()


def test_default_release_never_submits_even_operator_resumed(tmp_path,monkeypatch):
    _,orders=setup_loop(tmp_path,monkeypatch)
    cycle()
    assert orders == []


def test_one_pending_entry_blocks_second_symbol(tmp_path,monkeypatch):
    path,orders=setup_loop(tmp_path,monkeypatch,approved=True)
    cycle()
    assert len(orders) == 1
    assert orders[0]['qty']*orders[0]['reference_price'] <= 1000
    assert json.loads(path.read_text())['last_order_intent']['status'] == 'submitted'


def test_timeout_blocks_later_symbols_and_survives_restart(tmp_path,monkeypatch):
    path,orders=setup_loop(tmp_path,monkeypatch,approved=True,outcome='timeout')
    cycle()
    assert len(orders) == 1
    assert json.loads(path.read_text())['execution_uncertain']
    cycle()
    assert len(orders) == 1


def test_external_position_not_adopted_or_closed(tmp_path,monkeypatch):
    path,orders=setup_loop(tmp_path,monkeypatch,approved=True,
        position=SimpleNamespace(avg_entry_price='90',qty='5'))
    def forbidden(*args,**kwargs): raise AssertionError('Must not close external positions')
    monkeypatch.setattr(loop,'close_position',forbidden)
    cycle()
    state=json.loads(path.read_text())
    assert orders == []
    assert state['entry_price']['AAPL'] is None
    assert state['external_positions']['AAPL']


def test_corrupt_runtime_is_not_silently_reset(tmp_path,monkeypatch):
    path,_=setup_loop(tmp_path,monkeypatch)
    path.write_text('{broken')
    with pytest.raises(RuntimeError): loop.load_state()
