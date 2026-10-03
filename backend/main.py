from datetime import datetime
from datetime import timedelta
import hashlib
import hmac
import json
import math
import asyncio
import os
from pathlib import Path
import random
import secrets
from typing import Any
from typing import Optional

from fastapi import Depends
from fastapi import FastAPI
from fastapi import Header
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy import inspect
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import Base
from database import SessionLocal
from database import engine
from database import get_db
from models import Article
from models import ArticleComment
from models import ArticleFavorite
from models import ArticleLike
from models import AuthToken
from models import Message
from models import Novel1
from models import NovelFavorite
from models import Post
from models import PostComment
from models import PostLike
from models import PermissionAudit
from models import Profile
from models import ReadingProgress
from models import User
from models import Yulu
from permissions import ROLE_LABELS, permissions_for
from typing import Literal
from carbon_eye_realtime import get_realtime_aqi, refresh_realtime_aqi_hourly
from secure_geometry import SecureGeometryError
from secure_geometry import calculate_secure_geometry


TOKEN_DAYS = 7
ARTICLE_STATUSES = {"draft", "published", "hidden"}
MESSAGE_STATUSES = {"published", "hidden"}
CARBON_EYE_DATA_DIR = Path(__file__).resolve().parent / "data" / "carbon_eye"
CARBON_EYE_STATIC_FILES = (
    "overview.json",
    "monthly_trends.json",
    "weather_2024.json",
    "weather/weather_park_monthly.json",
    "weather/weather_air_correlations.json",
    "carbon_emissions.json",
    "warnings.json",
    "daily_cases.json",
    "methodology.json",
    "park_electricity_emissions.json",
    "sip_economic_carbon_intensity.json",
    "park_environment_snapshot.json",
    "industry_profile.json",
    "source_registry.json",
    "data_quality.json",
    "cdci.json",
    "cdci_sensitivity.json",
)


class RegisterRequest(BaseModel):
    model_config = {"extra": "forbid"}
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class PasswordRequest(BaseModel):
    old_password: str
    new_password: str


class AdminCreateUserRequest(BaseModel):
    model_config = {"extra": "forbid"}
    username: str
    password: str
    role: Literal["user", "elevated", "admin"] = "user"
    admin_password: Optional[str] = None


class AdminUpdateUserRequest(BaseModel):
    model_config = {"extra": "forbid"}
    username: Optional[str] = None
    password: Optional[str] = None
    is_muted: Optional[bool] = None


class RoleUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}
    role: Literal["user", "elevated", "admin"]
    admin_password: str
    new_password: Optional[str] = None


class PostCreateRequest(BaseModel):
    title: str
    content: str


class CommentCreateRequest(BaseModel):
    content: str


class ArticleCreateRequest(BaseModel):
    title: str
    summary: str = ""
    category: str = "随笔"
    tags: str = ""
    content: str
    status: str = "published"
    is_pinned: bool = False


class ArticleStatusRequest(BaseModel):
    status: str


class ArticlePinRequest(BaseModel):
    is_pinned: bool


class MessageCreateRequest(BaseModel):
    nickname: str = "游客"
    content: str


class MessageStatusRequest(BaseModel):
    status: str


class ReadingProgressRequest(BaseModel):
    progress: int = 0
    font_size: int = 18
    theme: str = "dark"


class SecureGeometryRequest(BaseModel):
    relation: str
    alice: dict[str, Any]
    bob: dict[str, Any]


app = FastAPI(title="个人网站后端")


def carbon_eye_cors_origins() -> list[str]:
    configured = os.getenv("CORS_ORIGINS", "")
    if configured.strip():
        return [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]
    return [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
    ]


app.add_middleware(
    CORSMiddleware,
    allow_origins=carbon_eye_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def carbon_eye_static_data_status() -> dict[str, Any]:
    missing = [name for name in CARBON_EYE_STATIC_FILES if not (CARBON_EYE_DATA_DIR / name).is_file()]
    return {
        "status": "ok" if not missing else "degraded",
        "data_dir": "backend/data/carbon_eye",
        "missing_files": missing,
        "generation_command": "python scripts/build_carbon_eye_data.py",
    }


def load_carbon_eye_json(file_name: str):
    relative_path = Path(file_name)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise HTTPException(status_code=400, detail="Invalid Carbon Eye data path")
    data_path = CARBON_EYE_DATA_DIR / relative_path
    if not data_path.is_file():
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Carbon Eye static data is unavailable.",
                "missing_file": relative_path.as_posix(),
                "generation_command": "python scripts/build_carbon_eye_data.py",
            },
        )
    try:
        return json.loads(data_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"碳眼数据文件格式错误：{file_name}") from exc


def now_utc():
    return datetime.utcnow()


def hash_password(password: str):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, saved_hash: str):
    try:
        salt, digest = saved_hash.split("$", 1)
    except ValueError:
        return False
    new_digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
    return hmac.compare_digest(new_digest, digest)


def clean_text(value: str, field_name: str, max_length: int, allow_empty: bool = False):
    text_value = (value or "").strip()
    if not text_value and not allow_empty:
        raise HTTPException(status_code=400, detail=f"{field_name}不能为空")
    if len(text_value) > max_length:
        raise HTTPException(status_code=400, detail=f"{field_name}不能超过 {max_length} 个字符")
    return text_value


def clean_status(value: str, allowed: set[str], field_name: str):
    status = clean_text(value, field_name, 20)
    if status not in allowed:
        raise HTTPException(status_code=400, detail=f"{field_name}不正确")
    return status


def validate_new_password(value: str, role: str = "user"):
    # Do not trim passwords: spaces can be intentional passphrase characters.
    minimum = 12 if role == "admin" else 8
    if len(value) < minimum or len(value) > 80:
        raise HTTPException(status_code=400, detail=f"密码需要 {minimum}–80 个字符")
    if value.lower() in {"123456", "12345678", "123456789012", "password", "password1234"} or len(set(value)) < 3:
        raise HTTPException(status_code=400, detail="请勿使用常见密码或重复字符密码")
    return value


def normalize_page(page: int, page_size: int):
    safe_page = max(1, int(page or 1))
    safe_page_size = min(50, max(1, int(page_size or 10)))
    return safe_page, safe_page_size


def paged_response(query, page: int, page_size: int, mapper):
    safe_page, safe_page_size = normalize_page(page, page_size)
    total = query.count()
    items = query.offset((safe_page - 1) * safe_page_size).limit(safe_page_size).all()
    return {
        "items": [mapper(item) for item in items],
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
        "pages": max(1, math.ceil(total / safe_page_size)),
    }


def format_time(value):
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


def split_tags(tags: str):
    return [tag.strip() for tag in (tags or "").split(",") if tag.strip()]


def user_to_dict(user: User):
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "role_label": ROLE_LABELS.get(user.role, "未授权"),
        "permissions": permissions_for(user.role, user.is_muted),
        "is_muted": bool(user.is_muted),
        "is_deleted": bool(user.is_deleted),
        "created_at": format_time(user.created_at),
    }


def get_username(db: Session, user_id: Optional[int]):
    if not user_id:
        return "游客"
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return "未知用户"
    if user.is_deleted:
        return f"{user.username}（已删除）"
    return user.username


def optional_user_from_header(db: Session, authorization: Optional[str]):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token_value = authorization.replace("Bearer ", "", 1).strip()
    token = db.query(AuthToken).filter(AuthToken.token == token_value).first()
    if not token:
        return None
    if token.expires_at < now_utc():
        db.delete(token)
        db.commit()
        return None
    user = db.query(User).filter(User.id == token.user_id).first()
    if not user or user.is_deleted:
        return None
    return user


def get_current_user(authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    user = optional_user_from_header(db, authorization)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    if user.role not in ROLE_LABELS:
        raise HTTPException(status_code=403, detail="账号权限未配置，请联系管理员")
    return user


def get_admin_user(current_user: User = Depends(get_current_user)):
    if "manage_users" not in permissions_for(current_user.role, current_user.is_muted):
        raise HTTPException(status_code=403, detail="只有管理员可以操作")
    return current_user


def ensure_not_muted(user: User):
    if user.is_muted:
        raise HTTPException(status_code=403, detail="你已被禁言，不能发布内容")


def get_publishing_user(current_user: User = Depends(get_current_user)):
    ensure_not_muted(current_user)
    if "publish" not in permissions_for(current_user.role):
        raise HTTPException(status_code=403, detail="当前为低权限账号，请联系管理员提升为高权限后发布内容")
    return current_user


def revoke_user_tokens(db: Session, user_id: int):
    db.query(AuthToken).filter(AuthToken.user_id == user_id).delete(synchronize_session=False)


def record_permission_change(db: Session, actor: User, target: User, old_role: Optional[str], action="role_change"):
    db.add(PermissionAudit(actor_user_id=actor.id, target_user_id=target.id, action=action, old_role=old_role, new_role=target.role))


def initialize_configured_admin(db: Session):
    """One-time owner-controlled setup; never resets an existing admin on restart."""
    setup_password = os.getenv("ADMIN_SETUP_PASSWORD")
    if not setup_password:
        return
    try:
        validate_new_password(setup_password, "admin")
    except HTTPException:
        raise RuntimeError("ADMIN_SETUP_PASSWORD 至少需要 12 位，且不能是常见弱密码") from None
    if db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(739302605)"))
    existing = db.query(User).filter(User.username == "admin").with_for_update().first()
    if existing:
        if existing.role != "admin" or existing.is_deleted or existing.is_muted:
            raise RuntimeError("admin 用户名已被非正常管理员占用，不会自动提权或恢复账号")
        return
    legacy = db.query(User).filter(User.username == "root", User.role == "admin", User.is_deleted == False).with_for_update().first()
    if legacy:
        # Preserve the user ID and all related content, but invalidate the
        # publicly advertised legacy credentials and every previous session.
        legacy.username = "admin"
        legacy.password_hash = hash_password(setup_password)
        legacy.is_muted = False
        admin = legacy
    else:
        admin = User(username="admin", password_hash=hash_password(setup_password), role="admin", is_muted=False, is_deleted=False)
        db.add(admin)
        db.flush()
    revoke_user_tokens(db, admin.id)
    record_permission_change(db, admin, admin, "admin" if legacy else None, "admin_setup")
    db.commit()


def ensure_article_exists(db: Session, article_id: int, user: Optional[User] = None, admin_mode: bool = False):
    article = db.query(Article).filter(Article.id == article_id).first()
    is_admin = admin_mode or (user and user.role == "admin")
    if not article or (article.is_deleted and not is_admin) or (article.status != "published" and not is_admin):
        raise HTTPException(status_code=404, detail="文章不存在")
    return article


def ensure_post_exists(db: Session, post_id: int, admin_mode: bool = False):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post or (post.is_deleted and not admin_mode):
        raise HTTPException(status_code=404, detail="帖子不存在")
    return post


def ensure_novel_exists(db: Session, novel_id: int):
    novel = db.query(Novel1).filter(Novel1.xs_id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")
    return novel


def novel_to_dict(db: Session, novel: Novel1, user: Optional[User] = None):
    favorite_count = db.query(NovelFavorite).filter(NovelFavorite.novel_id == novel.xs_id).count()
    is_favorited = bool(user and db.query(NovelFavorite).filter(NovelFavorite.novel_id == novel.xs_id, NovelFavorite.user_id == user.id).first())
    progress = db.query(ReadingProgress).filter(ReadingProgress.novel_id == novel.xs_id, ReadingProgress.user_id == user.id).first() if user else None
    return {
        "id": novel.xs_id,
        "name": novel.xs_name,
        "content": novel.xs_content,
        "favorite_count": favorite_count,
        "is_favorited": is_favorited,
        "progress": progress.progress if progress else 0,
        "font_size": progress.font_size if progress else 18,
        "theme": progress.theme if progress else "dark",
    }


def post_to_dict(db: Session, post: Post, user: Optional[User] = None):
    comment_count = db.query(PostComment).filter(PostComment.post_id == post.id, PostComment.is_deleted == False).count()
    like_count = db.query(PostLike).filter(PostLike.post_id == post.id).count()
    is_liked = bool(user and db.query(PostLike).filter(PostLike.post_id == post.id, PostLike.user_id == user.id).first())
    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "author": get_username(db, post.user_id),
        "created_at": format_time(post.created_at),
        "is_deleted": bool(post.is_deleted),
        "deleted_at": format_time(post.deleted_at),
        "comment_count": comment_count,
        "like_count": like_count,
        "is_liked": is_liked,
    }


def post_comment_to_dict(db: Session, comment: PostComment):
    return {
        "id": comment.id,
        "type": "post",
        "post_id": comment.post_id,
        "content": comment.content,
        "author": get_username(db, comment.user_id),
        "created_at": format_time(comment.created_at),
        "is_deleted": bool(comment.is_deleted),
    }


def article_to_dict(db: Session, article: Article, user: Optional[User] = None):
    comment_count = db.query(ArticleComment).filter(ArticleComment.article_id == article.id, ArticleComment.is_deleted == False).count()
    like_count = db.query(ArticleLike).filter(ArticleLike.article_id == article.id).count()
    favorite_count = db.query(ArticleFavorite).filter(ArticleFavorite.article_id == article.id).count()
    is_liked = bool(user and db.query(ArticleLike).filter(ArticleLike.article_id == article.id, ArticleLike.user_id == user.id).first())
    is_favorited = bool(user and db.query(ArticleFavorite).filter(ArticleFavorite.article_id == article.id, ArticleFavorite.user_id == user.id).first())
    return {
        "id": article.id,
        "title": article.title,
        "summary": article.summary,
        "category": article.category,
        "tags": split_tags(article.tags),
        "tags_text": article.tags,
        "content": article.content,
        "status": article.status,
        "is_pinned": bool(article.is_pinned),
        "is_deleted": bool(article.is_deleted),
        "created_at": format_time(article.created_at),
        "updated_at": format_time(article.updated_at),
        "deleted_at": format_time(article.deleted_at),
        "comment_count": comment_count,
        "like_count": like_count,
        "favorite_count": favorite_count,
        "is_liked": is_liked,
        "is_favorited": is_favorited,
    }


def article_comment_to_dict(db: Session, comment: ArticleComment):
    return {
        "id": comment.id,
        "type": "article",
        "article_id": comment.article_id,
        "content": comment.content,
        "author": get_username(db, comment.user_id),
        "created_at": format_time(comment.created_at),
        "is_deleted": bool(comment.is_deleted),
    }


def message_to_dict(db: Session, message: Message):
    return {
        "id": message.id,
        "nickname": message.nickname,
        "content": message.content,
        "author": get_username(db, message.user_id) if message.user_id else message.nickname,
        "status": message.status,
        "is_deleted": bool(message.is_deleted),
        "created_at": format_time(message.created_at),
        "deleted_at": format_time(message.deleted_at),
    }


def yulu_to_dict(yulu: Yulu):
    return {
        "id": yulu.id,
        "yname": yulu.yname,
        "content": yulu.content,
    }


def add_column_if_missing(connection, table_name: str, column_name: str, ddl: str):
    columns = {column["name"] for column in inspect(connection).get_columns(table_name)}
    if column_name not in columns:
        if connection.dialect.name == "postgresql":
            ddl = ddl.replace("DATETIME", "TIMESTAMP")
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {ddl}"))


def upgrade_existing_schema():
    with engine.begin() as connection:
        add_column_if_missing(connection, "articles", "summary", "summary VARCHAR(255) NOT NULL DEFAULT ''")
        add_column_if_missing(connection, "articles", "category", "category VARCHAR(80) NOT NULL DEFAULT 'Essay'")
        add_column_if_missing(connection, "articles", "tags", "tags VARCHAR(255) NOT NULL DEFAULT ''")
        add_column_if_missing(connection, "articles", "status", "status VARCHAR(20) NOT NULL DEFAULT 'published'")
        add_column_if_missing(connection, "articles", "is_pinned", "is_pinned BOOLEAN NOT NULL DEFAULT FALSE")
        add_column_if_missing(connection, "articles", "is_deleted", "is_deleted BOOLEAN NOT NULL DEFAULT FALSE")
        add_column_if_missing(connection, "articles", "deleted_at", "deleted_at DATETIME NULL")
        add_column_if_missing(connection, "posts", "is_deleted", "is_deleted BOOLEAN NOT NULL DEFAULT FALSE")
        add_column_if_missing(connection, "posts", "deleted_at", "deleted_at DATETIME NULL")
        add_column_if_missing(connection, "post_comments", "is_deleted", "is_deleted BOOLEAN NOT NULL DEFAULT FALSE")
        add_column_if_missing(connection, "post_comments", "deleted_at", "deleted_at DATETIME NULL")
        add_column_if_missing(connection, "article_comments", "is_deleted", "is_deleted BOOLEAN NOT NULL DEFAULT FALSE")
        add_column_if_missing(connection, "article_comments", "deleted_at", "deleted_at DATETIME NULL")
        if connection.dialect.name != "sqlite":
            connection.execute(text("ALTER TABLE articles ALTER COLUMN category SET DEFAULT '随笔'"))
        connection.execute(text("UPDATE articles SET category = :category WHERE category IN ('Ëæ±Ê', 'éç¬', '')"), {"category": "随笔"})
        connection.execute(text("UPDATE articles SET status = 'published' WHERE status IS NULL OR status = ''"))


def seed_demo_data(db: Session, admin: User):
    if db.query(Article).count() == 0:
        article = Article(
            title="欢迎来到左右的个人网站",
            summary="这是一篇 Markdown 示例文章，用来测试文章发布、分类、标签、点赞、收藏和评论。",
            category="站点日志",
            tags="Vue,FastAPI,MySQL",
            content="# 欢迎\n\n这是第一篇 Markdown 文章。\n\n- 前端使用 Vue 3 + Vite\n- 后端使用 FastAPI\n- 数据库使用 MySQL\n\n后面可以继续写学习笔记、项目总结和个人日记。",
            status="published",
            is_pinned=True,
        )
        db.add(article)
    if db.query(Post).count() == 0:
        post = Post(user_id=admin.id, title="第一个帖子", content="帖子区已经可以使用了，登录后可以发帖、点赞和评论。")
        db.add(post)
    if db.query(Message).count() == 0:
        message = Message(user_id=admin.id, nickname="左右", content="留言板已经上线，欢迎来这里留一句话。", status="published")
        db.add(message)
    db.commit()


realtime_refresh_task = None
realtime_refresh_stop_event = None
database_initialized = False


@app.on_event("startup")
async def startup_event():
    global realtime_refresh_task, realtime_refresh_stop_event, database_initialized
    database_initialized = False
    if os.getenv("CARBON_EYE_REALTIME_SCHEDULER", "").strip().lower() in {"1", "true", "yes"}:
        realtime_refresh_stop_event = asyncio.Event()
        realtime_refresh_task = asyncio.create_task(refresh_realtime_aqi_hourly(realtime_refresh_stop_event))
    if os.getenv("CARBON_EYE_STANDALONE", "").strip().lower() in {"1", "true", "yes"}:
        return
    if os.getenv("RENDER") and engine.dialect.name == "sqlite":
        raise RuntimeError("完整网站部署必须配置持久化 DATABASE_URL，不能使用 Render 临时 SQLite 文件")
    try:
        Base.metadata.create_all(bind=engine)
        upgrade_existing_schema()
        db = SessionLocal()
        try:
            initialize_configured_admin(db)
            bootstrap_username = clean_text(os.getenv("INITIAL_ADMIN_USERNAME", "admin"), "管理员用户名", 30)
            admin = db.query(User).filter(User.role == "admin", User.is_deleted == False).order_by(User.id).first()
            if not admin:
                bootstrap_password = os.getenv("INITIAL_ADMIN_PASSWORD")
                if not bootstrap_password:
                    database_initialized = True
                    return
                try:
                    validate_new_password(bootstrap_password, "admin")
                except HTTPException:
                    raise RuntimeError("INITIAL_ADMIN_PASSWORD 至少需要 12 个字符，且不能是常见弱密码") from None
                if db.query(User).filter(User.username == bootstrap_username).first():
                    raise RuntimeError("初始化管理员用户名已存在，不会自动提权已有账号")
                admin = User(username=bootstrap_username, password_hash=hash_password(bootstrap_password), role="admin", is_muted=False, is_deleted=False)
                db.add(admin)
                db.commit()
                db.refresh(admin)
            if os.getenv("SEED_DEMO_DATA", "").strip().lower() in {"1", "true", "yes"}:
                seed_demo_data(db, admin)
            database_initialized = True
        finally:
            db.close()
    except SQLAlchemyError as exc:
        # Fail a full-site deploy instead of advertising a healthy partial site.
        # Never log connection URLs, SQL parameters or account content.
        raise RuntimeError("数据库初始化失败，请检查持久化 DATABASE_URL 和网络配置") from None


@app.on_event("shutdown")
async def shutdown_event():
    if realtime_refresh_stop_event:
        realtime_refresh_stop_event.set()
    if realtime_refresh_task:
        try:
            await realtime_refresh_task
        except asyncio.CancelledError:
            pass


@app.get("/healthz")
def read_healthz():
    static_status = carbon_eye_static_data_status()
    return {
        "service": "carbon-eye-api",
        "version": "2.0.0",
        "status": "ok" if static_status["status"] == "ok" else "degraded",
        "static_data_status": static_status,
        "website_mode": "full" if database_initialized else "carbon-eye-only",
    }


@app.get("/readyz")
def read_website_readyz():
    if not database_initialized:
        raise HTTPException(status_code=503, detail="完整网站数据库尚未初始化")
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            if not db.query(Profile).first():
                raise HTTPException(status_code=503, detail="尚未迁移个人资料")
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="持久化数据库暂不可用") from None
    return {"status": "ok", "service": "personal-website", "database": "ok"}


@app.get("/")
def read_root():
    return {"message": "个人网站后端启动成功"}


@app.get("/api/carbon-eye/overview")
def read_carbon_eye_overview():
    return load_carbon_eye_json("overview.json")


@app.get("/api/carbon-eye/monthly-trends")
def read_carbon_eye_monthly_trends():
    return load_carbon_eye_json("monthly_trends.json")


@app.get("/api/carbon-eye/weather-2024")
def read_carbon_eye_weather_2024():
    return load_carbon_eye_json("weather_2024.json")


@app.get("/api/carbon-eye/carbon-emissions")
def read_carbon_eye_carbon_emissions():
    return load_carbon_eye_json("carbon_emissions.json")


@app.get("/api/carbon-eye/warnings")
def read_carbon_eye_warnings():
    return load_carbon_eye_json("warnings.json")


@app.get("/api/carbon-eye/daily-cases")
def read_carbon_eye_daily_cases():
    return load_carbon_eye_json("daily_cases.json")


@app.get("/api/carbon-eye/methodology")
def read_carbon_eye_methodology():
    return load_carbon_eye_json("methodology.json")


@app.get("/api/carbon-eye/realtime-aqi")
def read_carbon_eye_realtime_aqi():
    return get_realtime_aqi()


@app.get("/api/carbon-eye/park-carbon-estimate")
def read_carbon_eye_park_carbon_estimate():
    return load_carbon_eye_json("park_electricity_emissions.json")


@app.get("/api/carbon-eye/cdci")
def read_carbon_eye_cdci():
    return load_carbon_eye_json("cdci.json")


@app.get("/api/carbon-eye/industry-profile")
def read_carbon_eye_industry_profile():
    return load_carbon_eye_json("industry_profile.json")


@app.get("/api/carbon-eye/governance-explanation")
def read_carbon_eye_governance_explanation():
    return load_carbon_eye_json("governance_explanation.json")


@app.get("/api/carbon-eye/health")
def read_carbon_eye_health():
    return read_healthz()


@app.get("/api/carbon-eye/park-electricity-emissions")
def read_carbon_eye_park_electricity_emissions():
    return load_carbon_eye_json("park_electricity_emissions.json")


@app.get("/api/carbon-eye/economic-carbon-intensity")
def read_carbon_eye_economic_carbon_intensity():
    return load_carbon_eye_json("sip_economic_carbon_intensity.json")


@app.get("/api/carbon-eye/park-environment-snapshot")
def read_carbon_eye_park_environment_snapshot():
    return load_carbon_eye_json("park_environment_snapshot.json")


@app.get("/api/carbon-eye/weather-long-term")
def read_carbon_eye_weather_long_term():
    return load_carbon_eye_json("weather/weather_park_monthly.json")


@app.get("/api/carbon-eye/weather-correlations")
def read_carbon_eye_weather_correlations():
    return load_carbon_eye_json("weather/weather_air_correlations.json")


@app.get("/api/carbon-eye/cdci-sensitivity")
def read_carbon_eye_cdci_sensitivity():
    return load_carbon_eye_json("cdci_sensitivity.json")


@app.get("/api/carbon-eye/data-quality")
def read_carbon_eye_data_quality():
    return load_carbon_eye_json("data_quality.json")


@app.get("/api/carbon-eye/sources")
def read_carbon_eye_sources():
    return load_carbon_eye_json("source_registry.json")


@app.get("/api/profile")
def read_profile(db: Session = Depends(get_db)):
    try:
        profile = db.query(Profile).order_by(Profile.id.asc()).first()
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="数据库暂不可用，请稍后重试") from None
    if not profile:
        raise HTTPException(status_code=404, detail="profile 表中还没有个人信息，请先执行 sql/init.sql")
    return {
        "id": profile.id,
        "name": profile.name,
        "title": profile.title,
        "description": profile.description,
        "github": profile.github,
        "email": profile.email,
    }


@app.get("/api/yulu/random")
def read_random_yulu(yname: str = "fcx", exclude_id: Optional[int] = None, db: Session = Depends(get_db)):
    yulu_name = clean_text(yname, "语录人物标识", 80)
    query = db.query(Yulu).filter(Yulu.yname == yulu_name)
    total = query.count()
    if total == 0:
        raise HTTPException(status_code=404, detail=f"{yulu_name} 暂无语录，请先向 yulu 表插入数据")

    candidate_query = query
    if exclude_id is not None and total > 1:
        candidate_query = query.filter(Yulu.id != exclude_id)

    candidate_total = candidate_query.count()
    if candidate_total == 0:
        candidate_query = query
        candidate_total = total

    offset = random.randint(0, candidate_total - 1)
    yulu = candidate_query.order_by(Yulu.id.asc()).offset(offset).first()
    return yulu_to_dict(yulu)


@app.post("/api/secure-geometry/calculate")
def calculate_secure_geometry_api(data: SecureGeometryRequest):
    try:
        return calculate_secure_geometry(data.relation, data.alice, data.bob)
    except SecureGeometryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/novels")
def read_novels(q: str = "", db: Session = Depends(get_db), authorization: Optional[str] = Header(default=None)):
    user = optional_user_from_header(db, authorization)
    query = db.query(Novel1)
    if q.strip():
        keyword = f"%{q.strip()}%"
        query = query.filter(or_(Novel1.xs_name.like(keyword), Novel1.xs_content.like(keyword)))
    novels = query.order_by(Novel1.xs_id.asc()).all()
    return [novel_to_dict(db, novel, user) for novel in novels]


@app.get("/api/novels/{novel_id}")
def read_novel_detail(novel_id: int, db: Session = Depends(get_db), authorization: Optional[str] = Header(default=None)):
    user = optional_user_from_header(db, authorization)
    novel = ensure_novel_exists(db, novel_id)
    return {"novel": novel_to_dict(db, novel, user)}


@app.post("/api/auth/register")
def register_user(data: RegisterRequest, db: Session = Depends(get_db)):
    username = clean_text(data.username, "用户名", 30)
    password = validate_new_password(data.password)
    if username.lower() in {"admin", "root"}:
        raise HTTPException(status_code=400, detail="该用户名保留给管理员，请使用其他用户名")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(username=username, password_hash=hash_password(password), role="user", is_muted=False, is_deleted=False)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "注册成功", "user": user_to_dict(user)}


@app.post("/api/auth/login")
def login_user(data: LoginRequest, db: Session = Depends(get_db)):
    username = clean_text(data.username, "用户名", 30)
    password = data.password
    if len(password) > 80:
        raise HTTPException(status_code=400, detail="密码不能超过 80 个字符")
    user = db.query(User).filter(User.username == username).first()
    if not user or user.is_deleted or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token_value = secrets.token_urlsafe(32)
    token = AuthToken(token=token_value, user_id=user.id, expires_at=now_utc() + timedelta(days=TOKEN_DAYS))
    db.add(token)
    db.commit()
    return {"message": "登录成功", "token": token_value, "user": user_to_dict(user)}


@app.get("/api/auth/me")
def read_me(current_user: User = Depends(get_current_user)):
    return {"user": user_to_dict(current_user)}


@app.post("/api/auth/logout")
def logout_user(authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    if authorization and authorization.startswith("Bearer "):
        token_value = authorization.replace("Bearer ", "", 1).strip()
        token = db.query(AuthToken).filter(AuthToken.token == token_value).first()
        if token:
            db.delete(token)
            db.commit()
    return {"message": "已退出登录"}


@app.get("/api/admin/dashboard")
def admin_dashboard(db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    return {
        "users": db.query(User).filter(User.is_deleted == False).count(),
        "muted_users": db.query(User).filter(User.is_muted == True, User.is_deleted == False).count(),
        "posts": db.query(Post).filter(Post.is_deleted == False).count(),
        "deleted_posts": db.query(Post).filter(Post.is_deleted == True).count(),
        "post_comments": db.query(PostComment).filter(PostComment.is_deleted == False).count(),
        "articles": db.query(Article).filter(Article.is_deleted == False).count(),
        "draft_articles": db.query(Article).filter(Article.status == "draft", Article.is_deleted == False).count(),
        "article_comments": db.query(ArticleComment).filter(ArticleComment.is_deleted == False).count(),
        "messages": db.query(Message).filter(Message.is_deleted == False).count(),
        "novels": db.query(Novel1).count(),
    }


@app.get("/api/admin/users")
def admin_read_users(db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    users = db.query(User).order_by(User.id.asc()).all()
    return [user_to_dict(user) for user in users]


@app.post("/api/admin/users")
def admin_create_user(data: AdminCreateUserRequest, db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    username = clean_text(data.username, "用户名", 30)
    password = validate_new_password(data.password, data.role)
    if data.role == "admin" and not verify_password(data.admin_password or "", admin_user.password_hash):
        raise HTTPException(status_code=403, detail="创建管理员前请确认当前管理员密码")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(username=username, password_hash=hash_password(password), role=data.role, is_muted=False, is_deleted=False)
    db.add(user)
    db.flush()
    record_permission_change(db, admin_user, user, None, "create_user")
    db.commit()
    db.refresh(user)
    return {"message": "用户创建成功", "user": user_to_dict(user)}


@app.put("/api/admin/users/{user_id}/role")
def admin_update_user_role(user_id: int, data: RoleUpdateRequest, db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    # Serialize changes to administrators on PostgreSQL, then recheck the actor:
    # two administrators must not concurrently demote one another to zero admins.
    admins = db.query(User).filter(User.role == "admin", User.is_deleted == False).order_by(User.id).with_for_update().populate_existing().all()
    actor = next((user for user in admins if user.id == admin_user.id and not user.is_muted), None)
    if actor is None:
        raise HTTPException(status_code=403, detail="管理员权限已失效，请重新登录")
    if not verify_password(data.admin_password, actor.password_hash):
        raise HTTPException(status_code=403, detail="当前管理员密码不正确")
    target = db.query(User).filter(User.id == user_id).with_for_update().populate_existing().first()
    if not target or target.is_deleted:
        raise HTTPException(status_code=404, detail="用户不存在或已删除")
    if target.id == actor.id:
        raise HTTPException(status_code=403, detail="不能修改自己的角色，请由另一位管理员操作")
    old_role = target.role
    if old_role == data.role:
        return {"message": "角色未变更", "user": user_to_dict(target)}
    if old_role == "admin" and data.role != "admin" and sum(not user.is_muted for user in admins) <= 1:
        raise HTTPException(status_code=409, detail="必须保留至少一个可用管理员")
    if data.role == "admin":
        if target.is_muted:
            raise HTTPException(status_code=400, detail="请先解除禁言再提升为管理员")
        if data.new_password is None:
            raise HTTPException(status_code=400, detail="提升为管理员时必须设置至少 12 位的新密码")
        target.password_hash = hash_password(validate_new_password(data.new_password, "admin"))
    target.role = data.role
    revoke_user_tokens(db, target.id)
    record_permission_change(db, actor, target, old_role)
    db.commit()
    db.refresh(target)
    return {"message": "权限已更新，该用户需要重新登录", "user": user_to_dict(target)}


@app.get("/api/admin/permission-audit")
def admin_permission_audit(page: int = 1, page_size: int = 20, db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    query = db.query(PermissionAudit).order_by(PermissionAudit.id.desc())
    return paged_response(query, page, page_size, lambda row: {
        "id": row.id, "actor": get_username(db, row.actor_user_id), "target": get_username(db, row.target_user_id),
        "action": row.action, "old_role": row.old_role, "new_role": row.new_role, "created_at": format_time(row.created_at),
    })


@app.put("/api/admin/users/{user_id}")
def admin_update_user(user_id: int, data: AdminUpdateUserRequest, db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.role == "admin":
        raise HTTPException(status_code=403, detail="不能在这里修改管理员账号")
    if data.username is not None:
        username = clean_text(data.username, "用户名", 30)
        exists = db.query(User).filter(User.username == username, User.id != user_id).first()
        if exists:
            raise HTTPException(status_code=400, detail="用户名已存在")
        user.username = username
    if data.password is not None and data.password.strip():
        user.password_hash = hash_password(validate_new_password(data.password, user.role))
        revoke_user_tokens(db, user.id)
    if data.is_muted is not None:
        if user.is_muted != data.is_muted:
            revoke_user_tokens(db, user.id)
        user.is_muted = data.is_muted
    db.commit()
    db.refresh(user)
    return {"message": "用户更新成功", "user": user_to_dict(user)}


@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: int, db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.role == "admin":
        raise HTTPException(status_code=403, detail="不能删除管理员账号")
    user.is_deleted = True
    revoke_user_tokens(db, user.id)
    db.commit()
    return {"message": "用户已软删除"}


@app.put("/api/admin/users/{user_id}/mute")
def admin_mute_user(user_id: int, db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.role == "admin":
        raise HTTPException(status_code=404, detail="普通用户不存在")
    user.is_muted = True
    revoke_user_tokens(db, user.id)
    db.commit()
    return {"message": "已禁言", "user": user_to_dict(user)}


@app.put("/api/admin/users/{user_id}/unmute")
def admin_unmute_user(user_id: int, db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.role == "admin":
        raise HTTPException(status_code=404, detail="普通用户不存在")
    user.is_muted = False
    revoke_user_tokens(db, user.id)
    db.commit()
    return {"message": "已解除禁言", "user": user_to_dict(user)}


@app.get("/api/posts")
def read_posts(page: int = 1, page_size: int = 9, sort: str = "latest", q: str = "", db: Session = Depends(get_db), authorization: Optional[str] = Header(default=None)):
    user = optional_user_from_header(db, authorization)
    query = db.query(Post).filter(Post.is_deleted == False)
    if q.strip():
        keyword = f"%{q.strip()}%"
        query = query.filter(or_(Post.title.like(keyword), Post.content.like(keyword)))
    query = query.order_by(Post.created_at.asc() if sort == "oldest" else Post.created_at.desc(), Post.id.desc())
    return paged_response(query, page, page_size, lambda post: post_to_dict(db, post, user))


@app.post("/api/posts")
def create_post(data: PostCreateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_publishing_user)):
    ensure_not_muted(current_user)
    title = clean_text(data.title, "帖子标题", 80)
    content = clean_text(data.content, "帖子内容", 5000)
    post = Post(user_id=current_user.id, title=title, content=content)
    db.add(post)
    db.commit()
    db.refresh(post)
    return {"message": "发帖成功", "post": post_to_dict(db, post, current_user)}


@app.get("/api/posts/{post_id}")
def read_post_detail(post_id: int, db: Session = Depends(get_db), authorization: Optional[str] = Header(default=None)):
    user = optional_user_from_header(db, authorization)
    post = ensure_post_exists(db, post_id, admin_mode=bool(user and user.role == "admin"))
    comments = db.query(PostComment).filter(PostComment.post_id == post.id, PostComment.is_deleted == False).order_by(PostComment.created_at.asc(), PostComment.id.asc()).all()
    return {"post": post_to_dict(db, post, user), "comments": [post_comment_to_dict(db, comment) for comment in comments]}


@app.post("/api/posts/{post_id}/comments")
def create_post_comment(post_id: int, data: CommentCreateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_publishing_user)):
    ensure_not_muted(current_user)
    post = ensure_post_exists(db, post_id)
    content = clean_text(data.content, "评论内容", 1000)
    comment = PostComment(post_id=post.id, user_id=current_user.id, content=content)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return {"message": "评论成功", "comment": post_comment_to_dict(db, comment)}


@app.post("/api/posts/{post_id}/like")
def like_post(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    post = ensure_post_exists(db, post_id)
    exists = db.query(PostLike).filter(PostLike.post_id == post.id, PostLike.user_id == current_user.id).first()
    if not exists:
        db.add(PostLike(post_id=post.id, user_id=current_user.id))
        db.commit()
    return {"message": "已点赞", "post": post_to_dict(db, post, current_user)}


@app.delete("/api/posts/{post_id}/like")
def unlike_post(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    post = ensure_post_exists(db, post_id)
    exists = db.query(PostLike).filter(PostLike.post_id == post.id, PostLike.user_id == current_user.id).first()
    if exists:
        db.delete(exists)
        db.commit()
    return {"message": "已取消点赞", "post": post_to_dict(db, post, current_user)}


@app.get("/api/articles/categories")
def read_article_categories(db: Session = Depends(get_db)):
    rows = db.query(Article.category).filter(Article.is_deleted == False, Article.status == "published").distinct().order_by(Article.category.asc()).all()
    return [row[0] for row in rows if row[0]]


@app.get("/api/articles")
def read_articles(page: int = 1, page_size: int = 9, sort: str = "latest", q: str = "", category: str = "", tag: str = "", db: Session = Depends(get_db), authorization: Optional[str] = Header(default=None)):
    user = optional_user_from_header(db, authorization)
    query = db.query(Article).filter(Article.is_deleted == False, Article.status == "published")
    if q.strip():
        keyword = f"%{q.strip()}%"
        query = query.filter(or_(Article.title.like(keyword), Article.summary.like(keyword), Article.content.like(keyword)))
    if category.strip():
        query = query.filter(Article.category == category.strip())
    if tag.strip():
        query = query.filter(Article.tags.like(f"%{tag.strip()}%"))
    if sort == "oldest":
        query = query.order_by(Article.is_pinned.desc(), Article.created_at.asc(), Article.id.desc())
    else:
        query = query.order_by(Article.is_pinned.desc(), Article.created_at.desc(), Article.id.desc())
    return paged_response(query, page, page_size, lambda article: article_to_dict(db, article, user))


@app.post("/api/articles")
def create_article(data: ArticleCreateRequest, db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    title = clean_text(data.title, "文章标题", 100)
    summary = clean_text(data.summary, "文章摘要", 255, allow_empty=True)
    category = clean_text(data.category, "文章分类", 80) or "随笔"
    tags = clean_text(data.tags, "文章标签", 255, allow_empty=True)
    content = clean_text(data.content, "文章内容", 20000)
    status = clean_status(data.status, ARTICLE_STATUSES, "文章状态")
    article = Article(title=title, summary=summary, category=category, tags=tags, content=content, status=status, is_pinned=data.is_pinned)
    db.add(article)
    db.commit()
    db.refresh(article)
    return {"message": "文章保存成功", "article": article_to_dict(db, article, admin_user)}


@app.get("/api/articles/{article_id}")
def read_article_detail(article_id: int, db: Session = Depends(get_db), authorization: Optional[str] = Header(default=None)):
    user = optional_user_from_header(db, authorization)
    article = ensure_article_exists(db, article_id, user=user)
    comments = db.query(ArticleComment).filter(ArticleComment.article_id == article.id, ArticleComment.is_deleted == False).order_by(ArticleComment.created_at.asc(), ArticleComment.id.asc()).all()
    return {"article": article_to_dict(db, article, user), "comments": [article_comment_to_dict(db, comment) for comment in comments]}


@app.post("/api/articles/{article_id}/comments")
def create_article_comment(article_id: int, data: CommentCreateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_publishing_user)):
    ensure_not_muted(current_user)
    article = ensure_article_exists(db, article_id, user=current_user)
    content = clean_text(data.content, "评论内容", 1000)
    comment = ArticleComment(article_id=article.id, user_id=current_user.id, content=content)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return {"message": "评论成功", "comment": article_comment_to_dict(db, comment)}


@app.post("/api/articles/{article_id}/like")
def like_article(article_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    article = ensure_article_exists(db, article_id, user=current_user)
    exists = db.query(ArticleLike).filter(ArticleLike.article_id == article.id, ArticleLike.user_id == current_user.id).first()
    if not exists:
        db.add(ArticleLike(article_id=article.id, user_id=current_user.id))
        db.commit()
    return {"message": "已点赞", "article": article_to_dict(db, article, current_user)}


@app.delete("/api/articles/{article_id}/like")
def unlike_article(article_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    article = ensure_article_exists(db, article_id, user=current_user)
    exists = db.query(ArticleLike).filter(ArticleLike.article_id == article.id, ArticleLike.user_id == current_user.id).first()
    if exists:
        db.delete(exists)
        db.commit()
    return {"message": "已取消点赞", "article": article_to_dict(db, article, current_user)}


@app.post("/api/articles/{article_id}/favorite")
def favorite_article(article_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    article = ensure_article_exists(db, article_id, user=current_user)
    exists = db.query(ArticleFavorite).filter(ArticleFavorite.article_id == article.id, ArticleFavorite.user_id == current_user.id).first()
    if not exists:
        db.add(ArticleFavorite(article_id=article.id, user_id=current_user.id))
        db.commit()
    return {"message": "已收藏", "article": article_to_dict(db, article, current_user)}


@app.delete("/api/articles/{article_id}/favorite")
def unfavorite_article(article_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    article = ensure_article_exists(db, article_id, user=current_user)
    exists = db.query(ArticleFavorite).filter(ArticleFavorite.article_id == article.id, ArticleFavorite.user_id == current_user.id).first()
    if exists:
        db.delete(exists)
        db.commit()
    return {"message": "已取消收藏", "article": article_to_dict(db, article, current_user)}


@app.get("/api/admin/articles")
def admin_read_articles(page: int = 1, page_size: int = 10, sort: str = "latest", status: str = "", q: str = "", db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    query = db.query(Article)
    if status.strip():
        if status == "deleted":
            query = query.filter(Article.is_deleted == True)
        else:
            query = query.filter(Article.status == status.strip(), Article.is_deleted == False)
    if q.strip():
        keyword = f"%{q.strip()}%"
        query = query.filter(or_(Article.title.like(keyword), Article.summary.like(keyword), Article.content.like(keyword)))
    query = query.order_by(Article.is_pinned.desc(), Article.created_at.asc() if sort == "oldest" else Article.created_at.desc(), Article.id.desc())
    return paged_response(query, page, page_size, lambda article: article_to_dict(db, article, admin_user))


@app.put("/api/admin/articles/{article_id}")
def admin_update_article(article_id: int, data: ArticleCreateRequest, db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    article = ensure_article_exists(db, article_id, user=admin_user, admin_mode=True)
    article.title = clean_text(data.title, "文章标题", 100)
    article.summary = clean_text(data.summary, "文章摘要", 255, allow_empty=True)
    article.category = clean_text(data.category, "文章分类", 80) or "随笔"
    article.tags = clean_text(data.tags, "文章标签", 255, allow_empty=True)
    article.content = clean_text(data.content, "文章内容", 20000)
    article.status = clean_status(data.status, ARTICLE_STATUSES, "文章状态")
    article.is_pinned = data.is_pinned
    db.commit()
    db.refresh(article)
    return {"message": "文章更新成功", "article": article_to_dict(db, article, admin_user)}


@app.delete("/api/admin/articles/{article_id}")
def admin_delete_article(article_id: int, db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    article = ensure_article_exists(db, article_id, user=admin_user, admin_mode=True)
    article.is_deleted = True
    article.deleted_at = now_utc()
    db.commit()
    return {"message": "文章已软删除"}


@app.put("/api/admin/articles/{article_id}/status")
def admin_update_article_status(article_id: int, data: ArticleStatusRequest, db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    article = ensure_article_exists(db, article_id, user=admin_user, admin_mode=True)
    article.status = clean_status(data.status, ARTICLE_STATUSES, "文章状态")
    db.commit()
    return {"message": "文章状态已更新", "article": article_to_dict(db, article, admin_user)}


@app.put("/api/admin/articles/{article_id}/pin")
def admin_update_article_pin(article_id: int, data: ArticlePinRequest, db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    article = ensure_article_exists(db, article_id, user=admin_user, admin_mode=True)
    article.is_pinned = data.is_pinned
    db.commit()
    return {"message": "文章置顶状态已更新", "article": article_to_dict(db, article, admin_user)}


@app.get("/api/admin/posts")
def admin_read_posts(page: int = 1, page_size: int = 10, q: str = "", db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    query = db.query(Post)
    if q.strip():
        keyword = f"%{q.strip()}%"
        query = query.filter(or_(Post.title.like(keyword), Post.content.like(keyword)))
    query = query.order_by(Post.created_at.desc(), Post.id.desc())
    return paged_response(query, page, page_size, lambda post: post_to_dict(db, post, admin_user))


@app.delete("/api/admin/posts/{post_id}")
def admin_delete_post(post_id: int, db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    post = ensure_post_exists(db, post_id, admin_mode=True)
    post.is_deleted = True
    post.deleted_at = now_utc()
    db.commit()
    return {"message": "帖子已软删除"}


@app.get("/api/admin/comments")
def admin_read_comments(page: int = 1, page_size: int = 10, comment_type: str = "all", db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    comments = []
    if comment_type in ("all", "post"):
        comments.extend([post_comment_to_dict(db, comment) for comment in db.query(PostComment).order_by(PostComment.created_at.desc()).all()])
    if comment_type in ("all", "article"):
        comments.extend([article_comment_to_dict(db, comment) for comment in db.query(ArticleComment).order_by(ArticleComment.created_at.desc()).all()])
    comments.sort(key=lambda item: item["created_at"], reverse=True)
    safe_page, safe_page_size = normalize_page(page, page_size)
    total = len(comments)
    start = (safe_page - 1) * safe_page_size
    return {"items": comments[start:start + safe_page_size], "total": total, "page": safe_page, "page_size": safe_page_size, "pages": max(1, math.ceil(total / safe_page_size))}


@app.delete("/api/admin/comments/{comment_type}/{comment_id}")
def admin_delete_comment(comment_type: str, comment_id: int, db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    if comment_type == "post":
        comment = db.query(PostComment).filter(PostComment.id == comment_id).first()
    elif comment_type == "article":
        comment = db.query(ArticleComment).filter(ArticleComment.id == comment_id).first()
    else:
        raise HTTPException(status_code=400, detail="评论类型不正确")
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")
    comment.is_deleted = True
    comment.deleted_at = now_utc()
    db.commit()
    return {"message": "评论已软删除"}


@app.post("/api/novels/{novel_id}/favorite")
def favorite_novel(novel_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    novel = ensure_novel_exists(db, novel_id)
    exists = db.query(NovelFavorite).filter(NovelFavorite.novel_id == novel.xs_id, NovelFavorite.user_id == current_user.id).first()
    if not exists:
        db.add(NovelFavorite(novel_id=novel.xs_id, user_id=current_user.id))
        db.commit()
    return {"message": "已收藏", "novel": novel_to_dict(db, novel, current_user)}


@app.delete("/api/novels/{novel_id}/favorite")
def unfavorite_novel(novel_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    novel = ensure_novel_exists(db, novel_id)
    exists = db.query(NovelFavorite).filter(NovelFavorite.novel_id == novel.xs_id, NovelFavorite.user_id == current_user.id).first()
    if exists:
        db.delete(exists)
        db.commit()
    return {"message": "已取消收藏", "novel": novel_to_dict(db, novel, current_user)}


@app.get("/api/novels/{novel_id}/progress")
def read_novel_progress(novel_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_novel_exists(db, novel_id)
    progress = db.query(ReadingProgress).filter(ReadingProgress.novel_id == novel_id, ReadingProgress.user_id == current_user.id).first()
    if not progress:
        return {"progress": 0, "font_size": 18, "theme": "dark"}
    return {"progress": progress.progress, "font_size": progress.font_size, "theme": progress.theme}


@app.put("/api/novels/{novel_id}/progress")
def update_novel_progress(novel_id: int, data: ReadingProgressRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_novel_exists(db, novel_id)
    progress_value = max(0, min(100, int(data.progress)))
    font_size = max(14, min(26, int(data.font_size)))
    theme = data.theme if data.theme in ["dark", "light"] else "dark"
    progress = db.query(ReadingProgress).filter(ReadingProgress.novel_id == novel_id, ReadingProgress.user_id == current_user.id).first()
    if not progress:
        progress = ReadingProgress(novel_id=novel_id, user_id=current_user.id, progress=progress_value, font_size=font_size, theme=theme)
        db.add(progress)
    else:
        progress.progress = progress_value
        progress.font_size = font_size
        progress.theme = theme
    db.commit()
    return {"message": "阅读进度已保存", "progress": progress_value, "font_size": font_size, "theme": theme}


@app.get("/api/messages")
def read_messages(page: int = 1, page_size: int = 10, db: Session = Depends(get_db)):
    query = db.query(Message).filter(Message.is_deleted == False, Message.status == "published").order_by(Message.created_at.desc(), Message.id.desc())
    return paged_response(query, page, page_size, lambda message: message_to_dict(db, message))


@app.post("/api/messages")
def create_message(data: MessageCreateRequest, db: Session = Depends(get_db), user: User = Depends(get_publishing_user)):
    content = clean_text(data.content, "留言内容", 1000)
    nickname = user.username if user else clean_text(data.nickname, "昵称", 40)
    message = Message(user_id=user.id if user else None, nickname=nickname, content=content, status="published")
    db.add(message)
    db.commit()
    db.refresh(message)
    return {"message": "留言成功", "item": message_to_dict(db, message)}


@app.get("/api/admin/messages")
def admin_read_messages(page: int = 1, page_size: int = 10, status: str = "", db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    query = db.query(Message)
    if status == "deleted":
        query = query.filter(Message.is_deleted == True)
    elif status.strip():
        query = query.filter(Message.status == status.strip(), Message.is_deleted == False)
    query = query.order_by(Message.created_at.desc(), Message.id.desc())
    return paged_response(query, page, page_size, lambda message: message_to_dict(db, message))


@app.put("/api/admin/messages/{message_id}/status")
def admin_update_message_status(message_id: int, data: MessageStatusRequest, db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="留言不存在")
    message.status = clean_status(data.status, MESSAGE_STATUSES, "留言状态")
    db.commit()
    return {"message": "留言状态已更新", "item": message_to_dict(db, message)}


@app.delete("/api/admin/messages/{message_id}")
def admin_delete_message(message_id: int, db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="留言不存在")
    message.is_deleted = True
    message.deleted_at = now_utc()
    db.commit()
    return {"message": "留言已软删除"}


@app.get("/api/me/summary")
def read_my_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {
        "user": user_to_dict(current_user),
        "posts": db.query(Post).filter(Post.user_id == current_user.id, Post.is_deleted == False).count(),
        "post_comments": db.query(PostComment).filter(PostComment.user_id == current_user.id, PostComment.is_deleted == False).count(),
        "article_comments": db.query(ArticleComment).filter(ArticleComment.user_id == current_user.id, ArticleComment.is_deleted == False).count(),
        "article_favorites": db.query(ArticleFavorite).filter(ArticleFavorite.user_id == current_user.id).count(),
        "novel_favorites": db.query(NovelFavorite).filter(NovelFavorite.user_id == current_user.id).count(),
    }


@app.get("/api/me/posts")
def read_my_posts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    posts = db.query(Post).filter(Post.user_id == current_user.id, Post.is_deleted == False).order_by(Post.created_at.desc(), Post.id.desc()).all()
    return [post_to_dict(db, post, current_user) for post in posts]


@app.get("/api/me/comments")
def read_my_comments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    post_comments = db.query(PostComment).filter(PostComment.user_id == current_user.id, PostComment.is_deleted == False).order_by(PostComment.created_at.desc(), PostComment.id.desc()).all()
    article_comments = db.query(ArticleComment).filter(ArticleComment.user_id == current_user.id, ArticleComment.is_deleted == False).order_by(ArticleComment.created_at.desc(), ArticleComment.id.desc()).all()
    return {
        "post_comments": [post_comment_to_dict(db, comment) for comment in post_comments],
        "article_comments": [article_comment_to_dict(db, comment) for comment in article_comments],
    }


@app.get("/api/me/favorites")
def read_my_favorites(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    article_favorites = db.query(ArticleFavorite).filter(ArticleFavorite.user_id == current_user.id).order_by(ArticleFavorite.created_at.desc()).all()
    novel_favorites = db.query(NovelFavorite).filter(NovelFavorite.user_id == current_user.id).order_by(NovelFavorite.created_at.desc()).all()
    articles = []
    for favorite in article_favorites:
        article_query = db.query(Article).filter(Article.id == favorite.article_id, Article.is_deleted == False)
        if current_user.role != "admin":
            article_query = article_query.filter(Article.status == "published")
        article = article_query.first()
        if article:
            articles.append(article_to_dict(db, article, current_user))
    novels = [novel_to_dict(db, ensure_novel_exists(db, favorite.novel_id), current_user) for favorite in novel_favorites]
    return {"articles": articles, "novels": novels}


@app.put("/api/me/password")
def update_my_password(data: PasswordRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    old_password = data.old_password
    new_password = validate_new_password(data.new_password, current_user.role)
    if not verify_password(old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码不正确")
    current_user.password_hash = hash_password(new_password)
    revoke_user_tokens(db, current_user.id)
    db.commit()
    return {"message": "密码修改成功，请重新登录"}
