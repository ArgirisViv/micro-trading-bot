"""Explicit opt-in exit-only process. No entry orders or historical-feed imports."""
import json
import os
import time
from pathlib import Path
from core import alpaca_trade
from core.execution_ledger import ExecutionLedger
from core.execution_runtime import ledger_path
from core.execution_safety import exclusive_runtime
from core.crypto_exit_supervisor import supervision_cycle


def main():
    if os.getenv('ENABLE_CRYPTO_EXIT_SUPERVISOR','false').lower()!='true':
        raise SystemExit('Exit supervisor disabled; controlled paper validation required first')
    state_path=Path(os.getenv('STATE_FILE','/app/runtime/state.json'))
    path=ledger_path(state_path)
    if not path.is_file():raise SystemExit('Existing owned execution ledger required; no automatic adoption')
    status_path=path.with_name('crypto_exit_status.json')
    with exclusive_runtime(str(path)+'.crypto-exit.lock'):
        ledger=ExecutionLedger(path)
        while True:
            result=supervision_cycle(ledger,alpaca_trade)
            tmp=status_path.with_suffix('.tmp')
            with tmp.open('w',encoding='utf-8') as handle:
                json.dump(result,handle);handle.flush();os.fsync(handle.fileno())
            os.replace(tmp,status_path)
            time.sleep(5)


if __name__=='__main__':main()
