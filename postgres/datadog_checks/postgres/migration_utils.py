# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Shared utilities for migration tool detection in PostgreSQL.
Used by both migrations.py (full migration collection) and schemas.py (migration context).
"""

from __future__ import annotations

# All supported migration tools - used for auto-detection when no filter is specified
SUPPORTED_MIGRATION_TOOLS = ("alembic", "golang-migrate", "prisma", "typeorm")

CHECK_TABLE_EXISTS_QUERY = """
SELECT EXISTS (
    SELECT FROM pg_tables WHERE tablename = %s
);
"""

GET_ALEMBIC_VERSION_QUERY = """
SELECT version_num FROM alembic_version;
"""

GET_GOLANG_MIGRATE_VERSION_QUERY = """
SELECT version, dirty FROM schema_migrations ORDER BY version DESC LIMIT 1;
"""

GET_PRISMA_MIGRATIONS_QUERY = """
SELECT id, migration_name, finished_at, applied_steps_count FROM _prisma_migrations ORDER BY finished_at DESC LIMIT 50;
"""

GET_TYPEORM_MIGRATIONS_QUERY = """
SELECT id, name, timestamp FROM migrations ORDER BY timestamp DESC LIMIT 50;
"""


def check_table_exists(cursor, table_name: str) -> bool:
    cursor.execute(CHECK_TABLE_EXISTS_QUERY, (table_name,))
    result = cursor.fetchone()
    if result is None:
        return False
    if isinstance(result, dict):
        return result.get("exists", False)
    return result[0] if result else False


def _empty_result() -> dict:
    """Return empty migration result structure."""
    return {"detected": False, "version": None, "dirty": None, "migrations": []}


def collect_alembic_migration(cursor, log=None) -> dict:
    """Collect Alembic migration info. Returns full result dict."""
    result = _empty_result()
    try:
        if check_table_exists(cursor, "alembic_version"):
            result["detected"] = True
            cursor.execute(GET_ALEMBIC_VERSION_QUERY)
            row = cursor.fetchone()
            if row:
                result["version"] = row.get("version_num") if isinstance(row, dict) else row[0]
    except Exception as e:
        if log:
            log.debug("Error collecting alembic migration: %s", e)
    return result


def collect_golang_migrate_migration(cursor, log=None) -> dict:
    """Collect golang-migrate migration info. Returns full result dict."""
    result = _empty_result()
    try:
        if check_table_exists(cursor, "schema_migrations"):
            result["detected"] = True
            cursor.execute(GET_GOLANG_MIGRATE_VERSION_QUERY)
            row = cursor.fetchone()
            if row:
                if isinstance(row, dict):
                    result["version"] = row.get("version")
                    result["dirty"] = row.get("dirty")
                else:
                    result["version"] = row[0]
                    result["dirty"] = row[1] if len(row) > 1 else None
    except Exception as e:
        if log:
            log.debug("Error collecting golang-migrate migration: %s", e)
    return result


def collect_prisma_migration(cursor, log=None) -> dict:
    """Collect Prisma migration info. Returns full result dict."""
    result = _empty_result()
    try:
        if check_table_exists(cursor, "_prisma_migrations"):
            result["detected"] = True
            cursor.execute(GET_PRISMA_MIGRATIONS_QUERY)
            rows = cursor.fetchall()
            migrations = [dict(row) if hasattr(row, 'keys') else row for row in rows]
            result["migrations"] = migrations
            if migrations:
                first = migrations[0]
                result["version"] = first.get("migration_name") if isinstance(first, dict) else None
    except Exception as e:
        if log:
            log.debug("Error collecting prisma migration: %s", e)
    return result


def collect_typeorm_migration(cursor, log=None) -> dict:
    """Collect TypeORM migration info. Returns full result dict."""
    result = _empty_result()
    try:
        if check_table_exists(cursor, "migrations"):
            result["detected"] = True
            cursor.execute(GET_TYPEORM_MIGRATIONS_QUERY)
            rows = cursor.fetchall()
            migrations = [dict(row) if hasattr(row, 'keys') else row for row in rows]
            result["migrations"] = migrations
            if migrations:
                first = migrations[0]
                result["version"] = first.get("name") if isinstance(first, dict) else None
    except Exception as e:
        if log:
            log.debug("Error collecting typeorm migration: %s", e)
    return result


def get_migration_version_only(cursor, tool: str, log=None) -> str | None:
    """Get just the version string for a migration tool. Used by schema collection."""
    if tool == "alembic":
        result = collect_alembic_migration(cursor, log)
        return result["version"]
    elif tool == "golang-migrate":
        result = collect_golang_migrate_migration(cursor, log)
        return str(result["version"]) if result["version"] is not None else None
    elif tool == "prisma":
        result = collect_prisma_migration(cursor, log)
        return result["version"]
    elif tool == "typeorm":
        result = collect_typeorm_migration(cursor, log)
        return result["version"]
    return None
