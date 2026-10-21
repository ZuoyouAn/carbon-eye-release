"""Use disposable SQLite only; never send test pageviews to production."""
from datetime import datetime, timedelta, timezone
import json
import uuid

import pytest
from sqlalchemy.dialects import postgresql

from test_website_deployment import full_client
from test_permissions import login, create_member
import main as website
import site_analytics as traffic


def event(site='space', path='/', visitor=None, identifier=None):
    return {'site': site, 'path': path, 'visitor_id': visitor or str(uuid.uuid4()), 'event_id': identifier or str(uuid.uuid4())}


def collect(client, payload, **headers):
    return client.post('/api/analytics/collect', json=payload, headers={'Origin': next(iter(traffic.ORIGINS[payload['site']])), 'User-Agent': 'Mozilla/5.0 Browser', **headers})


def report(client, **params):
    headers, _ = login(client)
    return client.get('/api/admin/analytics', headers=headers, params=params)


def test_empty_report_is_private_admin_only_and_has_seven_zero_days(full_client):
    assert full_client.get('/api/admin/analytics').status_code == 401
    _, low, _ = create_member(full_client)
    assert full_client.get('/api/admin/analytics', headers=low).status_code == 403
    response = report(full_client)
    data = response.json()
    assert response.status_code == 200 and response.headers['cache-control'] == 'private, no-store'
    assert data['totals'] == {'pv': 0, 'uv': 0} and len(data['series']) == 7
    assert data['timezone'] == 'Asia/Shanghai' and data['retention_days'] == 90
    assert data['top_pages'] == [] and 'hash_secret' not in response.text


def test_duplicate_events_are_idempotent_and_browser_uv_is_deduplicated(full_client):
    first = event()
    assert collect(full_client, first).status_code == 204
    assert collect(full_client, first).status_code == 204
    assert collect(full_client, event(path='/projects', visitor=first['visitor_id'])).status_code == 204
    assert collect(full_client, event()).status_code == 204
    data = report(full_client).json()
    assert data['today'] == data['totals'] == {'pv': 3, 'uv': 2}
    assert data['top_pages'][0]['path'] == '/' and data['top_pages'][0]['pv'] == 2


def test_site_filter_and_cross_site_identity_are_explicit(full_client):
    visitor = str(uuid.uuid4())
    collect(full_client, event(visitor=visitor))
    collect(full_client, event('video', '/cinema', visitor))
    assert report(full_client).json()['totals'] == {'pv': 2, 'uv': 2}
    assert report(full_client, site='video').json()['totals'] == {'pv': 1, 'uv': 1}
    assert {row['site'] for row in report(full_client).json()['sites']} == {'space', 'video'}


@pytest.mark.parametrize('path', ['/api/cinema', '/api/proxy', '/video.ts', '/admin', '/profile', '/login', '/unknown/private-name', '//example.com', '/articles/name'])
def test_non_page_and_private_paths_do_not_create_records(full_client, path):
    assert collect(full_client, event(path=path)).status_code == 204
    with website.SessionLocal() as db:
        assert db.query(traffic.AnalyticsPageView).count() == 0


def test_queries_rooms_titles_ids_and_raw_visitors_are_not_persisted(full_client):
    payload = event('video', '/watch?url=https://sensitive.example/movie.mp4&room=private-room#account')
    assert collect(full_client, payload).status_code == 204
    assert collect(full_client, event(path='/articles/12345?token=private')).status_code == 204
    assert collect(full_client, event(path='/posts/:id')).status_code == 204
    with website.SessionLocal() as db:
        rows = db.query(traffic.AnalyticsPageView).all()
        assert {row.path for row in rows} == {'/watch', '/articles/:id', '/posts/:id'}
        assert all(len(row.visitor) == 64 and row.visitor != payload['visitor_id'] for row in rows)
    rendered = report(full_client).text
    assert all(value not in rendered for value in [payload['visitor_id'], 'sensitive.example', 'private-room', '12345', 'token='])


@pytest.mark.parametrize('headers', [{'DNT': '1'}, {'Sec-GPC': '1'}, {'User-Agent': 'HeadlessChrome'}, {'User-Agent': 'Googlebot'}, {'User-Agent': 'space-analytics-healthcheck'}])
def test_opt_out_bots_and_health_probes_do_not_count(full_client, headers):
    assert collect(full_client, event(), **headers).status_code == 204
    assert report(full_client).json()['totals']['pv'] == 0


def test_origin_payload_bounds_and_unsupported_filters(full_client):
    assert collect(full_client, event(), Origin='https://evil.example').status_code == 403
    assert collect(full_client, event('video'), Origin='https://carbon-eye-sip.netlify.app').status_code == 403
    assert collect(full_client, {**event(), 'email': 'must-not-be-accepted'}).status_code == 422
    assert collect(full_client, {**event(), 'visitor_id': 'x' * 36}).status_code == 422
    assert full_client.post('/api/analytics/collect', content=b'x' * 4097).status_code == 413
    assert report(full_client, days=91).status_code == 422
    assert report(full_client, site='unknown').status_code == 422


def test_old_analytics_are_cleaned_without_deleting_accounts(full_client):
    report(full_client)
    with website.SessionLocal() as db:
        db.add(traffic.AnalyticsPageView(site='space', event_id=str(uuid.uuid4()), visitor='a' * 64, path='/', day=(datetime.now(timezone.utc) - timedelta(days=100)).date(), created_at=datetime.now(timezone.utc).replace(tzinfo=None)))
        db.get(traffic.AnalyticsConfig, 1).cleanup_day = None
        db.commit()
    assert collect(full_client, event()).status_code == 204
    with website.SessionLocal() as db:
        assert db.query(traffic.AnalyticsPageView).count() == 1
        assert db.query(website.User).count() == 1


def test_daily_buckets_use_china_time(full_client, monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 21, 17, 30, tzinfo=timezone.utc).astimezone(tz)
    monkeypatch.setattr(traffic, 'datetime', Clock)
    assert collect(full_client, event()).status_code == 204
    data = report(full_client).json()
    assert data['to'] == '2026-10-22' and data['series'][-1] == {'date': '2026-10-22', 'pv': 1, 'uv': 1}


def test_limiter_is_bounded_and_resets_per_minute():
    limiter = traffic.TrafficLimiter()
    assert all(limiter.allow('visitor', 2, 120) for _ in range(2))
    assert not limiter.allow('visitor', 2, 120)
    assert limiter.allow('visitor', 2, 180)
    assert len(limiter.entries) == 1


def test_postgres_insert_uses_conflict_safe_event_key():
    statement = traffic.pg_insert(traffic.AnalyticsPageView).values(site='space', event_id=str(uuid.uuid4()), visitor='x' * 64, path='/', day=datetime.now().date(), created_at=datetime.now()).on_conflict_do_nothing()
    assert 'ON CONFLICT DO NOTHING' in str(statement.compile(dialect=postgresql.dialect()))
