"""Runtime integration for the ledger; no network on import."""
import os
from pathlib import Path
from typing import Any
from core import alpaca_trade
from core.execution_ledger import ExecutionLedger, LedgerError, reconcile, verify_positions, amount, field, utc_timestamp, TERMINAL


def ledger_path(state_path):
    return Path(os.getenv('EXECUTION_DB',str(Path(state_path).with_name('execution.sqlite3'))))


def initialize_ledger(state: dict[str, Any], state_path: str | Path) -> ExecutionLedger:
    path = ledger_path(state_path)
    if state.get('execution_schema_version') and not path.is_file():
        raise LedgerError('Previously initialized ledger is missing; automatic recreation refused')
    ledger = ExecutionLedger(path)
    # Import only a known stage-1 intent, never infer ownership from entry_price.
    intent = state.get('last_order_intent')
    if intent and not state.get('execution_schema_version'):
        ledger.prepare_entry(intent['symbol'],intent['qty'],intent['reference_price'],
            intent['bar_start'],client_id=intent['client_order_id'])
    if not state.get('execution_schema_version') and state.get('submitted_symbols'):
        state['legacy_review_required'] = True
    state['execution_schema_version'] = 2
    return ledger


def refresh_execution(ledger: ExecutionLedger, *, broker: Any = alpaca_trade) -> dict[str, Any]:
    try:
        account_id=field(broker.get_account(),'id')
        if account_id is None:raise LedgerError('Paper account ID missing')
        ledger.bind_account(str(account_id))
    except Exception:
        result=ledger.snapshot()
        result.update(read_errors=['paper_account_identity_unavailable_or_mismatch'],
            position_mismatches=[],external_positions=[],positions_unavailable=True,blocked=True)
        return result
    result = reconcile(ledger,broker)
    try:
        positions = broker.get_positions()
        if positions is None: raise LedgerError('Positions unavailable')
        ownership = verify_positions(result,positions)
        result.update(ownership)
        result['blocked'] = bool(result['faults'] or result['unresolved_client_ids'] or
            result['read_errors'] or ownership['blocked'] or result['protection_unverified_symbols'])
    except Exception:
        result.update(position_mismatches=[],external_positions=[],positions_unavailable=True,blocked=True)
    return result


def apply_execution_state(state: dict[str, Any], snapshot: dict[str, Any]) -> None:
    state['execution'] = snapshot
    state['execution_reconciled_at'] = utc_timestamp()
    # Never clear a stage-1 lock lacking any persisted recoverable intent.
    orphan_lock = state.get('execution_uncertain') and not snapshot['orders']
    state['execution_uncertain'] = bool(snapshot['blocked'] or orphan_lock or state.get('legacy_review_required'))
    state['external_positions'] = {row['symbol']:row for row in snapshot.get('external_positions',[])}
    state['managed_positions'] = []
    today=state.get('last_reset_date')
    roots=[row for row in snapshot['orders'] if row['parent_id'] is None]
    # Prepared intents count conservatively, even if a crash preceded the POST.
    # This restores the cap after an ack-before-state-save crash.
    if today:
        state['daily_order_count']=sum(row['created_at'][:10]==today for row in roots)
    latest={row['symbol']:row for row in roots}
    inventory={row['entry_id']:row for row in snapshot['inventory']}
    for symbol,row in latest.items():
        lot=inventory.get(row['client_id'])
        completed=(lot and amount(lot['open_qty']) == 0 and amount(lot['acquired_qty']) > 0)
        unfilled_terminal=row['status'] in TERMINAL and amount(row['filled_qty'])==0
        if completed or unfilled_terminal:
            state.setdefault('prev_sig',{})[symbol]=0
            state.setdefault('entry_price',{})[symbol]=None
            state.setdefault('trailing_max',{})[symbol]=None
    matching = not snapshot.get('position_mismatches') and not snapshot.get('positions_unavailable')
    for lot in snapshot['inventory']:
        if amount(lot['open_qty']) > 0:
            entry_price = amount(lot['open_cost']) / amount(lot['open_qty'])
            state['managed_positions'].append(dict(symbol=lot['symbol'],qty=lot['open_qty'],
                entry_price=str(entry_price),entry_id=lot['entry_id'],
                ownership='ledger',broker_quantity_verified=matching,
                accounting='broker-derived average cost'))
