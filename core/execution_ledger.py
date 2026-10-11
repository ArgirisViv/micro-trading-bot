"""Durable long-only execution journal; cumulative broker fills, not estimates.

Amounts are Decimal text. A fill checkpoint is a delta between broker snapshots,
NOT an exchange execution ID. Corrections/replacements quarantine, never guess.
"""
from __future__ import annotations

import re
import sqlite3
import uuid
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 2
TERMINAL = {'filled', 'canceled', 'expired', 'rejected'}
ACTIVE = {'new', 'accepted', 'pending_new', 'accepted_for_bidding',
          'partially_filled', 'pending_cancel', 'pending_replace', 'held', 'stopped'}


class LedgerError(RuntimeError): pass


def amount(value, *, positive=False):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise LedgerError('Invalid numeric broker field') from exc
    if not result.is_finite() or result < 0 or (positive and result <= 0):
        raise LedgerError('Invalid numeric broker field')
    return result


def utc_timestamp(value=None):
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    try:
        timestamp = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError as exc:
        raise LedgerError('Invalid broker timestamp') from exc
    if timestamp.tzinfo is None:
        raise LedgerError('Broker timestamps must be timezone-aware')
    return timestamp.astimezone(timezone.utc).isoformat()


def field(obj, name, default=None):
    return obj.get(name, default) if isinstance(obj, dict) else getattr(obj, name, default)


def normalized_symbol(symbol):
    symbol = str(symbol)
    if not re.fullmatch(r'[A-Z0-9./-]{1,24}', symbol):
        raise LedgerError('Invalid instrument symbol')
    return symbol.replace('/', '')


class ExecutionLedger:
    def __init__(self, path, *, readonly=False):
        self.path = Path(path)
        self.readonly = readonly
        if readonly:
            if not self.path.is_file(): raise LedgerError('Execution ledger is unavailable')
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0,1,SCHEMA_VERSION): raise LedgerError('Unsupported ledger schema')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS orders (
                    client_id TEXT PRIMARY KEY, intent_key TEXT UNIQUE NOT NULL,
                    symbol TEXT NOT NULL, side TEXT NOT NULL CHECK(side IN ('buy','sell')),
                    parent_id TEXT REFERENCES orders(client_id), broker_id TEXT UNIQUE,
                    requested_qty TEXT NOT NULL, reference_price TEXT NOT NULL,
                    status TEXT NOT NULL, filled_qty TEXT NOT NULL DEFAULT '0',
                    filled_notional TEXT NOT NULL DEFAULT '0', avg_price TEXT,
                    created_at TEXT NOT NULL, observed_at TEXT, broker_time TEXT
                    , leg_type TEXT
                );
                CREATE TABLE IF NOT EXISTS inventory (
                    entry_id TEXT PRIMARY KEY REFERENCES orders(client_id),
                    symbol TEXT NOT NULL, acquired_qty TEXT NOT NULL DEFAULT '0',
                    open_qty TEXT NOT NULL DEFAULT '0', open_cost TEXT NOT NULL DEFAULT '0',
                    realized_gross TEXT NOT NULL DEFAULT '0', sold_qty TEXT NOT NULL DEFAULT '0',
                    entry_time TEXT, exit_time TEXT
                );
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id INTEGER PRIMARY KEY, client_id TEXT NOT NULL REFERENCES orders(client_id),
                    cumulative_qty TEXT NOT NULL, delta_qty TEXT NOT NULL,
                    delta_notional TEXT NOT NULL, realized_gross TEXT,
                    broker_time TEXT NOT NULL, observed_at TEXT NOT NULL,
                    UNIQUE(client_id,cumulative_qty)
                );
                CREATE TABLE IF NOT EXISTS faults (
                    code TEXT PRIMARY KEY, detail TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY, client_id TEXT, kind TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS crypto_policies (
                    entry_id TEXT PRIMARY KEY REFERENCES orders(client_id),policy TEXT NOT NULL,
                    high_water TEXT NOT NULL DEFAULT '0'
                );
            ''')
            db.execute('BEGIN IMMEDIATE')
            try:
                if 'asset_class' not in [row['name'] for row in db.execute('PRAGMA table_info(orders)')]:
                    db.execute("ALTER TABLE orders ADD COLUMN asset_class TEXT NOT NULL DEFAULT 'stocks'")
                db.execute('PRAGMA user_version=2');db.commit()
            except BaseException:db.rollback();raise

    @contextmanager
    def connection(self):
        if self.readonly:
            db = sqlite3.connect(self.path.resolve().as_uri() + '?mode=ro', uri=True, timeout=5)
        else:
            db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
            db.execute('PRAGMA synchronous=FULL')
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def transaction(self):
        if self.readonly: raise LedgerError('Read-only execution ledger')
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def prepare_entry(self, symbol, qty, reference_price, bar_start, *, client_id=None,asset_class='stocks',exit_policy=None):
        """Commit intent before POST. Returns (record, created); existing = NO POST."""
        normalized_symbol(symbol)
        if asset_class not in {'stocks','crypto'}:raise LedgerError('Invalid asset class')
        crypto_policy = exit_policy if isinstance(exit_policy, dict) else None
        if asset_class=='crypto':
            if crypto_policy is None or set(crypto_policy)!={'stop_pct','take_pct','trail_pct','partial_pct','partial_ratio'}:
                raise LedgerError('Persisted crypto exit policy required')
            if any(not 0<amount(value,positive=True)<1 for value in crypto_policy.values()):raise LedgerError('Invalid crypto exit policy')
            if amount(crypto_policy['partial_pct'])>=amount(crypto_policy['take_pct']):raise LedgerError('Invalid partial threshold')
        qty, reference_price = amount(qty, positive=True), amount(reference_price, positive=True)
        timestamp = utc_timestamp(bar_start)
        key = f'entry|{symbol}|{timestamp}'
        client_id = client_id or 'orbit-' + uuid.uuid4().hex
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,48}', client_id): raise LedgerError('Invalid client ID')
        with self.transaction() as db:
            existing = db.execute('SELECT * FROM orders WHERE intent_key=?', (key,)).fetchone()
            if existing:
                if (existing['symbol'], amount(existing['requested_qty']), amount(existing['reference_price'])) != (symbol,qty,reference_price):
                    raise LedgerError('Intent key already has different parameters')
                if existing['asset_class']!=asset_class:raise LedgerError('Intent asset class changed')
                if asset_class=='crypto':
                    pinned=db.execute('SELECT policy FROM crypto_policies WHERE entry_id=?',(existing['client_id'],)).fetchone()
                    if pinned is None or crypto_policy is None or any(
                        amount(json.loads(pinned['policy'])[key]) != amount(value)
                        for key, value in crypto_policy.items()
                    ):
                        raise LedgerError('Persisted crypto policy changed')
                return dict(existing), False
            db.execute('''INSERT INTO orders(client_id,intent_key,symbol,side,requested_qty,
                reference_price,status,created_at) VALUES(?,?,?,'buy',?,?,'prepared',?)''',
                (client_id,key,symbol,str(qty),str(reference_price),utc_timestamp()))
            db.execute('UPDATE orders SET asset_class=? WHERE client_id=?',(asset_class,client_id))
            if asset_class=='crypto':
                if crypto_policy is None:
                    raise LedgerError('Persisted crypto exit policy required')
                db.execute('INSERT INTO crypto_policies(entry_id,policy) VALUES(?,?)',
                    (client_id,json.dumps({key:str(value) for key,value in crypto_policy.items()},sort_keys=True)))
            db.execute('INSERT INTO events(client_id,kind,created_at) VALUES(?,?,?)',
                (client_id,'intent_prepared',utc_timestamp()))
            return dict(db.execute('SELECT * FROM orders WHERE client_id=?',(client_id,)).fetchone()), True

    def prepare_exit(self,entry_id,qty,reference_price,reason):
        if reason not in {'fixed_stop','trailing_stop','take_profit','partial_take'}:raise LedgerError('Invalid exit reason')
        qty,reference_price=amount(qty,positive=True),amount(reference_price,positive=True)
        with self.transaction() as db:
            parent=db.execute('SELECT * FROM orders WHERE client_id=?',(entry_id,)).fetchone()
            lot=db.execute('SELECT * FROM inventory WHERE entry_id=?',(entry_id,)).fetchone()
            if not parent or parent['asset_class']!='crypto' or parent['status'] not in {'filled','canceled','expired'}:
                raise LedgerError('Crypto entry not settled')
            if not lot or qty>amount(lot['open_qty']):raise LedgerError('Exit exceeds owned crypto')
            exits=list(db.execute('SELECT * FROM orders WHERE parent_id=?',(entry_id,)))
            if any(row['status'] not in TERMINAL for row in exits):raise LedgerError('Exit already pending')
            if reason=='partial_take' and any(row['intent_key'].startswith('exit|partial_take|') for row in exits):
                raise LedgerError('Partial take already attempted')
            client_id='orbit-'+uuid.uuid4().hex
            key=f'exit|{reason}|{entry_id}|{len(exits)}'
            db.execute('''INSERT INTO orders(client_id,intent_key,symbol,side,parent_id,requested_qty,
                reference_price,status,created_at,asset_class) VALUES(?,?,?,'sell',?,?,?,'prepared',?,'crypto')''',
                (client_id,key,parent['symbol'],entry_id,str(qty),str(reference_price),utc_timestamp()))
            return dict(db.execute('SELECT * FROM orders WHERE client_id=?',(client_id,)).fetchone())

    def software_exits(self):
        with self.connection() as db:
            return [dict(row) for row in db.execute("SELECT * FROM orders WHERE intent_key LIKE 'exit|%' ORDER BY created_at")]

    def crypto_policy(self,entry_id,bid):
        with self.transaction() as db:
            row=db.execute('SELECT * FROM crypto_policies WHERE entry_id=?',(entry_id,)).fetchone()
            if not row:raise LedgerError('Crypto exit policy unavailable')
            high=max(amount(row['high_water']),amount(bid,positive=True))
            db.execute('UPDATE crypto_policies SET high_water=? WHERE entry_id=?',(str(high),entry_id))
            return json.loads(row['policy']),high

    def observe_order(self,client_id,order):
        try:
            with self.transaction() as db:self._observe(db,client_id,order)
        except (LedgerError,sqlite3.IntegrityError) as exc:
            self.fault('order:'+client_id,str(exc) if isinstance(exc,LedgerError) else 'Order identifier conflict')
            raise LedgerError('Order snapshot quarantined') from exc

    def mark_uncertain(self, client_id):
        with self.transaction() as db:
            db.execute("UPDATE orders SET status='uncertain' WHERE client_id=? AND status='prepared'",(client_id,))
            db.execute('INSERT INTO events(client_id,kind,created_at) VALUES(?,?,?)',
                (client_id,'submission_unconfirmed',utc_timestamp()))

    def fault(self, code, detail):
        # Only controlled application messages, never raw provider exception/URL.
        with self.transaction() as db:
            db.execute('INSERT OR IGNORE INTO faults VALUES(?,?,?)',(code,detail,utc_timestamp()))

    def bind_account(self, account_id):
        if not isinstance(account_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',account_id):
            raise LedgerError('Broker account identity unavailable')
        mismatch=False
        with self.transaction() as db:
            row=db.execute("SELECT value FROM metadata WHERE key='paper_account_id'").fetchone()
            if row and row['value'] != account_id:
                mismatch=True
            elif not row:
                db.execute("INSERT INTO metadata VALUES('paper_account_id',?)",(account_id,))
        if mismatch:
            self.fault('account_mismatch','Configured paper account differs from the ledger owner')
            raise LedgerError('Paper account mismatch; reconciliation refused')

    def observe_tree(self, client_id, root):
        """Parent fill and all nested child fills commit atomically or not at all."""
        try:
            with self.transaction() as db:
                self._observe(db,client_id,root)
                parent = db.execute('SELECT * FROM orders WHERE client_id=?',(client_id,)).fetchone()
                if parent['side'] != 'buy' or parent['parent_id'] is not None:
                    raise LedgerError('Nested root must be an owned entry')
                legs = field(root,'legs',None) or []
                if not isinstance(legs,(list,tuple)): raise LedgerError('Invalid nested bracket legs')
                for leg in legs:
                    broker_id = str(field(leg,'id',''))
                    child_id = str(field(leg,'client_order_id',''))
                    if not broker_id or not child_id: raise LedgerError('Bracket leg identifiers missing')
                    leg_type=field(leg,'type')
                    if leg_type not in {'limit','stop','stop_limit'}:
                        raise LedgerError('Unsupported bracket leg type')
                    if field(leg,'side') != 'sell' or normalized_symbol(field(leg,'symbol','')) != normalized_symbol(parent['symbol']):
                        raise LedgerError('Bracket leg ownership mismatch')
                    existing = db.execute('SELECT * FROM orders WHERE client_id=?',(child_id,)).fetchone()
                    if existing and existing['parent_id'] != client_id: raise LedgerError('Bracket leg parent conflict')
                    if existing and existing['leg_type'] and existing['leg_type'] != leg_type:
                        raise LedgerError('Bracket leg type changed')
                    if not existing:
                        db.execute('''INSERT INTO orders(client_id,intent_key,symbol,side,parent_id,
                            requested_qty,reference_price,status,created_at)
                            VALUES(?,?,?,'sell',?,?,?,'prepared',?)''',
                            (child_id,'leg|'+broker_id,parent['symbol'],client_id,
                             str(amount(field(leg,'qty'),positive=True)),parent['reference_price'],utc_timestamp()))
                    self._observe(db,child_id,leg)
                    db.execute('UPDATE orders SET leg_type=? WHERE client_id=?',(leg_type,child_id))
        except (LedgerError, sqlite3.IntegrityError) as exc:
            self.fault('order:'+client_id, str(exc) if isinstance(exc,LedgerError) else 'Broker identifier conflict')
            raise LedgerError('Broker snapshot quarantined; entries blocked') from exc

    def _observe(self, db, client_id, snapshot):
        row = db.execute('SELECT * FROM orders WHERE client_id=?',(client_id,)).fetchone()
        if row is None: raise LedgerError('Order has no local intent')
        if str(field(snapshot,'client_order_id','')) != client_id:
            raise LedgerError('Client order identifier mismatch')
        if normalized_symbol(field(snapshot,'symbol','')) != normalized_symbol(row['symbol']) or field(snapshot,'side') != row['side']:
            raise LedgerError('Order instrument/side mismatch')
        broker_id = str(field(snapshot,'id',''))
        if not broker_id or (row['broker_id'] and row['broker_id'] != broker_id):
            raise LedgerError('Broker order identifier mismatch')
        if field(snapshot,'replaced_by') or field(snapshot,'replaces'):
            raise LedgerError('Replaced orders require explicit recovery')
        status = str(field(snapshot,'status',''))
        if status not in ACTIVE | TERMINAL:
            raise LedgerError('Unsupported broker order status')
        if row['status'] in TERMINAL and row['status'] != status:
            raise LedgerError('Terminal order status changed')
        requested = amount(field(snapshot,'qty'),positive=True)
        if row['side'] == 'buy' and requested != amount(row['requested_qty']):
            raise LedgerError('Broker entry quantity changed')
        cumulative = amount(field(snapshot,'filled_qty'))
        previous = amount(row['filled_qty'])
        if cumulative > requested or cumulative < previous:
            raise LedgerError('Invalid/regressing cumulative filled quantity')
        if status == 'filled' and cumulative != requested:
            raise LedgerError('Filled status has incomplete quantity')
        if status == 'partially_filled' and not 0 < cumulative < requested:
            raise LedgerError('Partial status has invalid quantity')
        if status == 'rejected' and cumulative != 0:
            raise LedgerError('Rejected order has a fill')
        avg = amount(field(snapshot,'filled_avg_price'),positive=True) if cumulative > 0 else Decimal(0)
        notional = cumulative * avg
        old_notional = amount(row['filled_notional'])
        delta, delta_notional = cumulative-previous, notional-old_notional
        if delta == 0 and delta_notional != 0:
            raise LedgerError('Fill price correction requires explicit recovery')
        if delta > 0 and delta_notional <= 0:
            raise LedgerError('Invalid incremental fill notional')
        observed = utc_timestamp()
        broker_time = utc_timestamp(field(snapshot,'filled_at') or field(snapshot,'updated_at')) if delta > 0 else None
        if delta > 0 and not (field(snapshot,'filled_at') or field(snapshot,'updated_at')):
            raise LedgerError('Fill snapshot timestamp missing')
        realized = None
        if delta > 0:
            if row['side'] == 'buy':
                db.execute('INSERT OR IGNORE INTO inventory(entry_id,symbol) VALUES(?,?)',(client_id,row['symbol']))
                lot = db.execute('SELECT * FROM inventory WHERE entry_id=?',(client_id,)).fetchone()
                if amount(lot['sold_qty']) > 0: raise LedgerError('Late entry fill after exit requires recovery')
                db.execute('''UPDATE inventory SET acquired_qty=?,open_qty=?,open_cost=?,
                    entry_time=COALESCE(entry_time,?) WHERE entry_id=?''',
                    (str(amount(lot['acquired_qty'])+delta),str(amount(lot['open_qty'])+delta),
                     str(amount(lot['open_cost'])+delta_notional),broker_time,client_id))
            else:
                lot = db.execute('SELECT * FROM inventory WHERE entry_id=?',(row['parent_id'],)).fetchone()
                parent = db.execute('SELECT status FROM orders WHERE client_id=?',(row['parent_id'],)).fetchone()
                if lot is None or parent['status'] not in {'filled','canceled','expired'}:
                    raise LedgerError('Exit fill without fully filled owned parent')
                if broker_time is None or lot['entry_time'] is None:
                    raise LedgerError('Exit or entry timestamp missing')
                if datetime.fromisoformat(broker_time) < datetime.fromisoformat(lot['entry_time']):
                    raise LedgerError('Exit timestamp precedes the entry')
                open_qty, open_cost = amount(lot['open_qty']), amount(lot['open_cost'])
                if delta > open_qty: raise LedgerError('Exit quantity exceeds owned inventory')
                basis = open_cost if delta == open_qty else open_cost*delta/open_qty
                realized = delta_notional-basis
                db.execute('''UPDATE inventory SET open_qty=?,open_cost=?,realized_gross=?,
                    sold_qty=?,exit_time=? WHERE entry_id=?''',
                    (str(open_qty-delta),str(open_cost-basis),
                     str(Decimal(lot['realized_gross'])+realized),str(amount(lot['sold_qty'])+delta),
                     broker_time,row['parent_id']))
            db.execute('''INSERT INTO checkpoints(client_id,cumulative_qty,delta_qty,
                delta_notional,realized_gross,broker_time,observed_at) VALUES(?,?,?,?,?,?,?)''',
                (client_id,str(cumulative),str(delta),str(delta_notional),
                 str(realized) if realized is not None else None,broker_time,observed))
        db.execute('''UPDATE orders SET broker_id=?,requested_qty=?,status=?,filled_qty=?,
            filled_notional=?,avg_price=?,observed_at=?,broker_time=COALESCE(?,broker_time)
            WHERE client_id=?''',(broker_id,str(requested),status,str(cumulative),str(notional),
                str(avg) if cumulative else None,observed,broker_time,client_id))
        if row['status'] != status:
            db.execute('INSERT INTO events(client_id,kind,created_at) VALUES(?,?,?)',
                (client_id,'broker_status:'+status,observed))

    def roots(self):
        with self.connection() as db:
            return [dict(row) for row in db.execute('SELECT * FROM orders WHERE parent_id IS NULL ORDER BY created_at,client_id')]

    def snapshot(self) -> dict[str, Any]:
        with self.connection() as db:
            if db.execute('PRAGMA user_version').fetchone()[0] != SCHEMA_VERSION:
                raise LedgerError('Unsupported ledger schema')
            # One read transaction: dashboard must not mix states across commits.
            db.execute('BEGIN')
            orders = [dict(row) for row in db.execute('SELECT * FROM orders ORDER BY created_at,client_id')]
            inventory = [dict(row) for row in db.execute('SELECT * FROM inventory ORDER BY entry_id')]
            faults = [dict(row) for row in db.execute('SELECT * FROM faults ORDER BY created_at')]
            checkpoints = db.execute('SELECT COUNT(*) FROM checkpoints').fetchone()[0]
            account_bound = bool(db.execute("SELECT value FROM metadata WHERE key='paper_account_id'").fetchone())
        pending = [row for row in orders if row['parent_id'] is None and row['status'] not in TERMINAL]
        uncertain = [row['client_id'] for row in orders if row['status'] in {'prepared','uncertain'}]
        reserve = sum(((amount(row['requested_qty'])-amount(row['filled_qty'])) *
            amount(row['reference_price']) for row in pending), Decimal(0))
        closed = [row for row in inventory if amount(row['acquired_qty']) > 0 and amount(row['open_qty']) == 0]
        unprotected=[]
        for lot in inventory:
            if amount(lot['open_qty']) <= 0: continue
            parent=next(row for row in orders if row['client_id']==lot['entry_id'])
            if parent['asset_class']=='crypto':
                # Software supervision is NOT broker-side bracket protection.
                unprotected.append(lot['symbol'])
                continue
            legs=[row for row in orders if row['parent_id']==lot['entry_id'] and row['status'] in ACTIVE]
            covered=[row for row in legs if amount(row['requested_qty'])-amount(row['filled_qty']) >= amount(lot['open_qty'])]
            stop=any(row['leg_type'] in {'stop','stop_limit'} for row in covered)
            take=any(row['leg_type']=='limit' for row in covered)
            if parent['status'] != 'filled' or not stop or not take:
                unprotected.append(lot['symbol'])
        return dict(schema_version=SCHEMA_VERSION, account_bound=account_bound, orders=orders, inventory=inventory,
            faults=faults, fill_checkpoints=checkpoints, unresolved_client_ids=uncertain,
            pending_entries=len(pending), reserved_reference_notional=str(reserve),
            closed_trades=closed, blocked=bool(faults or uncertain),
            protection_unverified_symbols=unprotected,
            accounting='broker_cumulative_fill_deltas; gross P&L; fees not reconciled')


def reconcile(ledger, broker):
    """GET only. A 404/timeout never authorizes another POST for an existing intent."""
    errors = []
    for row in ledger.roots():
        try:
            order = broker.get_order(row['broker_id']) if row['broker_id'] else broker.get_order_by_client_order_id(row['client_id'])
            if order is None:
                errors.append('order_not_found:'+row['client_id'])
                continue
            if not row['broker_id']:
                # The legacy SDK client-ID endpoint has no nested parameter.
                order = broker.get_order(str(field(order,'id','')))
                if order is None:
                    errors.append('nested_order_unavailable:'+row['client_id'])
                    continue
            ledger.observe_tree(row['client_id'],order)
        except Exception:
            errors.append('order_reconciliation_failed:'+row['client_id'])
    for row in ledger.software_exits():
        try:
            order=broker.get_order(row['broker_id']) if row['broker_id'] else broker.get_order_by_client_order_id(row['client_id'])
            if order is None:errors.append('exit_not_found:'+row['client_id']);continue
            ledger.observe_order(row['client_id'],order)
        except Exception:errors.append('exit_reconciliation_failed:'+row['client_id'])
    result = ledger.snapshot()
    result['read_errors'] = errors
    result['blocked'] = result['blocked'] or bool(errors)
    return result


def verify_positions(snapshot, positions):
    """No adoption/closing. Same-symbol manual changes cannot be safely segregated."""
    expected, actual, external, mismatches = {}, {}, [], []
    for lot in snapshot['inventory']:
        symbol = normalized_symbol(lot['symbol'])
        expected[symbol] = expected.get(symbol,Decimal(0)) + amount(lot['open_qty'])
    for position in positions:
        symbol = normalized_symbol(field(position,'symbol',''))
        if symbol in actual: raise LedgerError('Duplicate broker position symbol')
        qty = Decimal(str(field(position,'qty')))
        if not qty.is_finite(): raise LedgerError('Invalid broker position quantity')
        actual[symbol] = qty
    for symbol in set(expected) | set(actual):
        owned, broker_qty = expected.get(symbol,Decimal(0)),actual.get(symbol,Decimal(0))
        if owned != broker_qty:
            if owned == 0 and symbol not in expected:
                external.append(dict(symbol=symbol,qty=str(broker_qty),ownership='external'))
            else:
                mismatches.append(dict(symbol=symbol,owned_qty=str(owned),broker_qty=str(broker_qty)))
    return dict(external_positions=external,position_mismatches=mismatches,
                blocked=bool(mismatches))
