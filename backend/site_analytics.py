"""First-party, bounded page analytics. No IP, account, query or media storage."""
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import re
import secrets
import threading
import time
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import Column, Date, DateTime, Index, Integer, String, delete, distinct, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from database import Base

SHANGHAI = timezone(timedelta(hours=8))
RETENTION_DAYS = 90
ORIGINS = {
    'space': {'https://carbon-eye-sip.netlify.app'},
    'video': {'https://zuoyou-space-libretv.onrender.com'},
}
SPACE_PATHS = {'/', '/novels', '/posts', '/articles', '/projects', '/human3', '/chat', '/games', '/games/swarm', '/games/winter', '/wasteland', '/solar-system', '/life-guide', '/document-tools', '/libretv', '/ghosttrack', '/crypto-lab', '/secure-geometry', '/secure-geometry/paper', '/store', '/roadmap', '/timeline', '/messages', '/changelog'}
VIDEO_PATHS = {'/', '/watch', '/cinema', '/live', '/about'}
SPACE_PATHS.add('/carbon-eye')
BOT = re.compile(r'bot|crawler|spider|headless|selenium|webdriver|python|httpx|curl|space-analytics-healthcheck', re.I)


class AnalyticsConfig(Base):
    __tablename__ = 'analytics_config'
    id = Column(Integer, primary_key=True)
    hash_secret = Column(String(64), nullable=False)
    started_at = Column(DateTime, nullable=False)
    cleanup_day = Column(Date, nullable=True)


class AnalyticsPageView(Base):
    __tablename__ = 'analytics_pageviews'
    site = Column(String(10), primary_key=True)
    event_id = Column(String(36), primary_key=True)
    visitor = Column(String(64), nullable=False)
    path = Column(String(100), nullable=False)
    day = Column(Date, nullable=False)
    created_at = Column(DateTime, nullable=False)
    __table_args__ = (Index('ix_analytics_day_site', 'day', 'site'), Index('ix_analytics_site_day_visitor', 'site', 'day', 'visitor'))


class PageEvent(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    site: Literal['space', 'video']
    event_id: str = Field(min_length=36, max_length=36)
    visitor_id: str = Field(min_length=36, max_length=36)
    path: str = Field(min_length=1, max_length=300)


def normalized_path(site, value):
    # Never store queries, hashes, titles, room codes or arbitrary path text.
    path = value.split('?', 1)[0].split('#', 1)[0].rstrip('/') or '/'
    if site == 'video':
        return path if path in VIDEO_PATHS else None
    if path in SPACE_PATHS:
        return path
    if re.fullmatch(r'/(articles|novels|posts)/:id', path):
        return path
    match = re.fullmatch(r'/(articles|novels|posts)/[0-9]+', path)
    return '/' + match.group(1) + '/:id' if match else None


def insert_for(db, model):
    dialect = db.get_bind().dialect.name
    if dialect == 'postgresql':
        return pg_insert(model)
    if dialect == 'sqlite':
        return sqlite_insert(model)
    raise HTTPException(503, '当前数据库不支持访问统计')


def config_for(db):
    config = db.get(AnalyticsConfig, 1)
    if config is None:
        db.execute(insert_for(db, AnalyticsConfig).values(id=1, hash_secret=secrets.token_hex(32), started_at=datetime.now(timezone.utc).replace(tzinfo=None)).on_conflict_do_nothing())
        config = db.get(AnalyticsConfig, 1)
    return config


class TrafficLimiter:
    """Single-instance abuse bounds. Keys are hashed and never persisted/logged."""
    def __init__(self):
        self.entries = OrderedDict()
        self.lock = threading.Lock()

    def allow(self, key, limit, now=None):
        minute = int((time.time() if now is None else now) // 60)
        with self.lock:
            while self.entries and next(iter(self.entries.values()))[0] < minute:
                self.entries.popitem(last=False)
            old_minute, count = self.entries.get(key, (minute, 0))
            count = count if old_minute == minute else 0
            if count >= limit or (key not in self.entries and len(self.entries) >= 5000):
                return False
            self.entries[key] = (minute, count + 1)
            self.entries.move_to_end(key)
            return True


limiter = TrafficLimiter()


def record_event(db, event, client_host):
    now = datetime.now(timezone.utc)
    day = now.astimezone(SHANGHAI).date()
    config = config_for(db)
    visitor = hmac.new(config.hash_secret.encode(), f'{event.site}:{event.visitor_id}'.encode(), hashlib.sha256).hexdigest()
    # The proxy's IP represents many video visitors: only use it as a broad cap.
    network = hmac.new(config.hash_secret.encode(), f'{day}:{client_host}'.encode(), hashlib.sha256).hexdigest()
    if not limiter.allow('visitor:' + visitor, 30) or not limiter.allow('network:' + network, 600) or not limiter.allow('global', 2000):
        db.rollback()
        raise HTTPException(429, '访问统计请求过于频繁')
    if config.cleanup_day != day:
        db.execute(delete(AnalyticsPageView).where(AnalyticsPageView.day < day - timedelta(days=RETENTION_DAYS - 1)))
        config.cleanup_day = day
    db.execute(insert_for(db, AnalyticsPageView).values(site=event.site, event_id=event.event_id, visitor=visitor, path=normalized_path(event.site, event.path), day=day, created_at=now.replace(tzinfo=None)).on_conflict_do_nothing())
    db.commit()


def analytics_report(db, days, site):
    today = datetime.now(timezone.utc).astimezone(SHANGHAI).date()
    since = today - timedelta(days=days - 1)
    config = config_for(db)
    started_at = config.started_at.replace(tzinfo=timezone.utc).astimezone(SHANGHAI).isoformat()
    if config.cleanup_day != today:
        db.execute(delete(AnalyticsPageView).where(AnalyticsPageView.day < today - timedelta(days=RETENTION_DAYS - 1)))
        config.cleanup_day = today
    db.commit()
    query = db.query(AnalyticsPageView).filter(AnalyticsPageView.day >= since, AnalyticsPageView.day <= today)
    if site != 'all':
        query = query.filter(AnalyticsPageView.site == site)

    def summary(base):
        pv, uv = base.with_entities(func.count(), func.count(distinct(AnalyticsPageView.visitor))).one()
        return {'pv': pv, 'uv': uv}

    totals = summary(query)
    daily = {row[0]: {'pv': row[1], 'uv': row[2]} for row in query.with_entities(AnalyticsPageView.day, func.count(), func.count(distinct(AnalyticsPageView.visitor))).group_by(AnalyticsPageView.day).all()}
    series = []
    for offset in range(days):
        day = since + timedelta(days=offset)
        series.append({'date': day.isoformat(), **daily.get(day, {'pv': 0, 'uv': 0})})
    top_pages = [{'site': s, 'path': path, 'pv': pv, 'uv': uv} for s, path, pv, uv in query.with_entities(AnalyticsPageView.site, AnalyticsPageView.path, func.count(), func.count(distinct(AnalyticsPageView.visitor))).group_by(AnalyticsPageView.site, AnalyticsPageView.path).order_by(func.count().desc(), AnalyticsPageView.site, AnalyticsPageView.path).limit(20).all()]
    return {
        'site': site, 'days': days, 'timezone': 'Asia/Shanghai', 'started_at': started_at,
        'retention_days': RETENTION_DAYS, 'from': since.isoformat(), 'to': today.isoformat(),
        'today': daily.get(today, {'pv': 0, 'uv': 0}), 'totals': totals, 'series': series, 'top_pages': top_pages,
        'sites': [{'site': s, **summary(query.filter(AnalyticsPageView.site == s))} for s in (['space', 'video'] if site == 'all' else [site])],
    }


def make_router(get_db, get_admin_user):
    router = APIRouter()

    @router.post('/api/analytics/collect', status_code=204)
    async def collect(request: Request, db=Depends(get_db)):
        chunks = bytearray()
        async for chunk in request.stream():
            if len(chunks) + len(chunk) > 4096:
                raise HTTPException(413, '统计请求过大')
            chunks.extend(chunk)
        try:
            event = PageEvent.model_validate(json.loads(chunks))
            if any(UUID(value).version != 4 for value in [event.event_id, event.visitor_id]):
                raise ValueError()
        except (ValueError, ValidationError, TypeError):
            raise HTTPException(422, '统计事件无效') from None
        if request.headers.get('origin', '') not in ORIGINS[event.site]:
            raise HTTPException(403, '统计来源不匹配')
        if normalized_path(event.site, event.path) is None or BOT.search(request.headers.get('user-agent', '')) or request.headers.get('dnt') == '1' or request.headers.get('sec-gpc') == '1':
            return Response(status_code=204, headers={'Cache-Control': 'no-store'})
        try:
            await run_in_threadpool(record_event, db, event, request.client.host if request.client else 'unknown')
        except SQLAlchemyError:
            db.rollback()
            raise HTTPException(503, '访问统计暂不可用') from None
        return Response(status_code=204, headers={'Cache-Control': 'no-store'})

    @router.get('/api/admin/analytics')
    def report(response: Response, days: int = Query(7, ge=1, le=90), site: Literal['all', 'space', 'video'] = Query('all'), db=Depends(get_db), admin=Depends(get_admin_user)):
        response.headers['Cache-Control'] = 'private, no-store'
        try:
            return analytics_report(db, days, site)
        except SQLAlchemyError:
            db.rollback()
            raise HTTPException(503, '访问统计暂不可用') from None

    return router
