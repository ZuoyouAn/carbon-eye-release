from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Column, Integer, MetaData, Table, Text, create_engine, func, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("CARBON_EYE_STANDALONE", "true")
import main as website
from db_config import database_engine_options, normalize_database_url
from models import Base, Novel1, Profile, User, Yulu

spec = importlib.util.spec_from_file_location("website_migration", ROOT / "scripts" / "migrate_website_database.py")
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


def memory_engine():
    return create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


def populate(engine):
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        db.add(Profile(id=1, name="测试站点", title="学习", description="中文资料", github="https://github.com/example", email="example@example.com"))
        db.add(User(id=10, username="root", password_hash=website.hash_password("-".join(["test", "admin", "only", "1234"])), role="admin", is_muted=False, is_deleted=False))
        db.add(Novel1(xs_id=8, xs_name="中文小说", xs_content="第一章\nUnicode 内容 ✨"))
        db.add(Yulu(id=13, yname="fcx", content="测试语录"))
        db.commit()


@pytest.fixture
def full_client(monkeypatch):
    engine = memory_engine()
    populate(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(website, "engine", engine)
    monkeypatch.setattr(website, "SessionLocal", factory)
    monkeypatch.setenv("CARBON_EYE_STANDALONE", "false")
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("SEED_DEMO_DATA", raising=False)

    def override_db():
        with factory() as db:
            yield db

    website.app.dependency_overrides[website.get_db] = override_db
    try:
        with TestClient(website.app) as client:
            yield client
    finally:
        website.app.dependency_overrides.pop(website.get_db, None)
        engine.dispose()


@pytest.mark.parametrize("scheme", ["postgres", "postgresql", "postgresql+psycopg"])
def test_neon_url_normalization(scheme):
    url = normalize_database_url(f"{scheme}://example:ignored@db.example/neondb?sslmode=require")
    assert url.drivername == "postgresql+psycopg"
    options = database_engine_options(url)
    assert options["poolclass"] is NullPool
    assert options["connect_args"]["prepare_threshold"] is None
    assert url.query["sslmode"] == "require"
    assert options["hide_parameters"] is True


def test_full_site_readiness_and_content(full_client):
    assert full_client.get("/readyz").status_code == 200
    assert full_client.get("/healthz").json()["website_mode"] == "full"
    assert full_client.get("/api/profile").json()["description"] == "中文资料"
    assert len(full_client.get("/api/novels").json()) == 1
    assert full_client.get("/api/yulu/random").status_code == 200
    for path in ["/api/articles", "/api/posts", "/api/messages"]:
        assert full_client.get(path).status_code == 200
    assert full_client.get("/api/admin/dashboard").status_code == 401


def test_registered_users_can_publish_but_not_administer(full_client):
    payload = {"username": "visitor", "password": "-".join(["test", "visitor", "1234"])}
    assert full_client.post("/api/auth/register", json=payload).status_code == 200
    response = full_client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    headers = {"Authorization": "Bearer " + response.json()["token"]}
    assert full_client.get("/api/admin/dashboard", headers=headers).status_code == 403
    assert full_client.post("/api/posts", headers=headers, json={"title": "云端帖子", "content": "测试"}).status_code == 200
    assert full_client.post("/api/messages", headers=headers, json={"content": "留言测试"}).status_code == 200
    assert full_client.get("/api/me/summary", headers=headers).status_code == 200


def test_render_full_mode_rejects_ephemeral_sqlite(monkeypatch):
    monkeypatch.setenv("CARBON_EYE_STANDALONE", "false")
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setattr(website, "engine", memory_engine())
    with pytest.raises(RuntimeError, match="持久化"):
        with TestClient(website.app):
            pass


def test_database_failure_cannot_claim_full_site_is_ready(monkeypatch):
    from sqlalchemy.exc import OperationalError
    monkeypatch.setenv("CARBON_EYE_STANDALONE", "false")
    monkeypatch.delenv("RENDER", raising=False)
    with patch.object(website.Base.metadata, "create_all", side_effect=OperationalError("SELECT", {}, Exception("sensitive example"))):
        with pytest.raises(RuntimeError, match="初始化失败") as error:
            with TestClient(website.app):
                pass
    assert "sensitive example" not in str(error.value)


def test_legacy_schema_upgrade_is_idempotent_on_sqlite(monkeypatch):
    engine = memory_engine()
    with engine.begin() as db:
        for name in ["articles", "posts", "post_comments", "article_comments"]:
            db.execute(text(f"CREATE TABLE {name} (id INTEGER PRIMARY KEY, content TEXT)"))
    monkeypatch.setattr(website, "engine", engine)
    website.upgrade_existing_schema()
    website.upgrade_existing_schema()
    with engine.connect() as db:
        db.execute(text("SELECT category, deleted_at, is_pinned FROM articles"))


def test_migration_preserves_unicode_legacy_rows_and_omits_sessions():
    source, target = memory_engine(), memory_engine()
    populate(source)
    legacy = Table("novel", MetaData(), Column("xs_id", Integer, primary_key=True), Column("xs_name", Text), Column("xs_content", Text))
    legacy.create(source)
    with source.begin() as db:
        db.execute(legacy.insert(), {"xs_id": 3850, "xs_name": "旧小说", "xs_content": "旧内容"})
        from datetime import datetime, timedelta
        db.execute(website.AuthToken.__table__.insert(), {"token": "test-session", "user_id": 10, "expires_at": datetime.utcnow() + timedelta(days=1)})
    dry_run = migration.migrate(source, target)
    assert dry_run["mode"] == "dry-run"
    from sqlalchemy import inspect
    assert inspect(target).get_table_names() == []
    report = migration.migrate(source, target, apply=True)
    assert report["verified"] is True
    assert report["target_rows"]["auth_tokens"] == 0
    assert report["target_rows"]["novel"] == 1
    with target.connect() as db:
        assert db.scalar(select(Novel1.__table__.c.xs_content)) == "第一章\nUnicode 内容 ✨"
    with source.connect() as db:
        assert db.scalar(select(func.count()).select_from(website.AuthToken.__table__)) == 1
    with pytest.raises(ValueError, match="not empty"):
        migration.migrate(source, target, apply=True)


def test_migration_refuses_same_database():
    engine = memory_engine()
    with pytest.raises(ValueError, match="different databases"):
        migration.migrate(engine, engine, apply=True)


def test_full_mode_never_silently_seeds_demo_content(full_client):
    assert full_client.get("/api/articles").json()["total"] == 0
    assert full_client.get("/api/posts").json()["total"] == 0
    assert full_client.get("/api/messages").json()["total"] == 0
