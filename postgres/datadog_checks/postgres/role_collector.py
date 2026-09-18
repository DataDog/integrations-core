# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from psycopg.rows import dict_row

from datadog_checks.base.utils.db.utils import default_json_event_encoding, now_ms

from .filters import regex_exclude_clauses, regex_include_clause
from .role_queries import (
    QUERY_DEFAULT_PRIVILEGES,
    QUERY_OBJECT_DEPENDENCIES,
    QUERY_OBJECT_PRIVILEGES,
    QUERY_OBJECTS,
    QUERY_ROLE_SETTINGS,
    QUERY_ROLES,
    list_databases_query,
    memberships_query,
)
from .util import payload_pg_version
from .version_utils import V14, V16

if TYPE_CHECKING:
    from datadog_checks.postgres import PostgreSql


INSTANCE_ARRAYS = ("roles", "memberships", "settings")
DATABASE_ARRAYS = ("object_privileges", "default_privileges", "objects", "object_dependencies")
PAYLOAD_CHUNK_SIZE = 10_000


class RoleCollectionCancelled(Exception):
    """Raised to stop a role snapshot without marking it complete."""


@dataclass
class PostgresRoleCollectorConfig:
    collection_interval: float
    max_query_duration: float
    include_databases: list[str]
    exclude_databases: list[str]
    payload_chunk_size: int = PAYLOAD_CHUNK_SIZE


class RoleSnapshotEmitter:
    """Build and submit a chunked snapshot containing multiple entity arrays."""

    def __init__(
        self,
        base_event: dict[str, Any],
        array_names: tuple[str, ...],
        submit: Callable[[dict[str, Any]], None],
        chunk_size: int,
    ) -> None:
        self._base_event = base_event
        self._array_names = array_names
        self._submit = submit
        self._chunk_size = chunk_size
        self._buffers: dict[str, list[dict[str, Any]]] = {name: [] for name in array_names}
        self._buffered_rows_count = 0
        self.payloads_count = 0
        self.rows_count = 0

    def append(self, array_name: str, row: dict[str, Any]) -> None:
        self._buffers[array_name].append(row)
        self.rows_count += 1
        self._buffered_rows_count += 1
        if self._buffered_rows_count >= self._chunk_size:
            self._flush(is_last=False)

    def flush_terminal(self) -> None:
        self._flush(is_last=True)

    def discard(self) -> None:
        self._clear_buffers()

    def _clear_buffers(self) -> None:
        for rows in self._buffers.values():
            rows.clear()
        self._buffered_rows_count = 0

    def _flush(self, is_last: bool) -> None:
        event = dict(self._base_event)
        event["timestamp"] = now_ms()
        for name, rows in self._buffers.items():
            event[name] = list(rows)

        self.payloads_count += 1
        if is_last:
            event["collection_payloads_count"] = self.payloads_count

        self._submit(event)
        self._clear_buffers()


class PostgresRoleCollector:
    """Collect role and privilege snapshots from a PostgreSQL instance."""

    def __init__(self, check: PostgreSql, cancel_event: threading.Event) -> None:
        role_config = check._config.collect_roles
        self._check = check
        self._cancel_event = cancel_event
        self._log = check.log
        self._config = PostgresRoleCollectorConfig(
            collection_interval=role_config.collection_interval,
            max_query_duration=role_config.max_query_duration,
            include_databases=list(role_config.include_databases),
            exclude_databases=list(role_config.exclude_databases),
        )
        self._unsupported_version_logged = False
        self._rows_count = 0
        self._payloads_count = 0

    def collect_roles(self, tags_no_db: list[str]) -> bool:
        """Collect the instance scope and each accessible logical database scope."""
        if self._check.version is None or self._check.version < V14:
            if not self._unsupported_version_logged:
                self._log.warning(
                    "Role collection requires PostgreSQL 14 or later; connected to %s", self._check.version
                )
                self._unsupported_version_logged = True
            return False

        started_at = time.time() * 1000
        had_error = False
        self._rows_count = 0
        self._payloads_count = 0
        try:
            if self._cancel_event.is_set():
                return False

            if not self._collect_instance_scope(tags_no_db):
                had_error = True

            try:
                databases = self._get_databases()
            except RoleCollectionCancelled:
                return False
            except Exception:
                had_error = True
                self._log.exception("Error listing databases for role collection")
                databases = []

            for database_name in databases:
                if self._cancel_event.is_set():
                    break
                if not self._collect_database_scope(database_name, tags_no_db):
                    had_error = True

            return True
        finally:
            status = "error" if had_error else "success"
            metric_tags = self._check.tags + [f"status:{status}"]
            self._check.histogram(
                "dd.postgres.roles.time",
                (time.time() * 1000) - started_at,
                tags=metric_tags,
                hostname=self._check.reported_hostname,
                raw=True,
            )
            self._check.gauge(
                "dd.postgres.roles.rows_count",
                self._rows_count,
                tags=metric_tags,
                hostname=self._check.reported_hostname,
                raw=True,
            )
            self._check.gauge(
                "dd.postgres.roles.payloads_count",
                self._payloads_count,
                tags=metric_tags,
                hostname=self._check.reported_hostname,
                raw=True,
            )

    def _collect_instance_scope(self, tags_no_db: list[str]) -> bool:
        emitter = self._new_emitter("pg_roles", INSTANCE_ARRAYS, tags_no_db)
        try:
            with self._check._get_main_db() as conn:
                with conn.transaction():
                    with conn.cursor(row_factory=dict_row) as cursor:
                        self._configure_transaction(cursor)
                        self._collect_query(cursor, QUERY_ROLES, (), "roles", emitter)
                        self._collect_query(
                            cursor,
                            memberships_query(pg16_plus=self._check.version >= V16),
                            (),
                            "memberships",
                            emitter,
                        )
                        self._collect_query(cursor, QUERY_ROLE_SETTINGS, (), "settings", emitter)
            emitter.flush_terminal()
            return True
        except RoleCollectionCancelled:
            emitter.discard()
            return False
        except Exception:
            emitter.discard()
            self._log.exception("Error collecting PostgreSQL instance role metadata")
            return False
        finally:
            self._record_emitter(emitter)

    def _collect_database_scope(self, database_name: str, tags_no_db: list[str]) -> bool:
        emitter = self._new_emitter(
            "pg_role_privileges",
            DATABASE_ARRAYS,
            tags_no_db,
            database_name=database_name,
        )
        try:
            with self._check.db_pool.get_connection(database_name) as conn:
                with conn.transaction():
                    with conn.cursor(row_factory=dict_row) as cursor:
                        self._configure_transaction(cursor)
                        self._collect_query(cursor, QUERY_DEFAULT_PRIVILEGES, (), "default_privileges", emitter)
                        self._collect_query(cursor, QUERY_OBJECT_PRIVILEGES, (), "object_privileges", emitter)
                        self._collect_query(cursor, QUERY_OBJECTS, (), "objects", emitter)
                        self._collect_query(cursor, QUERY_OBJECT_DEPENDENCIES, (), "object_dependencies", emitter)
            emitter.flush_terminal()
            return True
        except RoleCollectionCancelled:
            emitter.discard()
            return False
        except Exception:
            emitter.discard()
            self._log.exception("Error collecting role privileges for database '%s'", database_name)
            return False
        finally:
            self._record_emitter(emitter)

    def _get_databases(self) -> list[str]:
        params: list[str] = []
        database_filter = "TRUE"
        if self._check._config.dbstrict and not self._check.autodiscovery:
            database_filter += " AND d.datname = %s"
            params.append(self._check._config.dbname)
        else:
            database_filter += regex_exclude_clauses("d.datname", self._config.exclude_databases)
            params.extend(self._config.exclude_databases)
            database_filter += regex_include_clause("d.datname", self._config.include_databases)
            params.extend(self._config.include_databases)

            autodiscovery_databases = self._check.autodiscovery.get_items() if self._check.autodiscovery else []
            if autodiscovery_databases:
                database_filter += " AND d.datname IN ({})".format(", ".join(["%s"] * len(autodiscovery_databases)))
                params.extend(autodiscovery_databases)

        with self._check._get_main_db() as conn:
            with conn.transaction():
                with conn.cursor(row_factory=dict_row) as cursor:
                    self._configure_transaction(cursor)
                    self._check_cancelled()
                    query = list_databases_query(database_filter)
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    return [row["database_name"] for row in cursor]

    def _configure_transaction(self, cursor: Any) -> None:
        self._check_cancelled()
        cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        cursor.execute(
            "SELECT pg_catalog.set_config('statement_timeout', %s, true)",
            (str(int(self._config.max_query_duration * 1000)),),
        )

    def _collect_query(
        self,
        cursor: Any,
        query: str,
        params: tuple[Any, ...],
        array_name: str,
        emitter: RoleSnapshotEmitter,
    ) -> None:
        self._check_cancelled()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        for row in cursor:
            self._check_cancelled()
            emitter.append(array_name, dict(row))

    def _new_emitter(
        self,
        kind: str,
        array_names: tuple[str, ...],
        tags_no_db: list[str],
        database_name: str | None = None,
    ) -> RoleSnapshotEmitter:
        event = {
            "host": self._check.reported_hostname,
            "database_instance": self._check.database_identifier,
            "agent_version": self._check.agent_version,
            "dbms": self._check.dbms,
            "dbms_version": payload_pg_version(self._check.version),
            "kind": kind,
            "collection_interval": self._config.collection_interval,
            "tags": tags_no_db,
            "cloud_metadata": self._check.cloud_metadata,
            "collection_started_at": now_ms(),
        }
        if database_name is not None:
            event["database_name"] = database_name
        return RoleSnapshotEmitter(
            event,
            array_names,
            self._submit_event,
            self._config.payload_chunk_size,
        )

    def _submit_event(self, event: dict[str, Any]) -> None:
        self._check.database_monitoring_metadata(json.dumps(event, default=default_json_event_encoding))

    def _record_emitter(self, emitter: RoleSnapshotEmitter) -> None:
        self._rows_count += emitter.rows_count
        self._payloads_count += emitter.payloads_count

    def _check_cancelled(self) -> None:
        if self._cancel_event.is_set():
            raise RoleCollectionCancelled()
