"""Neon verification using TEMP tables and a rolled-back outer transaction only."""
import argparse
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable
from db_config import database_engine_options, normalize_database_url
from site_analytics import AnalyticsConfig, AnalyticsPageView, PageEvent, analytics_report, record_event


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--env-file', required=True)
    args = parser.parse_args()
    value = dotenv_values(args.env_file).get('DATABASE_URL')
    if not value:
        raise RuntimeError('No database setting in the specified private file')
    url = normalize_database_url(value)
    if url.get_backend_name() != 'postgresql' or not (url.host or '').endswith('.neon.tech'):
        raise RuntimeError('Only the existing Neon project is allowed')
    engine = create_engine(url, **database_engine_options(url))
    try:
        with engine.connect() as connection:
            outer = connection.begin()
            try:
                for model in [AnalyticsConfig, AnalyticsPageView]:
                    ddl = str(CreateTable(model.__table__).compile(dialect=engine.dialect)).replace('CREATE TABLE', 'CREATE TEMP TABLE', 1).rstrip() + ' ON COMMIT DROP'
                    connection.execute(text(ddl))
                with Session(bind=connection) as db:
                    identity = str(uuid4())
                    payload = PageEvent(site='space', path='/projects', visitor_id=identity, event_id=str(uuid4()))
                    record_event(db, payload, 'temporary-test')
                    if not connection.in_transaction():
                        raise RuntimeError('Outer transaction was unexpectedly closed')
                    record_event(db, payload, 'temporary-test')
                    record_event(db, PageEvent(site='video', path='/cinema', visitor_id=identity, event_id=str(uuid4())), 'temporary-test')
                    report = analytics_report(db, 7, 'all')
                    assert report['totals'] == {'pv': 2, 'uv': 2}
                    assert analytics_report(db, 7, 'video')['totals'] == {'pv': 1, 'uv': 1}
                    assert connection.in_transaction()
                    print('Neon TEMP-table verification passed: atomic deduplication, aggregation, site filtering. No public-table writes.')
            finally:
                if outer.is_active:
                    outer.rollback()
    finally:
        engine.dispose()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('PostgreSQL verification failed: ' + type(error).__name__)
        raise SystemExit(1)
