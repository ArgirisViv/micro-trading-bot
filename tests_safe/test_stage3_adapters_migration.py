import sqlite3
from types import SimpleNamespace
import pytest
from core import alpaca_trade as broker
from core.execution_ledger import ExecutionLedger,LedgerError


def test_v1_ledger_migration_preserves_order_and_does_not_create_crypto_ownership(tmp_path):
    path=tmp_path/'db.sqlite3'
    ledger=ExecutionLedger(path)
    intent=ledger.prepare_entry('AAPL',10,100,'2026-09-16T15:00Z')[0]
    with sqlite3.connect(path) as db:
        db.execute('ALTER TABLE orders DROP COLUMN asset_class')
        db.execute('PRAGMA user_version=1')
    with pytest.raises(LedgerError):ExecutionLedger(path,readonly=True).snapshot()
    migrated=ExecutionLedger(path).snapshot()
    assert migrated['schema_version']==2
    assert migrated['orders'][0]['client_id']==intent['client_id']
    assert migrated['orders'][0]['asset_class']=='stocks'
    assert migrated['inventory']==[]


def test_crypto_exit_adapter_rechecks_long_qty_and_uses_stable_id(monkeypatch):
    calls=[]
    class Client:
        def list_orders(self,**kwargs):return []
        def submit_order(self,**params):calls.append(params);return params
    monkeypatch.setattr(broker,'CRYPTO_WATCHLIST',['BTCUSD'])
    monkeypatch.setattr(broker,'get_position',lambda symbol:SimpleNamespace(qty='10'))
    monkeypatch.setattr(broker,'_client_for',lambda symbol:Client())
    broker.submit_crypto_exit('BTCUSD','5','stable-client-id')
    assert calls[0]['symbol']=='BTC/USD'
    assert calls[0]['side']=='sell'
    assert calls[0]['time_in_force']=='gtc'
    assert calls[0]['client_order_id']=='stable-client-id'


@pytest.mark.parametrize('qty',['0','-1','4','NaN','Infinity'])
def test_crypto_exit_cannot_short_or_close_invalid_broker_inventory(monkeypatch,qty):
    monkeypatch.setattr(broker,'CRYPTO_WATCHLIST',['BTCUSD'])
    monkeypatch.setattr(broker,'get_position',lambda symbol:SimpleNamespace(qty=qty))
    monkeypatch.setattr(broker,'_client_for',lambda symbol:pytest.fail('must not POST'))
    with pytest.raises(ValueError):broker.submit_crypto_exit('BTCUSD','5','stable-id')


def test_crypto_exit_conflicting_order_blocks_post(monkeypatch):
    class Client:
        def list_orders(self,**kwargs):return [SimpleNamespace(symbol='BTC/USD')]
        def submit_order(self,**kwargs):pytest.fail('conflicting close posted')
    monkeypatch.setattr(broker,'CRYPTO_WATCHLIST',['BTCUSD'])
    monkeypatch.setattr(broker,'get_position',lambda symbol:SimpleNamespace(qty='10'))
    monkeypatch.setattr(broker,'_client_for',lambda symbol:Client())
    with pytest.raises(RuntimeError):broker.submit_crypto_exit('BTCUSD','5','stable-id')


def test_crypto_supervisor_api_does_not_invent_healthy_status(client):
    data=client.get('/api/crypto-exits').json
    assert not data['available']
    assert not data['fresh']
