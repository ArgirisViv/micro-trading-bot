import json
import pandas as pd
import pytest
from scripts.download_research_data import fetch, date_range, load_key, safe_url, save_dataset, DownloadError


NOW = pd.Timestamp('2026-09-16T12:00Z')


class Response:
    def __init__(self,body,code=200): self.body,self.status_code=body,code
    def json(self): return self.body


def row(stamp='2025-10-01T13:30Z'):
    return dict(t=int(pd.Timestamp(stamp).timestamp()*1000),o=100,h=101,l=99,c=100,v=50)


def test_header_auth_pagination_and_roundtrip(tmp_path):
    calls, waits = [], []
    responses = iter([Response(dict(status='OK',results=[row()],
        next_url='https://api.massive.com/v2/aggs?cursor=next&apiKey=SECRET')),
        Response(dict(status='DELAYED',results=[row('2025-10-01T13:35Z')]))])
    def get(url,**kwargs):
        calls.append((url,kwargs))
        return next(responses)
    frame,metadata = fetch('AAPL','2025-10-01','2025-10-02','5min','FAKE',now=NOW,get=get,wait=waits.append)
    assert waits == [12]
    assert 'SECRET' not in calls[1][0]
    assert calls[0][1]['headers'] == {'Authorization':'Bearer FAKE'}
    assert calls[0][1]['timeout'] == (5,20)
    assert calls[0][1]['allow_redirects'] is False
    assert calls[1][1]['params'] is None
    path = save_dataset(tmp_path/'new',frame,metadata)
    data = pd.read_csv(path)
    assert len(data) == 2
    assert set(data) == {'timestamp','open','high','low','close','volume'}
    manifest = json.loads((path.parent/'dataset.json').read_text())
    assert len(manifest['sha256']) == 64
    assert 'FAKE' not in json.dumps(manifest)
    with pytest.raises(FileExistsError): save_dataset(path.parent,frame,metadata)


@pytest.mark.parametrize('url',['https://evil.example/x','http://api.massive.com/x',
    'https://name:pass@api.massive.com/x','https://api.massive.com:443/x'])
def test_reject_pagination_destinations(url):
    with pytest.raises(DownloadError): safe_url(url,'api.massive.com')


@pytest.mark.parametrize('code,message',[(401,'ACCESS_DENIED'),(403,'ACCESS_DENIED'),
    (429,'RATE_LIMITED'),(500,'HTTP_FAILED')])
def test_errors_do_not_expose_provider_body_or_key(code,message):
    with pytest.raises(DownloadError,match=message) as exc:
        fetch('AAPL','2025-10-01','2025-10-02','5min','SECRET',now=NOW,
            get=lambda *a,**k:Response({'error':'SECRET'},code))
    assert 'SECRET' not in str(exc.value)


@pytest.mark.parametrize('damage',['duplicate','ohlc','outside','empty','status'])
def test_bad_payload(damage):
    body = dict(status='OK',results=[row()])
    if damage == 'duplicate': body['results'] *= 2
    if damage == 'ohlc': body['results'][0]['l'] = 500
    if damage == 'outside': body['results'] = [row('2025-01-01T13:30Z')]
    if damage == 'empty': body['results'] = []
    if damage == 'status': body['status'] = 'SECRET'
    with pytest.raises(DownloadError):
        fetch('AAPL','2025-10-01','2025-10-02','5min','FAKE',now=NOW,
            get=lambda *a,**k:Response(body))


def test_network_error_redacted():
    def failure(*args,**kwargs): raise RuntimeError('SECRET')
    with pytest.raises(DownloadError,match='NETWORK_FAILED') as exc:
        fetch('AAPL','2025-10-01','2025-10-02','5min','SECRET',now=NOW,get=failure)
    assert 'SECRET' not in str(exc.value)


def test_repeated_cursor_stops():
    body = dict(status='OK',results=[row()],next_url='https://api.massive.com/next')
    with pytest.raises(DownloadError,match='PAGINATION_REPEATED'):
        fetch('AAPL','2025-10-01','2025-10-02','5min','FAKE',now=NOW,
            get=lambda *a,**k:Response(body),wait=lambda _:None)


def test_dates_validate_completed_et_day_and_dst():
    lower,upper = date_range('2025-03-08','2025-03-09',NOW)
    assert (upper-lower).total_seconds() == 47*3600
    with pytest.raises(DownloadError): date_range('2026-09-16','2026-09-16',NOW)
    with pytest.raises(DownloadError): date_range('2024-01-01','2025-01-01',NOW)


def test_env_reads_fake_key_without_interpolating_password(tmp_path):
    path = tmp_path/'test.env'
    path.write_text("POLYGON_API_KEY=FAKE\nDASHBOARD_PASSWORD_HASH='value$SECRET'\n",encoding='utf-8-sig')
    assert load_key(path) == ('FAKE','api.massive.com')
    with pytest.raises(DownloadError): load_key(tmp_path)


def test_main_mocked_download_never_imports_broker(tmp_path,monkeypatch,capsys):
    from scripts import download_research_data as script
    monkeypatch.setattr('sys.argv',['download','--start','2025-10-01','--end','2025-10-02','--output',str(tmp_path/'out')])
    monkeypatch.setattr(script,'load_key',lambda _:('FAKE','api.massive.com'))
    def fake(*a,**k):
        return fetch('AAPL','2025-10-01','2025-10-02','5min','FAKE',now=NOW,
            get=lambda *a,**k:Response(dict(status='OK',results=[row()])))
    monkeypatch.setattr(script,'fetch',fake)
    assert script.main() == 0
    assert 'FAKE' not in capsys.readouterr().out


def test_exporter_imports_no_project_config_or_broker_modules():
    import ast
    from pathlib import Path
    from scripts import download_research_data as script
    tree = ast.parse(Path(script.__file__).read_text())
    imports = []
    for node in ast.walk(tree):
        if isinstance(node,ast.Import): imports.extend(alias.name for alias in node.names)
        if isinstance(node,ast.ImportFrom): imports.append(node.module)
    assert not any(name.startswith(('core','config','alpaca','data')) for name in imports)
