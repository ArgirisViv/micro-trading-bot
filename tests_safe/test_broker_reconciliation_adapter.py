from types import SimpleNamespace
import pytest
import requests
from core import alpaca_trade as broker


def test_get_order_always_requests_nested_legs(monkeypatch):
    calls=[]
    class Client:
        def get_order(self,order_id,**kwargs):calls.append((order_id,kwargs));return 'snapshot'
    monkeypatch.setattr(broker,'_get_client',lambda asset:Client())
    assert broker.get_order('known-id')=='snapshot'
    assert calls==[('known-id',{'nested':True})]


def test_only_explicit_404_is_not_found(monkeypatch):
    class APIError(Exception):
        def __init__(self,status):self.status_code=status
    class Client:
        status=404
        def get_order_by_client_order_id(self,client_id):raise APIError(self.status)
    client=Client()
    monkeypatch.setattr(broker,'APIError',APIError)
    monkeypatch.setattr(broker,'_get_client',lambda asset:client)
    assert broker.get_order_by_client_order_id('known-id') is None
    client.status=403
    with pytest.raises(APIError):broker.get_order_by_client_order_id('known-id')


def test_arbitrary_lookup_exception_is_never_not_found(monkeypatch):
    class Client:
        def get_order_by_client_order_id(self,client_id):raise TimeoutError()
    monkeypatch.setattr(broker,'_get_client',lambda asset:Client())
    with pytest.raises(TimeoutError):broker.get_order_by_client_order_id('known-id')


def test_transport_disables_sdk_retries_and_bounds_requests(monkeypatch):
    old=SimpleNamespace(close=lambda:None)
    client=SimpleNamespace(_retry=3,_session=old)
    broker._configure_transport(client)
    assert client._retry==0
    calls=[]
    monkeypatch.setattr(requests.Session,'request',lambda self,method,url,**kwargs:calls.append(kwargs))
    client._session.request('POST','https://paper-api.alpaca.markets/v2/orders')
    assert calls[0]['timeout']==(5,20)
    assert calls[0]['allow_redirects'] is False
