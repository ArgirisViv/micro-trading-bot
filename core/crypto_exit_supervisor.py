"""Ledger-owned long-only exits. No historical feed, indicators or entry controls."""
from datetime import datetime,timezone
from decimal import Decimal,ROUND_DOWN
from typing import Any
from core.execution_ledger import ExecutionLedger,LedgerError,amount,utc_timestamp
from core.execution_runtime import refresh_execution


def evaluate_exit(ledger,lot,quote,now):
    bid,ask=amount(quote['bid'],positive=True),amount(quote['ask'],positive=True)
    timestamp=datetime.fromisoformat(utc_timestamp(quote['timestamp']))
    age=(now-timestamp).total_seconds()
    if not 0<=age<=10 or ask<bid:raise LedgerError('Crypto quote stale, future or crossed')
    entry=amount(lot['open_cost'])/amount(lot['open_qty'])
    policy,high=ledger.crypto_policy(lot['entry_id'],max(entry,bid))
    stop=entry*(1-amount(policy['stop_pct']))
    trailing=high*(1-amount(policy['trail_pct']))
    reason=None;qty=amount(lot['open_qty'])
    if bid<=stop:reason='fixed_stop'
    elif bid<=trailing:reason='trailing_stop'
    elif bid>=entry*(1+amount(policy['take_pct'])):reason='take_profit'
    elif bid>=entry*(1+amount(policy['partial_pct'])):
        prior=[row for row in ledger.software_exits() if row['parent_id']==lot['entry_id']]
        if not any(row['intent_key'].startswith('exit|partial_take|') for row in prior):
            reason='partial_take';qty=(qty*amount(policy['partial_ratio'])).quantize(Decimal('0.00000001'),rounding=ROUND_DOWN)
    return (reason,qty,bid) if reason and qty>0 else None


def supervision_cycle(ledger,broker,now=None):
    now=now or datetime.now(timezone.utc)
    snapshot=refresh_execution(ledger,broker=broker)
    result: dict[str, Any] = dict(
        checked_at=utc_timestamp(now),
        submitted=[],
        issues=[],
        mode='crypto_exit_only',
    )
    # Missing broker-side crypto brackets alone is NOT a reason to suppress a
    # required exit. All identity/order/inventory errors still fail closed.
    if (snapshot['faults'] or snapshot['unresolved_client_ids'] or snapshot.get('read_errors') or
        snapshot.get('positions_unavailable') or snapshot.get('position_mismatches')):
        result['issues'].append('Execution/account/ownership unresolved');return result
    roots={row['client_id']:row for row in snapshot['orders'] if row['parent_id'] is None}
    for lot in snapshot['inventory']:
        parent=roots[lot['entry_id']]
        if parent['asset_class']!='crypto' or amount(lot['open_qty'])<=0:continue
        if parent['status'] not in {'filled','canceled','expired'}:continue
        if any(row['parent_id']==lot['entry_id'] and row['status'] not in {'filled','canceled','expired','rejected'}
               for row in snapshot['orders']):continue
        try:
            action=evaluate_exit(ledger,lot,broker.get_crypto_quote(lot['symbol']),now)
            if not action:continue
            reason,qty,bid=action
            intent=ledger.prepare_exit(lot['entry_id'],qty,bid,reason)
            try:
                ack=broker.submit_crypto_exit(lot['symbol'],str(qty),intent['client_id'])
            except Exception:
                ledger.mark_uncertain(intent['client_id'])
                result['issues'].append('Exit submission unconfirmed; do not resubmit')
                break
            if ack is None:
                ledger.mark_uncertain(intent['client_id']);result['issues'].append('Exit acknowledgment unavailable');break
            ledger.observe_order(intent['client_id'],ack)
            result['submitted'].append(dict(symbol=lot['symbol'],reason=reason,client_id=intent['client_id']))
        except Exception:
            result['issues'].append('Crypto exit blocked or quote unavailable')
    return result
