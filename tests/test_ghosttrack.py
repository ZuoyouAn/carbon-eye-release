"""Exercise the installed website adapter, without private targets or live scraping."""
import sys
from pathlib import Path
import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
import ghosttrack_api as api

app = FastAPI()
app.include_router(api.router)

@pytest.fixture(autouse=True)
def clear_limits():
    with api._lock:
        api._visits.clear()

@pytest.mark.parametrize('value', ['127.0.0.1', '192.168.1.1', '::1', '169.254.1.1', '224.0.0.1', 'https://example.com', '1.1.1.1/../../admin', '2001:db8::1'])
def test_invalid_ip_never_calls_provider(monkeypatch, value):
    monkeypatch.setattr(api.httpx, 'get', lambda *a, **k: pytest.fail('No network expected'))
    with pytest.raises(HTTPException) as error:
        api.ip_lookup(value)
    assert error.value.status_code == 422

def test_precision_and_fixed_https_endpoint(monkeypatch):
    def get(url, **kwargs):
        assert url == 'https://ipwho.is/1.1.1.1'
        assert kwargs == {'timeout': 10, 'follow_redirects': False}
        return httpx.Response(200, request=httpx.Request('GET', url), json={'success': True, 'ip': '1.1.1.1', 'latitude': 22.123456, 'longitude': 113.654321})
    monkeypatch.setattr(api.httpx, 'get', get)
    assert '22.123456' in api.ip_lookup('1.1.1.1')['data']['maps_url']

def test_external_quota_is_not_reported_as_network_failure(monkeypatch):
    monkeypatch.setattr(api.httpx, 'get', lambda url, **kw: httpx.Response(429, headers={'Retry-After': '3600'}, request=httpx.Request('GET', url)))
    with pytest.raises(HTTPException) as error:
        api.ip_lookup('1.1.1.1')
    assert error.value.status_code == 429 and error.value.headers['Retry-After'] == '3600'
    assert '免费额度' in error.value.detail

def test_phone_metadata_only_and_offline(monkeypatch):
    monkeypatch.setattr(api.httpx, 'get', lambda *a, **k: pytest.fail('No network expected'))
    result = api.phone_lookup('+1 202 555 0123')['data']
    assert result['e164'] == '+12025550123' and result['region_code'] == 'US'
    assert result['possible'] is True and 'latitude' not in result and 'owner' not in result
    assert api.phone_lookup('010 12345678', 'CN')['data']['country_code'] == 86

@pytest.mark.parametrize('value,region', [('abc', 'CN'), ('123', 'ZZ'), ('+1<script>', 'US')])
def test_invalid_phone(value, region):
    with pytest.raises(HTTPException):
        api.phone_lookup(value, region)

@pytest.mark.parametrize('code,status', [(200, 'reachable'), (404, 'not_found'), (410, 'not_found'), (403, 'restricted'), (429, 'restricted'), (302, 'redirect'), (500, 'unknown')])
def test_username_response_does_not_claim_identity(code, status):
    with httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(code))) as client:
        result = api.check_profile(client, ('Test', 'https://example.com/{}'), 'a.b')
    assert result['status'] == status and result['http_status'] == code

def test_username_timeout_is_indeterminate():
    def fail(request):
        raise httpx.ReadTimeout('timeout')
    with httpx.Client(transport=httpx.MockTransport(fail)) as client:
        assert api.check_profile(client, ('Test', 'https://example.com/{}'), 'demo')['status'] == 'network_error'

@pytest.mark.parametrize('value', ['../admin', 'name/path', 'a?b=c', '<script>', 'a' * 41, '.hidden'])
def test_username_input_rejects_url_injection(value):
    with pytest.raises(HTTPException):
        api.username_lookup(value)

def test_website_routes_and_strict_request_schema():
    with TestClient(app) as client:
        assert client.get('/api/ghosttrack/health').json()['platforms'] == 19
        assert client.post('/api/ghosttrack/phone', json={'value': '+12025550123'}).status_code == 200
        assert client.post('/api/ghosttrack/phone', json={'value': 'x', 'extra': 1}).status_code == 422

def test_rate_limit_has_retry_after():
    with TestClient(app) as client:
        for _ in range(8):
            assert client.post('/api/ghosttrack/phone', json={'value': '+12025550123'}).status_code == 200
        result = client.post('/api/ghosttrack/phone', json={'value': '+12025550123'})
        assert result.status_code == 429 and result.headers['retry-after'] == '60'

def test_concurrency_is_bounded():
    for _ in range(3):
        api._jobs.acquire()
    try:
        with TestClient(app) as client:
            assert client.post('/api/ghosttrack/phone', json={'value': '+12025550123'}).status_code == 429
    finally:
        for _ in range(3):
            api._jobs.release()

def test_route_assets_and_source_links_are_installed():
    directory = ROOT / 'frontend/public/ghosttrack-workbench'
    html = (directory / 'index.html').read_text(encoding='utf-8')
    js = (directory / 'app.js').read_text(encoding='utf-8')
    assert 'retry-health' in html and 'HOW IT WORKS' in html
    assert 'trustedOrigins' in js and 'credentials: \'omit\'' in js
    assert 'localStorage' not in js and 'innerHTML' not in js
    assert "/ghosttrack" in (ROOT / 'frontend/src/router/index.js').read_text(encoding='utf-8')
