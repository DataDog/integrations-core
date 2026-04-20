# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Collects ClickHouse catalog metadata (tables + views + columns) and emits a
single `kind=clickhouse_databases` payload per cycle, consumed by
dbm-metadata-processor.

Why a catalog/metadata path (not events):
  Materialized views are durable named resources with structured children
  (columns) and multi-KB DDL. events-intake rejects nested arrays of
  objects and caps per-field size, so view payloads get silently dropped
  past `eventsapi.write_attempt`. OrgStore + REDAPL via metadata-processor
  are the right home for catalog data.

Dedup note (SDBM-***):
  When single_endpoint_mode=true on a ClickHouse Cloud replica set, the
  underlying queries run through clusterAllReplicas(system.tables) and
  return N identical rows per table/view. We dedupe on (database, name)
  before emission to keep the payload small and prevent metadata_modification_time
  churn from replica-local clock skew re-triggering SnapshotStore writes.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from clickhouse_connect.driver.exceptions import OperationalError

if TYPE_CHECKING:
    from datadog_checks.clickhouse import ClickhouseCheck
    from datadog_checks.clickhouse.config_models.instance import CollectSchemas

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method

# create_query DDL is bounded before emit. Real-world DDL is 1-3KB;
# the cap protects REDAPL/OrgStore from pathological view definitions.
_CREATE_QUERY_MAX_BYTES = 16 * 1024
_CREATE_QUERY_TRUNC_SUFFIX = '…[truncated]'

# ClickHouse system databases that should never appear in the catalog.
_SYSTEM_DATABASES = ('system', 'INFORMATION_SCHEMA', 'information_schema')

# Engines that represent views (any flavor). Any table row whose engine ends
# in "View" is a view for our purposes.
_VIEW_ENGINES = frozenset(['View', 'MaterializedView', 'LiveView', 'WindowView'])


# The tables query intentionally asks for everything we might want so we can
# issue a single round-trip per cycle. For views, the refreshable fields come
# from system.view_refreshes (24.3+) and are joined in Python, not SQL, so the
# query stays portable across ClickHouse versions.
_TABLES_QUERY = """\
SELECT
    database,
    name,
    engine,
    toString(uuid) AS uuid,
    toInt64(total_rows) AS total_rows,
    toInt64(total_bytes) AS total_bytes,
    create_table_query,
    sorting_key,
    partition_key,
    primary_key,
    sampling_key,
    toInt64(toUnixTimestamp(metadata_modification_time)) AS metadata_modified_at,
    as_select
FROM {tables_table}
WHERE database NOT IN ('system', 'INFORMATION_SCHEMA', 'information_schema')
ORDER BY database, name
LIMIT {max_tables}
"""

_COLUMNS_QUERY = """\
SELECT
    database,
    table,
    name,
    type,
    default_expression,
    comment,
    toInt32(position) AS position
FROM {columns_table}
WHERE database NOT IN ('system', 'INFORMATION_SCHEMA', 'information_schema')
ORDER BY database, table, position
"""

# system.view_refreshes exists in ClickHouse 24.3+. We handle UnknownTable by
# downgrading to a warning once, then skipping the column set for the cycle.
_VIEW_REFRESHES_QUERY = """\
SELECT
    database,
    view,
    status,
    toInt64(toUnixTimestamp(last_success_time)) AS last_refresh_time,
    last_refresh_result,
    toInt64(toUnixTimestamp(next_refresh_time)) AS next_refresh_time,
    exception
FROM {view_refreshes_table}
"""


def agent_check_getter(self):
    return self._check


class ClickhouseMetadata(DBMAsyncJob):
    """
    Collects the full ClickHouse catalog (tables, views, columns) into one
    `kind=clickhouse_databases` payload per cycle. Payloads are consumed by
    dbm-metadata-processor which writes three resource types to REDAPL and
    OrgStore.
    """

    def __init__(self, check: ClickhouseCheck, config: CollectSchemas):
        collection_interval = config.collection_interval

        super(ClickhouseMetadata, self).__init__(
            check,
            rate_limit=1 / collection_interval,
            run_sync=config.run_sync,
            enabled=config.enabled,
            dbms='clickhouse',
            min_collection_interval=check._config.min_collection_interval,
            expected_db_exceptions=(Exception,),
            job_name='clickhouse-metadata',
        )
        self._check = check
        self._config = config
        self._collection_interval = collection_interval
        self._max_tables: int = config.max_tables
        self._max_columns: int = config.max_columns

        self._db_client = None

        # Whether we've already logged the view_refreshes grant hint.
        # We log once per process lifetime to avoid log spam on older servers.
        self._view_refreshes_unsupported_logged = False
        self._view_refreshes_permission_logged = False

    def cancel(self):
        super(ClickhouseMetadata, self).cancel()
        self._close_db_client()

    def _close_db_client(self):
        if self._db_client:
            try:
                self._db_client.close()
            except Exception as e:
                self._log.debug("Error closing metadata client: %s", e)
            self._db_client = None

    def _execute_query(self, query: str) -> list:
        if self._db_client is None:
            self._db_client = self._check.create_dbm_client()
        try:
            return self._db_client.query(query).result_rows
        except OperationalError as e:
            self._log.warning("Connection error on metadata query, will reconnect: %s", e)
            self._close_db_client()
            raise

    @tracked_method(agent_check_getter=agent_check_getter)
    def run_job(self):
        self._collect_and_emit()

    def _collect_and_emit(self):
        start = time.time()
        try:
            tables_rows = self._execute_query(
                _TABLES_QUERY.format(
                    tables_table=self._check.get_system_table('tables'),
                    max_tables=self._max_tables,
                )
            )
        except Exception:
            self._log.exception("Failed to collect clickhouse tables")
            return

        try:
            columns_rows = self._execute_query(
                _COLUMNS_QUERY.format(columns_table=self._check.get_system_table('columns'))
            )
        except Exception:
            self._log.exception("Failed to collect clickhouse columns")
            columns_rows = []

        refresh_rows = self._collect_view_refreshes()

        payload = self._build_payload(tables_rows, columns_rows, refresh_rows)
        if payload is None:
            return

        self._check.database_monitoring_metadata(json.dumps(payload, default=default_json_event_encoding))
        self._log.debug(
            "Emitted clickhouse_databases payload (%d databases) in %.2fs",
            len(payload['metadata']['databases']),
            time.time() - start,
        )

    def _collect_view_refreshes(self) -> list:
        """
        Pull refresh status from system.view_refreshes. Returns [] on older
        servers or when the agent user lacks SELECT on system.view_refreshes —
        refresh fields simply don't populate for the cycle.
        """
        try:
            return self._execute_query(
                _VIEW_REFRESHES_QUERY.format(view_refreshes_table=self._check.get_system_table('view_refreshes'))
            )
        except Exception as e:
            message = str(e)
            lowered = message.lower()
            if 'unknown table' in lowered or 'unknowntable' in lowered:
                if not self._view_refreshes_unsupported_logged:
                    self._log.info(
                        "system.view_refreshes not present (ClickHouse < 24.3); refresh status will not be populated."
                    )
                    self._view_refreshes_unsupported_logged = True
            elif 'not enough privileges' in lowered or 'access_denied' in lowered:
                if not self._view_refreshes_permission_logged:
                    self._log.warning(
                        "Agent user lacks SELECT on system.view_refreshes; refresh status "
                        "will not be populated. Grant with: "
                        "GRANT SELECT ON system.view_refreshes TO <agent_user>"
                    )
                    self._view_refreshes_permission_logged = True
            else:
                self._log.exception("Unexpected error querying system.view_refreshes")
            return []

    def _build_payload(self, tables_rows, columns_rows, refresh_rows) -> dict[str, Any] | None:
        columns_by_parent = self._columns_by_parent(columns_rows)
        refresh_by_view = {(row[0], row[1]): row for row in refresh_rows}

        # Dedup by (database, name) because single_endpoint_mode joins via
        # clusterAllReplicas which returns identical rows from each replica.
        seen: set[tuple[str, str]] = set()

        databases: dict[str, dict[str, Any]] = defaultdict(lambda: {'name': '', 'tables': [], 'views': []})

        for row in tables_rows:
            (
                database,
                name,
                engine,
                uuid_str,
                total_rows,
                total_bytes,
                create_query,
                sorting_key,
                partition_key,
                primary_key,
                sampling_key,
                metadata_modified_at,
                as_select,
            ) = row

            if (database, name) in seen:
                continue
            seen.add((database, name))

            db = databases[database]
            db['name'] = database

            cols = columns_by_parent.get((database, name), [])
            truncated_ddl = _truncate_ddl(create_query)

            if engine in _VIEW_ENGINES:
                view = self._make_view(
                    name=name,
                    engine=engine,
                    uuid_str=uuid_str,
                    total_rows=total_rows,
                    total_bytes=total_bytes,
                    create_query=truncated_ddl,
                    as_select=as_select,
                    columns=cols,
                    metadata_modified_at=metadata_modified_at,
                    refresh_row=refresh_by_view.get((database, name)),
                )
                db['views'].append(view)
            else:
                db['tables'].append(
                    {
                        'name': name,
                        'engine': engine,
                        'uuid': uuid_str,
                        'total_rows': int(total_rows or 0),
                        'total_bytes': int(total_bytes or 0),
                        'sorting_key': sorting_key or '',
                        'partition_key': partition_key or '',
                        'primary_key': primary_key or '',
                        'sampling_key': sampling_key or '',
                        'create_query': truncated_ddl,
                        'columns': cols,
                        'metadata_modified_at': int(metadata_modified_at or 0),
                    }
                )

        if not databases:
            return None

        return {
            'kind': 'clickhouse_databases',
            'dbms': 'clickhouse',
            'database_instance': self._check.database_identifier,
            'database_hostname': self._check.reported_hostname,
            'host': self._check.reported_hostname,
            'dbms_version': self._check.dbms_version,
            'agent_version': datadog_agent.get_version(),
            'ddagenthostname': self._check.agent_hostname,
            'timestamp': time.time() * 1000,
            'collection_interval': self._collection_interval,
            'tags': self._check.tags,
            # Drives SnapshotStore reaping in dbm-metadata-processor.
            'collection_id': str(uuid.uuid4()),
            'metadata': {'databases': list(databases.values())},
        }

    def _make_view(
        self,
        name,
        engine,
        uuid_str,
        total_rows,
        total_bytes,
        create_query,
        as_select,
        columns,
        metadata_modified_at,
        refresh_row,
    ) -> dict[str, Any]:
        source_dbs, source_tables = _parse_view_sources(as_select, create_query)
        target_db, target_table = _parse_view_target(create_query)

        view: dict[str, Any] = {
            'name': name,
            'engine': engine,
            'uuid': uuid_str,
            'total_rows': int(total_rows or 0),
            'total_bytes': int(total_bytes or 0),
            'create_query': create_query,
            'columns': columns,
            'metadata_modified_at': int(metadata_modified_at or 0),
            'source_databases': source_dbs,
            'source_tables': source_tables,
        }

        if target_db is not None:
            view['target_database'] = target_db
        if target_table is not None:
            view['target_table'] = target_table

        if refresh_row is not None:
            # (database, view, status, last_refresh_time, last_refresh_result, next_refresh_time, exception)
            _, _, status, last_time, last_result, next_time, exception = refresh_row
            view['is_refreshable'] = True
            view['refresh_status'] = status or ''
            view['last_refresh_time'] = int(last_time or 0)
            view['last_refresh_result'] = last_result or ''
            view['next_refresh_time'] = int(next_time or 0)
            if exception:
                view['refresh_exception'] = exception
        else:
            view['is_refreshable'] = False

        return view

    def _columns_by_parent(self, columns_rows) -> dict[tuple[str, str], list[dict[str, Any]]]:
        out: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in columns_rows:
            database, table, name, type_, default, comment, position = row
            if len(out[(database, table)]) >= self._max_columns:
                continue
            out[(database, table)].append(
                {
                    'name': name,
                    'type': type_,
                    'default': default or '',
                    'comment': comment or '',
                    'position': int(position or 0),
                }
            )
        return out


def _truncate_ddl(create_query: str | None) -> str:
    if not create_query:
        return ''
    encoded = create_query.encode('utf-8')
    if len(encoded) <= _CREATE_QUERY_MAX_BYTES:
        return create_query
    # Truncate on a UTF-8 boundary so we never emit invalid bytes.
    budget = _CREATE_QUERY_MAX_BYTES - len(_CREATE_QUERY_TRUNC_SUFFIX.encode('utf-8'))
    clipped = encoded[:budget]
    # Walk back until we land on a valid UTF-8 boundary.
    while clipped and (clipped[-1] & 0xC0) == 0x80:
        clipped = clipped[:-1]
    return clipped.decode('utf-8', errors='ignore') + _CREATE_QUERY_TRUNC_SUFFIX


def _parse_view_sources(as_select: str | None, create_query: str | None) -> tuple[list[str], list[str]]:
    """
    Best-effort source extraction. ClickHouse's as_select field has the SELECT
    body for views; we do a very light parse looking for FROM/JOIN clauses. We
    intentionally keep this simple — the server-side DDL has full fidelity and
    lives in create_query, while these fields are for fast UI lookups only.
    """
    text = as_select or ''
    # Fallback to create_query if as_select is empty (older servers).
    if not text and create_query:
        text = create_query
    if not text:
        return [], []

    import re

    databases: list[str] = []
    tables: list[str] = []
    seen: set[tuple[str, str]] = set()
    # Match FROM db.table, FROM "db"."table", JOIN db.table, etc.
    pattern = re.compile(
        r"""\b(?:FROM|JOIN)\s+
            (?:"([^"]+)"|`([^`]+)`|([A-Za-z_][\w]*))
            (?:\s*\.\s*
              (?:"([^"]+)"|`([^`]+)`|([A-Za-z_][\w]*)))?""",
        re.IGNORECASE | re.VERBOSE,
    )
    for match in pattern.finditer(text):
        parts = [g for g in match.groups() if g]
        if len(parts) == 1:
            db_name = ''
            table_name = parts[0]
        else:
            db_name, table_name = parts[0], parts[1]
        if (db_name, table_name) in seen:
            continue
        seen.add((db_name, table_name))
        databases.append(db_name)
        tables.append(table_name)
    return databases, tables


def _parse_view_target(create_query: str | None) -> tuple[str | None, str | None]:
    """
    Extract the TO-clause target of a materialized view ("TO db.target_table").
    Returns (None, None) when the view has no TO clause (inline state).
    """
    if not create_query:
        return None, None

    import re

    match = re.search(
        r"""\bTO\s+
            (?:"([^"]+)"|`([^`]+)`|([A-Za-z_][\w]*))
            (?:\s*\.\s*
              (?:"([^"]+)"|`([^`]+)`|([A-Za-z_][\w]*)))?""",
        create_query,
        re.IGNORECASE | re.VERBOSE,
    )
    if not match:
        return None, None
    parts = [g for g in match.groups() if g]
    if len(parts) == 1:
        return None, parts[0]
    return parts[0], parts[1]
