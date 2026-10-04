import json
from pathlib import Path
import shutil
import subprocess
from unittest.mock import patch

import httpx
import pytest
from sqlalchemy import event

from test_website_deployment import full_client, website
import human3_ai as ai
from models import Article, Post


def answers():
    return {key: 'unknown' for key in ai.ANSWER_OPTIONS}


def login(client):
    response = client.post('/api/auth/login', json={'username': 'root', 'password': '-'.join(['test', 'admin', 'only', '1234'])})
    assert response.status_code == 200
    return {'Authorization': 'Bearer ' + response.json()['token']}


def enable(monkeypatch):
    monkeypatch.setenv('HUMAN3_AI_ENABLED', 'true')
    monkeypatch.setenv('HUMAN3_AI_PROVIDER', 'doubao')
    monkeypatch.setenv('HUMAN3_AI_MODEL', 'test-model')
    monkeypatch.setenv('HUMAN3_AI_API_KEY', 'test-' + __import__('uuid').uuid4().hex)


def test_questionnaire_api_contract_matches_frontend():
    if not shutil.which('node'):
        pytest.skip('Node required for cross-language contract check')
    root = Path(__file__).resolve().parents[1]
    script = "import {QUESTIONS} from './frontend/src/features/human3/questionnaire.js'; console.log(JSON.stringify(Object.fromEntries(QUESTIONS.map(q=>[q.id,q.options.map(o=>o.id)]))))"
    result = subprocess.run(['node', '--input-type=module', '-e', script], cwd=root, capture_output=True, text=True, check=True)
    assert {key: set(values) for key, values in json.loads(result.stdout).items()} == ai.ANSWER_OPTIONS


def test_public_summary_is_one_query_and_hides_private_content(full_client):
    with website.SessionLocal() as db:
        for state, deleted in [('published', False), ('draft', False), ('hidden', False), ('published', True)]:
            db.add(Article(title='test', content='private-body', status=state, is_deleted=deleted))
        db.add(Post(user_id=10, title='visible', content='private-body'))
        db.add(Post(user_id=10, title='deleted', content='private-body', is_deleted=True))
        db.commit()
    queries = []
    def record(*args):
        queries.append(args[2])
    event.listen(website.engine, 'before_cursor_execute', record)
    try:
        response = full_client.get('/api/site-summary')
    finally:
        event.remove(website.engine, 'before_cursor_execute', record)
    assert response.json() == {'novels': 1, 'posts': 1, 'articles': 1}
    assert len(queries) == 1
    assert 'private-body' not in response.text


def test_disabled_by_default_no_provider_call(full_client, monkeypatch):
    monkeypatch.delenv('HUMAN3_AI_ENABLED', raising=False)
    with patch.object(ai, 'invoke_model') as invoke:
        status = full_client.get('/api/human3/ai-status').json()
        assert status['mode'] == 'local_rules' and not status['enabled']
        response = full_client.post('/api/human3/reflect', headers=login(full_client), json={'consent': True, 'answers': answers()})
        assert response.status_code == 503
        invoke.assert_not_called()
    assert not any(word in status for word in ('key', 'api_key', 'base_url'))


def test_auth_and_explicit_consent_before_provider_call(full_client, monkeypatch):
    enable(monkeypatch)
    with patch.object(ai, 'invoke_model') as invoke:
        payload = {'consent': True, 'answers': answers()}
        assert full_client.post('/api/human3/reflect', json=payload).status_code == 401
        payload['consent'] = False
        assert full_client.post('/api/human3/reflect', headers=login(full_client), json=payload).status_code == 400
        invoke.assert_not_called()


@pytest.mark.parametrize('changes', [
    {'answers': {}}, {'consent': 'true'}, {'answers': {**answers(), 'fake': 'unknown'}},
    {'answers': {**answers(), 'mind-learning': 'b99'}}, {'reflection': 'x' * 1601},
    {'base_url': 'https://attacker.invalid'}, {'report': 'forged report'},
])
def test_forged_and_oversized_inputs_rejected(full_client, changes):
    payload = {'consent': True, 'answers': answers(), **changes}
    with patch.object(ai, 'invoke_model') as invoke:
        assert full_client.post('/api/human3/reflect', headers=login(full_client), json=payload).status_code == 422
        invoke.assert_not_called()


def test_daily_quota_persists_and_stores_no_answers(full_client, monkeypatch):
    enable(monkeypatch)
    headers = login(full_client)
    payload = {'consent': True, 'answers': answers(), 'reflection': 'private-reflection-marker'}
    with patch.object(ai, 'invoke_model', return_value='根据自报结果，先观察一周。') as invoke:
        for _ in range(2):
            response = full_client.post('/api/human3/reflect', headers=headers, json=payload)
            assert response.status_code == 200
        assert full_client.post('/api/human3/reflect', headers=headers, json=payload).status_code == 429
        assert invoke.call_count == 2
    with website.SessionLocal() as db:
        rows = db.query(ai.Human3Quota).all()
        assert sorted(row.used for row in rows) == [2, 2]
        assert set(ai.Human3Quota.__table__.columns.keys()) == {'day', 'scope', 'used'}


def test_global_quota_and_failure_redaction(full_client, monkeypatch):
    enable(monkeypatch)
    monkeypatch.setenv('HUMAN3_AI_GLOBAL_DAILY_LIMIT', '1')
    headers = login(full_client)
    with patch.object(ai, 'invoke_model', side_effect=httpx.ReadTimeout('sensitive-provider-detail')) as invoke:
        response = full_client.post('/api/human3/reflect', headers=headers, json={'consent': True, 'answers': answers()})
        assert response.status_code == 502
        assert 'sensitive-provider-detail' not in response.text
        assert full_client.post('/api/human3/reflect', headers=headers, json={'consent': True, 'answers': answers()}).status_code == 429
        assert invoke.call_count == 1


@pytest.mark.parametrize('key,value', [('HUMAN3_AI_PROVIDER', 'attacker'), ('HUMAN3_AI_API_KEY', ''), ('HUMAN3_AI_MODEL', ''), ('HUMAN3_AI_GLOBAL_DAILY_LIMIT', '0'), ('HUMAN3_AI_USER_DAILY_LIMIT', 'invalid')])
def test_bad_configuration_fails_closed(monkeypatch, key, value):
    enable(monkeypatch)
    monkeypatch.setenv(key, value)
    assert ai.configuration()[0] is False


@pytest.mark.parametrize('provider', ['deepseek', 'doubao'])
def test_provider_adapter_uses_allowlisted_endpoint_and_bounded_plain_text(provider):
    received = []
    def respond(request):
        received.append(request)
        return httpx.Response(200, json={'choices': [{'message': {'content': '补充反思'}}]})
    real_client = httpx.Client
    with patch.object(ai.httpx, 'Client', side_effect=lambda **kw: real_client(transport=httpx.MockTransport(respond), **kw)):
        assert ai.invoke_model(provider, 'test-model', 'not-a-real-key', ai.ReflectionRequest(consent=True, answers=answers())) == '补充反思'
    assert str(received[0].url) == ai.PROVIDERS[provider]
    payload = json.loads(received[0].content)
    length_field = 'max_completion_tokens' if provider == 'doubao' else 'max_tokens'
    assert payload[length_field] == 900 and payload['stream'] is False
    assert payload['thinking'] == {'type': 'disabled'}
    assert payload['messages'][0]['role'] == 'system'


@pytest.mark.parametrize('result', ['', 'x' * 5001, None, [], {'bad': 'shape'}])
def test_invalid_model_output_is_rejected(result):
    def respond(request):
        return httpx.Response(200, json={'choices': [{'message': {'content': result}}]})
    real_client = httpx.Client
    with patch.object(ai.httpx, 'Client', side_effect=lambda **kw: real_client(transport=httpx.MockTransport(respond), **kw)):
        with pytest.raises(ValueError):
            ai.invoke_model('doubao', 'test-model', 'not-a-real-key', ai.ReflectionRequest(consent=True, answers=answers()))


def test_provider_redirect_is_not_followed():
    received = []
    def respond(request):
        received.append(str(request.url))
        return httpx.Response(302, headers={'location': 'https://attacker.invalid'})
    real_client = httpx.Client
    with patch.object(ai.httpx, 'Client', side_effect=lambda **kw: real_client(transport=httpx.MockTransport(respond), **kw)):
        with pytest.raises(httpx.HTTPStatusError):
            ai.invoke_model('doubao', 'test-model', 'not-a-real-key', ai.ReflectionRequest(consent=True, answers=answers()))
    assert received == [ai.PROVIDERS['doubao']]
