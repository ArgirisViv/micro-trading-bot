import json
from datetime import datetime, timezone
from core.execution_ledger import ExecutionLedger
from core.execution_runtime import apply_execution_state, refresh_execution
from tests_safe.test_execution_ledger import prepare, order, leg, FakeBroker
from webapp import server


def completed_ledger():
    ledger=ExecutionLedger(server.STATE_JSON.with_name('execution.sqlite3'))
    intent=prepare(ledger)
    ack=order(intent,filled=10,avg='100',status='filled',legs=[
        leg(filled=10,avg='110',status='filled'),leg(name='stop',status='canceled')])
    result=refresh_execution(ledger,broker=FakeBroker(ack))
    state={'execution_schema_version':1,'last_heartbeat':datetime.now(timezone.utc).isoformat()}
    apply_execution_state(state,result)
    server.STATE_JSON.write_text(json.dumps(state))
    return ledger


def test_execution_endpoint_requires_login(client):
    client.post('/api/auth/logout',json={},headers={'X-Orbit-CSRF':client.get('/api/auth/status').json['csrf'],
        'X-Requested-With':'Orbit'})
    assert client.get('/api/execution').status_code==401


def test_missing_execution_endpoint_does_not_create_db(client):
    response=client.get('/api/execution')
    assert response.status_code==200
    assert not response.json['available']
    assert not server.STATE_JSON.with_name('execution.sqlite3').exists()


def test_execution_api_reports_owned_closed_gross_trade(client):
    completed_ledger()
    data=client.get('/api/execution').json
    assert data['available']
    assert len(data['closed_trades'])==1
    assert data['closed_trades'][0]['realized_gross']=='100'
    assert 'paper_account_id' not in str(data)


def test_overview_uses_ledger_dollars_not_partial_fill_events(client):
    completed_ledger()
    data=client.get('/api/overview').json['performance']['trades']
    assert data['source']=='paper-ledger-gross-usd'
    assert data['total_trades']==1
    assert data['win_rate_pct']==100
    assert data['average_win_pct'] is None


def test_staged_readiness_never_reports_ready(client,monkeypatch):
    monkeypatch.delenv('PAPER_ENTRIES_APPROVED',raising=False)
    completed_ledger()
    data=client.get('/api/readiness').json
    assert not data['ready_for_new_entries']
    assert 'entries_paused_or_stage_locked' in data['reasons']


def test_state_v2_does_not_promote_legacy_cached_position(client):
    server.STATE_JSON.write_text(json.dumps({'execution_schema_version':1,
        'entry_price':{'NVDA':100},'managed_positions':[]}))
    assert client.get('/api/state').json['positions']==[]


def test_execution_panel_present(client):
    assert b'id="execution-body"' in client.get('/').data
