"""Shared database settings, without loading secrets or opening connections."""
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool


def normalize_database_url(value: str):
    url = make_url(value)
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+psycopg")
    return url


def database_engine_options(url):
    options = {"pool_pre_ping": True, "hide_parameters": True}
    if url.get_backend_name() == "sqlite":
        options["connect_args"] = {"check_same_thread": False}
    elif url.get_backend_name() == "postgresql":
        # Release connections after requests so Neon can scale to zero. No
        # persistent prepared statements when connecting through PgBouncer.
        options["poolclass"] = NullPool
        options["connect_args"] = {"connect_timeout": 10, "prepare_threshold": None}
        if "sslmode" not in url.query:
            options["connect_args"]["sslmode"] = "require"
    elif url.get_backend_name() == "mysql":
        options["connect_args"] = {"connect_timeout": 10}
    return options
