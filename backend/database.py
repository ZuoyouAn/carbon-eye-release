from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from db_config import database_engine_options, normalize_database_url


load_dotenv()

DATABASE_URL = normalize_database_url(os.getenv("DATABASE_URL") or "sqlite:///./carbon_eye_demo.db")
IS_SQLITE = DATABASE_URL.get_backend_name() == "sqlite"
engine_kwargs = database_engine_options(DATABASE_URL)

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
