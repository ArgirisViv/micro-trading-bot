"""Offline/read-only ledger summary. Does not create a DB or call a broker."""
import argparse
import json
from core.execution_ledger import ExecutionLedger


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',required=True,help='Path to execution.sqlite3')
    args=parser.parse_args()
    try:
        snapshot=ExecutionLedger(args.db,readonly=True).snapshot()
        output={key:snapshot[key] for key in ('schema_version','account_bound','blocked',
            'pending_entries','reserved_reference_notional','fill_checkpoints',
            'protection_unverified_symbols')}
        output.update(orders=len(snapshot['orders']),open_lots=sum(float(row['open_qty'])>0
            for row in snapshot['inventory']),completed_owned_trades=len(snapshot['closed_trades']),
            fault_codes=[row['code'] for row in snapshot['faults']],
            note='Ledger summary only; live broker readiness is NOT checked.')
        print(json.dumps(output,indent=2))
    except Exception:
        print('Execution ledger unavailable or invalid. No database was created or changed.')
        raise SystemExit(1)


if __name__=='__main__':main()
