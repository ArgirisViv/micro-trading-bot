from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import copy
from typing import Any
import pytest
from core.execution_ledger import ExecutionLedger, LedgerError, reconcile, verify_positions
from core.execution_runtime import initialize_ledger, refresh_execution, apply_execution_state

TIME='2026-09-16T15:00:00+00:00'


@pytest.fixture
def ledger(tmp_path): return ExecutionLedger(tmp_path/'execution.sqlite3')


def prepare(ledger: ExecutionLedger, qty: Any = 10) -> dict[str, Any]:
    return ledger.prepare_entry('AAPL',qty,100,TIME)[0]


def order(intent: dict[str, Any], *, filled: Any = '0', avg: Any = None,
          status: str = 'new', legs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return dict(id='entry-broker-1',client_order_id=intent['client_id'],symbol='AAPL',
        side='buy',qty=intent['requested_qty'],filled_qty=str(filled),filled_avg_price=avg,
        status=status,updated_at=TIME,filled_at=TIME if str(filled)!='0' else None,
        legs=legs or [])


def leg(*,filled: Any = '0', avg: Any = None, status: str = 'new',
        name: str = 'take', qty: Any = '10') -> dict[str, Any]:
    return dict(id='leg-broker-'+name,client_order_id='broker-leg-'+name,symbol='AAPL',
        type='stop' if name=='stop' else 'limit',
        side='sell',qty=qty,filled_qty=str(filled),filled_avg_price=avg,status=status,
        updated_at=TIME,filled_at=TIME if str(filled)!='0' else None)


def test_intent_is_durable_before_ack_and_duplicate_cannot_repost(ledger):
    intent=prepare(ledger)
    reopened=ExecutionLedger(ledger.path)
    duplicate,created=reopened.prepare_entry('AAPL',10,100,TIME)
    assert not created
    assert duplicate['client_id']==intent['client_id']
    assert reopened.snapshot()['blocked']
    assert reopened.snapshot()['reserved_reference_notional']=='1000'


def test_two_threads_get_one_created_intent(ledger):
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:ledger.prepare_entry('AAPL',10,100,TIME),range(2)))
    assert sum(created for _,created in results)==1
    assert len(ledger.roots())==1


def test_duplicate_key_with_changed_parameters_refused(ledger):
    prepare(ledger)
    with pytest.raises(LedgerError): ledger.prepare_entry('AAPL',20,100,TIME)


@pytest.mark.parametrize('qty,price', [('NaN',100),('Infinity',100),(-1,100),(0,100),(1,0),(1,'NaN')])
def test_invalid_intent_never_written(ledger,qty,price):
    with pytest.raises(LedgerError):ledger.prepare_entry('AAPL',qty,price,TIME)
    assert ledger.roots()==[]


def test_accepted_order_has_no_invented_inventory_or_pnl(ledger):
    intent=prepare(ledger)
    ledger.observe_tree(intent['client_id'],order(intent))
    snapshot=ledger.snapshot()
    assert snapshot['inventory']==[]
    assert snapshot['closed_trades']==[]
    assert snapshot['pending_entries']==1
    assert not snapshot['blocked']


def test_duplicate_partial_fill_applied_once_and_restart_preserves_it(ledger):
    intent=prepare(ledger)
    ack=order(intent,filled='4',avg='100',status='partially_filled')
    ledger.observe_tree(intent['client_id'],ack)
    reopened=ExecutionLedger(ledger.path)
    reopened.observe_tree(intent['client_id'],ack)
    snapshot=reopened.snapshot()
    assert snapshot['fill_checkpoints']==1
    assert snapshot['inventory'][0]['open_qty']=='4'
    assert snapshot['inventory'][0]['open_cost']=='400'
    assert snapshot['reserved_reference_notional']=='600'


def test_weighted_fill_notional_is_delta_not_last_average_times_delta(ledger):
    intent=prepare(ledger)
    ledger.observe_tree(intent['client_id'],order(intent,filled='4',avg='100',status='partially_filled'))
    ledger.observe_tree(intent['client_id'],order(intent,filled='10',avg='106',status='filled'))
    lot=ledger.snapshot()['inventory'][0]
    assert lot['open_qty']=='10'
    assert lot['open_cost']=='1060'
    with ledger.connection() as db:
        delta=db.execute('SELECT delta_notional FROM checkpoints ORDER BY id DESC').fetchone()[0]
    assert delta=='660'


def test_nested_bracket_partial_exit_is_not_a_completed_trade(ledger):
    intent=prepare(ledger)
    ledger.observe_tree(intent['client_id'],order(intent,filled=10,avg='106',status='filled',legs=[leg(),leg(name='stop')]))
    ledger.observe_tree(intent['client_id'],order(intent,filled=10,avg='106',status='filled',
        legs=[leg(filled=3,avg='120',status='partially_filled'),leg(name='stop',qty='7')]))
    snapshot=ledger.snapshot()
    assert snapshot['closed_trades']==[]
    assert snapshot['inventory'][0]['open_qty']=='7'
    assert snapshot['inventory'][0]['realized_gross']=='42'
    assert len(snapshot['orders'])==3


def test_full_bracket_exit_realizes_one_position_trade_and_replay_is_idempotent(ledger):
    intent=prepare(ledger)
    partial=order(intent,filled=10,avg='106',status='filled',
        legs=[leg(filled=3,avg='120',status='partially_filled'),leg(name='stop',qty='7')])
    ledger.observe_tree(intent['client_id'],partial)
    final=order(intent,filled=10,avg='106',status='filled',
        legs=[leg(filled=10,avg='120',status='filled'),leg(name='stop',qty='7',status='canceled')])
    ledger.observe_tree(intent['client_id'],final)
    ledger.observe_tree(intent['client_id'],final)
    snapshot=ledger.snapshot()
    assert len(snapshot['closed_trades'])==1
    assert snapshot['closed_trades'][0]['realized_gross']=='140'
    assert snapshot['closed_trades'][0]['open_qty']=='0'
    assert snapshot['fill_checkpoints']==3


@pytest.mark.parametrize('status',['canceled','expired','rejected'])
def test_explicit_unfilled_terminal_status_releases_reservation(ledger,status):
    intent=prepare(ledger)
    ledger.observe_tree(intent['client_id'],order(intent,status=status))
    assert ledger.snapshot()['reserved_reference_notional']=='0'
    assert ledger.snapshot()['inventory']==[]


def test_canceled_partial_entry_keeps_owned_inventory_not_full_requested_qty(ledger):
    intent=prepare(ledger)
    ledger.observe_tree(intent['client_id'],order(intent,filled='4',avg='100',status='canceled'))
    snapshot=ledger.snapshot()
    assert snapshot['inventory'][0]['open_qty']=='4'
    assert snapshot['pending_entries']==0
    assert snapshot['reserved_reference_notional']=='0'


@pytest.mark.parametrize('mutation', ['client','symbol','side','qty','nan','regression','correction',
    'unknown_status','terminal_regression','incomplete_filled','replaced','missing_time'])
def test_inconsistent_snapshots_quarantine_without_mutating_inventory(ledger,mutation):
    intent=prepare(ledger)
    ack=order(intent,filled='4',avg='100',status='partially_filled')
    ledger.observe_tree(intent['client_id'],ack)
    wrong=copy.deepcopy(ack)
    if mutation=='client':wrong['client_order_id']='other'
    elif mutation=='symbol':wrong['symbol']='MSFT'
    elif mutation=='side':wrong['side']='sell'
    elif mutation=='qty':wrong['qty']='11'
    elif mutation=='nan':wrong['filled_qty']='NaN'
    elif mutation=='regression':wrong['filled_qty']='3'
    elif mutation=='correction':wrong['filled_avg_price']='101'
    elif mutation=='unknown_status':wrong['status']='mysterious'
    elif mutation=='terminal_regression':
        ledger.observe_tree(intent['client_id'],order(intent,filled='4',avg='100',status='canceled'))
        wrong['status']='new'
    elif mutation=='incomplete_filled':wrong['status']='filled'
    elif mutation=='replaced':wrong['replaced_by']='other-broker-order'
    elif mutation=='missing_time':
        wrong.update(filled_qty='5',filled_at=None,updated_at=None)
    with pytest.raises(LedgerError):ledger.observe_tree(intent['client_id'],wrong)
    snapshot=ExecutionLedger(ledger.path).snapshot()
    assert snapshot['blocked']
    assert snapshot['faults']
    assert snapshot['inventory'][0]['open_qty']=='4'


def test_overclosing_two_bracket_legs_rolls_back_whole_tree(ledger):
    intent=prepare(ledger)
    bad=order(intent,filled=10,avg='100',status='filled',legs=[
        leg(filled=10,avg='110',status='filled'),leg(name='stop',filled=10,avg='90',status='filled')])
    with pytest.raises(LedgerError):ledger.observe_tree(intent['client_id'],bad)
    snapshot=ledger.snapshot()
    assert snapshot['inventory']==[]
    assert snapshot['fill_checkpoints']==0
    assert snapshot['blocked']


def test_wrong_symbol_child_never_adopted(ledger):
    intent=prepare(ledger)
    wrong=leg();wrong['symbol']='MSFT'
    with pytest.raises(LedgerError):ledger.observe_tree(intent['client_id'],order(intent,legs=[wrong]))
    assert len(ledger.snapshot()['orders'])==1


class FakeBroker:
    def __init__(self, root: dict[str, Any] | None = None,
                 positions: list[dict[str, Any]] | None = None, failed: bool = False):
        self.root=root;self.positions=positions or [];self.failed=failed;self.reads=[]
    def get_account(self) -> dict[str, str | None]:return {'id':'offline-paper-account'}
    def get_order_by_client_order_id(self,client_id):
        self.reads.append(('client',client_id))
        if self.failed:raise TimeoutError('sensitive URL must not be exposed')
        return self.root
    def get_order(self,broker_id):
        self.reads.append(('nested',broker_id))
        if self.failed:raise TimeoutError('sensitive URL must not be exposed')
        return self.root
    def get_positions(self):return self.positions
    def submit_order(self,*args,**kwargs):raise AssertionError('Reconciliation must never POST')


def test_404_does_not_release_intent_or_authorize_resubmission(ledger):
    intent=prepare(ledger)
    result=reconcile(ledger,FakeBroker())
    assert result['blocked']
    assert result['reserved_reference_notional']=='1000'
    assert intent['client_id'] in result['unresolved_client_ids']


def test_timeout_after_acceptance_recovers_same_client_id_without_post(ledger):
    intent=prepare(ledger)
    ledger.mark_uncertain(intent['client_id'])
    broker=FakeBroker(order(intent,filled=10,avg='100',status='filled',legs=[leg(),leg(name='stop')]),
        positions=[dict(symbol='AAPL',qty='10')])
    result=refresh_execution(ledger,broker=broker)
    assert not result['blocked']
    assert broker.reads==[('client',intent['client_id']),('nested','entry-broker-1')]
    assert result['inventory'][0]['open_qty']=='10'


def test_read_timeout_retains_inventory_and_blocks_new_entries(ledger):
    intent=prepare(ledger)
    ledger.observe_tree(intent['client_id'],order(intent,filled=10,avg='100',status='filled'))
    result=refresh_execution(ledger,broker=FakeBroker(failed=True,positions=[dict(symbol='AAPL',qty=10)]))
    assert result['blocked']
    assert result['inventory'][0]['open_qty']=='10'
    assert 'sensitive' not in str(result)


def test_external_nvda_stays_external_and_does_not_create_lot(ledger):
    ownership=verify_positions(ledger.snapshot(),[dict(symbol='NVDA',qty='5')])
    assert ownership['external_positions']==[dict(symbol='NVDA',qty='5',ownership='external')]
    assert ledger.snapshot()['inventory']==[]


@pytest.mark.parametrize('qty',['9','11','0','-10'])
def test_same_symbol_manual_or_missing_quantity_blocks_ownership(ledger,qty):
    intent=prepare(ledger)
    ledger.observe_tree(intent['client_id'],order(intent,filled=10,avg='100',status='filled'))
    result: dict[str, Any] = verify_positions(ledger.snapshot(),[dict(symbol='AAPL',qty=qty)])
    assert result['blocked']
    assert result['position_mismatches'][0]['owned_qty']=='10'


def test_readonly_dashboard_does_not_create_missing_ledger(tmp_path):
    path=tmp_path/'missing.sqlite3'
    with pytest.raises(LedgerError):ExecutionLedger(path,readonly=True)
    assert not path.exists()


def test_missing_initialized_ledger_not_automatically_recreated(tmp_path):
    with pytest.raises(LedgerError):initialize_ledger({'execution_schema_version':1},tmp_path/'state.json')
    assert not (tmp_path/'execution.sqlite3').exists()


def test_stage1_intent_imported_but_legacy_ownership_requires_review(tmp_path):
    state=dict(submitted_symbols=['AAPL'],last_order_intent=dict(symbol='AAPL',qty=10,
        reference_price=100,bar_start=TIME,client_order_id='orbit-legacy'))
    ledger=initialize_ledger(state,tmp_path/'state.json')
    assert ledger.roots()[0]['client_id']=='orbit-legacy'
    assert state['legacy_review_required']
    assert ledger.snapshot()['inventory']==[]


def test_quantity_mismatch_is_not_presented_as_verified_managed_position(ledger):
    intent=prepare(ledger)
    broker=FakeBroker(order(intent,filled=10,avg='100',status='filled'),positions=[dict(symbol='AAPL',qty=11)])
    result=refresh_execution(ledger,broker=broker)
    state={}
    apply_execution_state(state,result)
    assert state['execution_uncertain']
    assert not state['managed_positions'][0]['broker_quantity_verified']


def test_account_change_quarantines_before_order_reads(ledger):
    prepare(ledger)
    ledger.bind_account('first-paper-account')
    broker=FakeBroker()
    result=refresh_execution(ledger,broker=broker)
    assert result['blocked']
    assert broker.reads==[]
    assert ledger.snapshot()['faults'][0]['code']=='account_mismatch'


def test_same_account_binding_idempotent_and_durable(ledger):
    ledger.bind_account('first-paper-account')
    reopened=ExecutionLedger(ledger.path)
    reopened.bind_account('first-paper-account')
    assert reopened.snapshot()['account_bound']
    assert reopened.snapshot()['faults']==[]


def test_null_account_id_refused_before_order_reads(ledger):
    prepare(ledger)
    broker=FakeBroker()
    broker.get_account=lambda:{'id':None}
    result=refresh_execution(ledger,broker=broker)
    assert result['blocked']
    assert broker.reads==[]
    assert not ledger.snapshot()['account_bound']


def test_known_inventory_without_exit_protection_blocks_new_entries(ledger):
    intent=prepare(ledger)
    broker=FakeBroker(order(intent,filled=10,avg='100',status='filled'),positions=[dict(symbol='AAPL',qty=10)])
    result=refresh_execution(ledger,broker=broker)
    assert result['blocked']
    assert result['protection_unverified_symbols']==['AAPL']


def test_insufficient_stop_coverage_cannot_be_marked_reconciled(ledger):
    intent=prepare(ledger)
    broker=FakeBroker(order(intent,filled=10,avg='100',status='filled',legs=[leg(),leg(name='stop',qty='5')]),
        positions=[dict(symbol='AAPL',qty=10)])
    result=refresh_execution(ledger,broker=broker)
    assert result['blocked']


def test_two_take_legs_do_not_count_as_stop_protection(ledger):
    intent=prepare(ledger)
    wrong=leg(name='stop');wrong['type']='limit'
    broker=FakeBroker(order(intent,filled=10,avg='100',status='filled',legs=[leg(),wrong]),
        positions=[dict(symbol='AAPL',qty=10)])
    assert refresh_execution(ledger,broker=broker)['blocked']


def test_exit_before_entry_is_quarantined(ledger):
    intent=prepare(ledger)
    wrong=leg(filled=10,avg='110',status='filled')
    wrong['filled_at']='2026-09-15T15:00:00Z'
    with pytest.raises(LedgerError):ledger.observe_tree(intent['client_id'],order(intent,
        filled=10,avg='100',status='filled',legs=[wrong]))
    assert ledger.snapshot()['fill_checkpoints']==0


def test_terminal_rejection_resets_signal_but_keeps_durable_intent(ledger):
    intent=prepare(ledger)
    ledger.observe_tree(intent['client_id'],order(intent,status='rejected'))
    state: dict[str, Any] = dict(prev_sig={'AAPL':1},execution_uncertain=True)
    apply_execution_state(state,ledger.snapshot())
    assert state['prev_sig']['AAPL']==0
    assert not ledger.prepare_entry('AAPL',10,100,TIME)[1]


def test_daily_cap_recovers_prepared_intent_count_after_missing_state_save(ledger):
    intent=prepare(ledger)
    state: dict[str, Any] = dict(last_reset_date=intent['created_at'][:10],daily_order_count=0)
    apply_execution_state(state,ledger.snapshot())
    assert state['daily_order_count']==1
