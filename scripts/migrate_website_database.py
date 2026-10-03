"""Copy the website into an EMPTY persistent database. Dry-run by default.

Secrets are read from ignored dotenv files; never supplied on the command line.
The source is SELECT-only. Active login tokens are deliberately not copied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from dotenv import dotenv_values
from sqlalchemy import Boolean, Column, Integer, MetaData, Table, create_engine, func, inspect, select, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from db_config import database_engine_options, normalize_database_url
from models import Base


def configured_engine(env_file):
    value = dotenv_values(env_file).get("DATABASE_URL")
    if not value:
        raise ValueError("Configuration file is missing DATABASE_URL")
    url = normalize_database_url(value)
    return create_engine(url, **database_engine_options(url))


def database_identity(engine):
    url = engine.url
    if engine.dialect.name == "sqlite":
        database = str(Path(url.database).resolve()) if url.database not in {None, "", ":memory:"} else id(engine)
    else:
        database = url.database
    return engine.dialect.name, url.host, url.port, database


def migration_tables(source):
    # Use application definitions to convert MySQL tinyints to PostgreSQL bools.
    metadata = MetaData()
    for table in Base.metadata.sorted_tables:
        table.to_metadata(metadata)
    if inspect(source).has_table("novel"):
        legacy = Table("novel", MetaData(), autoload_with=source)
        Table("novel", metadata, *[
            Column(column.name, column.type.as_generic(), primary_key=column.primary_key, nullable=column.nullable)
            for column in legacy.columns
        ])
    tables = metadata.sorted_tables
    source_names = set(inspect(source).get_table_names())
    for table in tables:
        if table.name not in source_names:
            raise ValueError(f"Source is missing required table: {table.name}")
        names = {column["name"] for column in inspect(source).get_columns(table.name)}
        if set(table.columns.keys()) - names:
            raise ValueError(f"Source table needs a schema upgrade: {table.name}")
    return metadata, tables


def table_counts(connection, tables):
    available = set(inspect(connection).get_table_names())
    return {
        table.name: connection.scalar(select(func.count()).select_from(table)) if table.name in available else 0
        for table in tables
    }


def canonical_rows(rows, table):
    for row in rows:
        item = dict(row)
        for column in table.columns:
            if isinstance(column.type, Boolean) and item[column.name] is not None:
                item[column.name] = bool(item[column.name])
        yield item


def update_digest(digest, row):
    value = json.dumps(row, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":"))
    digest.update(value.encode("utf-8") + b"\n")


def reset_sequences(connection, tables):
    if connection.dialect.name != "postgresql":
        return
    for table in tables:
        keys = list(table.primary_key.columns)
        if len(keys) != 1 or not isinstance(keys[0].type, Integer):
            continue
        key = keys[0]
        sequence = connection.scalar(text("SELECT pg_get_serial_sequence(:table_name, :column_name)"),
                                     {"table_name": table.name, "column_name": key.name})
        if sequence:
            maximum = connection.scalar(select(func.max(key)))
            connection.execute(text("SELECT setval(CAST(:sequence AS regclass), :value, :called)"),
                               {"sequence": sequence, "value": maximum or 1, "called": maximum is not None})


def migrate(source_engine, target_engine, apply=False):
    if database_identity(source_engine) == database_identity(target_engine):
        raise ValueError("Source and target must be different databases")
    with source_engine.connect() as source:
        if source_engine.dialect.name in {"mysql", "postgresql"}:
            source = source.execution_options(isolation_level="REPEATABLE READ")
        with source.begin():
            metadata, tables = migration_tables(source)
            source_counts = table_counts(source, tables)
            with target_engine.connect() as target:
                if any(table_counts(target, tables).values()):
                    raise ValueError("Target is not empty; no records have been overwritten")
            report = {"mode": "apply" if apply else "dry-run", "source_rows": source_counts,
                      "target_dialect": target_engine.dialect.name,
                      "excluded": ["auth_tokens"], "verified": False}
            if not apply:
                return report
            metadata.create_all(target_engine)
            with target_engine.begin() as target:
                if target_engine.dialect.name == "postgresql":
                    target.execute(text("SELECT pg_advisory_xact_lock(739302024)"))
                if any(table_counts(target, tables).values()):
                    raise ValueError("Target changed during preflight; migration cancelled")
                expected_hashes = {}
                for table in tables:
                    digest = hashlib.sha256()
                    if table.name != "auth_tokens":
                        query = select(table).order_by(*table.primary_key.columns)
                        result = source.execute(query).mappings()
                        while rows := result.fetchmany(200):
                            batch = list(canonical_rows(rows, table))
                            for row in batch:
                                update_digest(digest, row)
                            target.execute(table.insert(), batch)
                    expected_hashes[table.name] = digest.hexdigest()
                reset_sequences(target, tables)
                actual_counts = table_counts(target, tables)
                expected_counts = {**source_counts, "auth_tokens": 0}
                if actual_counts != expected_counts:
                    raise ValueError("Row-count verification failed; transaction rolled back")
                for table in tables:
                    digest = hashlib.sha256()
                    rows = target.execute(select(table).order_by(*table.primary_key.columns)).mappings()
                    for row in canonical_rows(rows, table):
                        update_digest(digest, row)
                    if digest.hexdigest() != expected_hashes[table.name]:
                        raise ValueError(f"Content verification failed: {table.name}; transaction rolled back")
                report.update(target_rows=actual_counts, verified=True)
            return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-env", type=Path, required=True)
    parser.add_argument("--target-env", type=Path, required=True)
    parser.add_argument("--apply", action="store_true", help="Copy data only after confirming an empty target")
    args = parser.parse_args()
    try:
        source = configured_engine(args.source_env)
        target = configured_engine(args.target_env)
        report = migrate(source, target, apply=args.apply)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        # Do not echo DBAPI messages: they can contain secrets and SQL data.
        print(f"Migration failed ({type(exc).__name__}); no credentials or row data are logged", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
