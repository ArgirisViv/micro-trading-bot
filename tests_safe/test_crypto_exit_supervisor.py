from datetime import datetime,timezone,timedelta
import copy
import pytest
from core.execution_ledger import ExecutionLedger,LedgerError
from core.crypto_exit_supervisor import supervision_cycle,evaluate_exit

NOW=datetime(2026,9,16,15,tzinfo=timezone.utc)
POLICY=dict(stop_pct=.02,take_pct=.04,trail_pct=.01,partial_pct=.02,partial_ratio=.5)


@pytest.fixture
def owned(tmp_path):
    ledger=ExecutionLedger(tmp_path/'execution.sqlite3')
    intent=ledger.prepare_entry('BTCUSD',10,100,NOW,asset_class='crypto',exit_policy=POLICY)[0]
    root=dict(id='buy-1',client_order_id=intent['client_id'],symbol='BTC/USD',side='buy',
        qty='10',filled_qty='10',filled_avg_price='100',status='filled',filled_at=NOW,legs=[])
    ledger.observe_tree(intent['client_id'],root)
    class Broker:
        bid='100';ask='100.1';timestamp=NOW;calls=[];exits={};fail=False;fill='0'
        def get_account(self):return {'id':'dedicated-paper'}
        def get_positions(self):
            sold=sum(float(row['filled_qty']) for row in self.exits.values())
            return [dict(symbol='BTC/USD',qty=str(10-sold))] if sold<10 else []
        def get_order(self,key):return root if key=='buy-1' else self.exits.get(key)
        def get_order_by_client_order_id(self,key):
            return next((row for row in self.exits.values() if row['client_order_id']==key),None)
        def get_crypto_quote(self,symbol):return dict(bid=self.bid,ask=self.ask,timestamp=self.timestamp)
        def submit_crypto_exit(self,symbol,qty,client_id):
            disk=ExecutionLedger(ledger.path).snapshot()
            assert client_id in disk['unresolved_client_ids']
            self.calls.append((symbol,qty,client_id))
            if self.fail:raise TimeoutError()
            ack=dict(id='sell-'+str(len(self.calls)),client_order_id=client_id,symbol='BTC/USD',
                side='sell',qty=qty,filled_qty=self.fill,filled_avg_price=self.bid if self.fill!='0' else None,
                status='filled' if self.fill==qty else 'new',filled_at=NOW)
            self.exits[ack['id']]=ack
            return ack
    broker=Broker();broker.calls=[];broker.exits={}
    return ledger,intent,root,broker


@pytest.mark.parametrize('bid,reason',[('97','fixed_stop'),('105','take_profit'),('103','partial_take')])
def test_exit_policy_uses_fresh_bid_not_historical_candles(owned,bid,reason):
    ledger,_,_,broker=owned
    broker.bid=bid;broker.ask=str(float(bid)+.1)
    result=supervision_cycle(ledger,broker,NOW)
    assert result['submitted'][0]['reason']==reason
    assert len(broker.calls)==1
    assert float(broker.calls[0][1])==(5 if reason=='partial_take' else 10)


def test_pending_exit_blocks_second_post_even_after_restart(owned):
    ledger,_,_,broker=owned;broker.bid='97';broker.ask='98'
    supervision_cycle(ledger,broker,NOW)
    supervision_cycle(ExecutionLedger(ledger.path),broker,NOW)
    assert len(broker.calls)==1


def test_exit_timeout_retains_intent_and_never_reposts(owned):
    ledger,_,_,broker=owned;broker.bid='97';broker.ask='98';broker.fail=True
    result=supervision_cycle(ledger,broker,NOW)
    assert result['issues']
    assert ledger.snapshot()['blocked']
    supervision_cycle(ExecutionLedger(ledger.path),broker,NOW)
    assert len(broker.calls)==1


@pytest.mark.parametrize('problem',['stale','future','crossed','nan','zero'])
def test_bad_quote_never_updates_high_water_or_posts(owned,problem):
    ledger,_,_,broker=owned
    if problem=='stale':broker.timestamp=NOW-timedelta(seconds=11)
    elif problem=='future':broker.timestamp=NOW+timedelta(seconds=1)
    elif problem=='crossed':broker.bid='101';broker.ask='100'
    elif problem=='nan':broker.bid='NaN'
    elif problem=='zero':broker.bid='0'
    assert supervision_cycle(ledger,broker,NOW)['issues']
    assert broker.calls==[]


def test_high_water_persists_for_trailing_stop(owned):
    ledger,intent,_,broker=owned
    lot=ledger.snapshot()['inventory'][0]
    # Pure evaluation establishes high water without actually submitting its take.
    evaluate_exit(ledger,lot,dict(bid='110',ask='111',timestamp=NOW),NOW)
    broker.bid='108';broker.ask='109'
    result=supervision_cycle(ExecutionLedger(ledger.path),broker,NOW)
    assert result['submitted'][0]['reason']=='trailing_stop'


def test_partial_exit_fill_then_full_stop_accounts_remaining_only(owned):
    ledger,_,_,broker=owned;broker.bid='103';broker.ask='104';broker.fill='5.00000000'
    supervision_cycle(ledger,broker,NOW)
    assert ledger.snapshot()['inventory'][0]['open_qty']=='5.00000000'
    assert ledger.snapshot()['closed_trades']==[]
    broker.bid='97';broker.ask='98';broker.fill='5.00000000'
    supervision_cycle(ledger,broker,NOW)
    assert len(broker.calls)==2
    assert float(broker.calls[1][1])==5
    assert len(ledger.snapshot()['closed_trades'])==1


def test_external_quantity_change_blocks_all_mutations(owned):
    ledger,_,_,broker=owned;broker.bid='97';broker.ask='98'
    broker.get_positions=lambda:[dict(symbol='BTC/USD',qty=11)]
    assert supervision_cycle(ledger,broker,NOW)['issues']
    assert broker.calls==[]


def test_changed_persisted_policy_is_refused(owned):
    ledger,_,_,_=owned
    changed=copy.copy(POLICY);changed['stop_pct']=.03
    with pytest.raises(LedgerError):ledger.prepare_entry('BTCUSD',10,100,NOW,asset_class='crypto',exit_policy=changed)


def test_crypto_policy_is_required_before_intent_commit(tmp_path):
    ledger=ExecutionLedger(tmp_path/'db')
    with pytest.raises(LedgerError):ledger.prepare_entry('BTCUSD',10,100,NOW,asset_class='crypto')
    assert ledger.roots()==[]
