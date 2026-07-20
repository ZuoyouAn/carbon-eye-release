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
from models import Profile
from models import ReadingProgress
from models import User
from models import Yulu
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
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class PasswordRequest(BaseModel):
    old_password: str
    new_password: str


class AdminCreateUserRequest(BaseModel):
    username: str
    password: str


class AdminUpdateUserRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    is_muted: Optional[bool] = None


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
    return user


def get_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以操作")
    return current_user


def ensure_not_muted(user: User):
    if user.is_muted:
        raise HTTPException(status_code=403, detail="你已被禁言，不能发布内容")


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
    row = connection.execute(text(f"SHOW COLUMNS FROM {table_name} LIKE :column_name"), {"column_name": column_name}).fetchone()
    if not row:
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
        connection.execute(text("ALTER TABLE articles ALTER category SET DEFAULT 'Essay'"))
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


@app.on_event("startup")
async def startup_event():
    global realtime_refresh_task, realtime_refresh_stop_event
    if os.getenv("CARBON_EYE_REALTIME_SCHEDULER", "").strip().lower() in {"1", "true", "yes"}:
        realtime_refresh_stop_event = asyncio.Event()
        realtime_refresh_task = asyncio.create_task(refresh_realtime_aqi_hourly(realtime_refresh_stop_event))
    if os.getenv("CARBON_EYE_STANDALONE", "").strip().lower() in {"1", "true", "yes"}:
        return
    try:
        Base.metadata.create_all(bind=engine)
        upgrade_existing_schema()
        db = SessionLocal()
        try:
            admin = db.query(User).filter(User.username == "root").first()
            if not admin:
                bootstrap_password = os.getenv("INITIAL_ADMIN_PASSWORD")
                if not bootstrap_password:
                    return
                admin = User(username="root", password_hash=hash_password(bootstrap_password), role="admin", is_muted=False, is_deleted=False)
                db.add(admin)
                db.commit()
                db.refresh(admin)
            else:
                admin.role = "admin"
                admin.is_deleted = False
                admin.is_muted = False
                db.commit()
                db.refresh(admin)
            seed_demo_data(db, admin)
        finally:
            db.close()
    except SQLAlchemyError as exc:
        print(f"数据库启动初始化失败，数据库功能暂不可用；碳眼只读接口仍可用：{exc}")


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
    }


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
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"数据库连接或查询失败：{exc}") from exc
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
    password = clean_text(data.password, "密码", 80)
    if len(password) < 3:
        raise HTTPException(status_code=400, detail="密码至少需要 3 个字符")
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
    password = clean_text(data.password, "密码", 80)
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
    password = clean_text(data.password, "密码", 80)
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(username=username, password_hash=hash_password(password), role="user", is_muted=False, is_deleted=False)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "用户创建成功", "user": user_to_dict(user)}


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
        user.password_hash = hash_password(clean_text(data.password, "密码", 80))
    if data.is_muted is not None:
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
    db.commit()
    return {"message": "用户已软删除"}


@app.put("/api/admin/users/{user_id}/mute")
def admin_mute_user(user_id: int, db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.role == "admin":
        raise HTTPException(status_code=404, detail="普通用户不存在")
    user.is_muted = True
    db.commit()
    return {"message": "已禁言", "user": user_to_dict(user)}


@app.put("/api/admin/users/{user_id}/unmute")
def admin_unmute_user(user_id: int, db: Session = Depends(get_db), admin_user: User = Depends(get_admin_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.role == "admin":
        raise HTTPException(status_code=404, detail="普通用户不存在")
    user.is_muted = False
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
def create_post(data: PostCreateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
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
def create_post_comment(post_id: int, data: CommentCreateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
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
def create_article_comment(article_id: int, data: CommentCreateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
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
def create_message(data: MessageCreateRequest, db: Session = Depends(get_db), authorization: Optional[str] = Header(default=None)):
    user = optional_user_from_header(db, authorization)
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
        article = db.query(Article).filter(Article.id == favorite.article_id, Article.is_deleted == False).first()
        if article:
            articles.append(article_to_dict(db, article, current_user))
    novels = [novel_to_dict(db, ensure_novel_exists(db, favorite.novel_id), current_user) for favorite in novel_favorites]
    return {"articles": articles, "novels": novels}


@app.put("/api/me/password")
def update_my_password(data: PasswordRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    old_password = clean_text(data.old_password, "旧密码", 80)
    new_password = clean_text(data.new_password, "新密码", 80)
    if len(new_password) < 3:
        raise HTTPException(status_code=400, detail="新密码至少需要 3 个字符")
    if not verify_password(old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码不正确")
    current_user.password_hash = hash_password(new_password)
    db.commit()
    return {"message": "密码修改成功"}
