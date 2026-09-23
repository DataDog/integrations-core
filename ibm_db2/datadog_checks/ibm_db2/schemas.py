# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

import ibm_db

from datadog_checks.base.utils.db.schemas import DatabaseInfo, SchemaCollector, SchemaCollectorConfig
from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.base.utils.serialization import json

from .connection import Db2Connection

if TYPE_CHECKING:
    from .config_models import InstanceConfig
    from .config_models.instance import CollectSchemas
    from .ibm_db2 import IbmDb2Check

# Db2 reserves schema names starting with SYS for the catalog; NULLID and SQLJ hold driver packages.
SYSTEM_SCHEMAS_FILTER = "s.SCHEMANAME NOT LIKE 'SYS%' AND s.SCHEMANAME NOT IN ('NULLID', 'SQLJ')"

# One row per table (or per schema without tables), with its columns, indexes, foreign keys and
# partition key aggregated into JSON arrays so rows can be streamed from the cursor one at a time.
#
# Every JSON_ARRAY fullselect starts from `SYSIBM.SYSDUMMY1 LEFT JOIN` so that it always returns at
# least one row: Db2 11.5 fails with SQL0901N ("Unexpected aggregation mode") when the fullselect is
# empty. The placeholder row yields a NULL element, which JSON_ARRAY drops (ABSENT ON NULL).
#
# Referential rule codes: https://www.ibm.com/docs/en/db2/11.5?topic=views-syscatreferences
SCHEMA_TABLES_QUERY = """
WITH schemas AS (
    SELECT s.SCHEMANAME AS schema_name, s.OWNER AS schema_owner
    FROM SYSCAT.SCHEMATA s
    WHERE {system_schemas_filter}{schema_filters}
),
tables AS (
    SELECT t.TABSCHEMA, t.TABNAME, t.OWNER, t.TYPE, t.CARD
    FROM SYSCAT.TABLES t
    WHERE t.TYPE IN ('T', 'N'){table_filters}
),
schema_tables AS (
    SELECT schemas.schema_name, schemas.schema_owner,
           tables.TABNAME AS table_name, tables.OWNER AS table_owner,
           tables.TYPE AS table_type, tables.CARD AS row_count
    FROM schemas
    LEFT JOIN tables ON tables.TABSCHEMA = schemas.schema_name
    ORDER BY schemas.schema_name, tables.TABNAME
    FETCH FIRST {max_tables} ROWS ONLY
)
SELECT schema_tables.schema_name, schema_tables.schema_owner,
       schema_tables.table_name, schema_tables.table_owner, schema_tables.table_type, schema_tables.row_count,
       JSON_ARRAY((
           SELECT CASE WHEN c.COLNAME IS NOT NULL THEN JSON_OBJECT(
                      KEY 'name' VALUE c.COLNAME,
                      KEY 'data_type' VALUE c.TYPENAME,
                      KEY 'length' VALUE c.LENGTH,
                      KEY 'scale' VALUE c.SCALE,
                      KEY 'nullable' VALUE CASE WHEN c.NULLS = 'Y' THEN 'true' ELSE 'false' END FORMAT JSON,
                      KEY 'default' VALUE c.DEFAULT
                  ) END
           FROM SYSIBM.SYSDUMMY1
           LEFT JOIN SYSCAT.COLUMNS c
                  ON c.TABSCHEMA = schema_tables.schema_name AND c.TABNAME = schema_tables.table_name
           ORDER BY c.COLNO
           FETCH FIRST {max_columns} ROWS ONLY
       ) FORMAT JSON RETURNING CLOB(100M)) AS columns,
       JSON_ARRAY((
           SELECT CASE WHEN i.INDNAME IS NOT NULL THEN JSON_OBJECT(
                      KEY 'schema' VALUE RTRIM(i.INDSCHEMA),
                      KEY 'name' VALUE i.INDNAME,
                      KEY 'is_unique' VALUE CASE WHEN i.UNIQUERULE IN ('P', 'U') THEN 'true' ELSE 'false' END
                          FORMAT JSON,
                      KEY 'is_primary' VALUE CASE WHEN i.UNIQUERULE = 'P' THEN 'true' ELSE 'false' END FORMAT JSON,
                      KEY 'index_type' VALUE RTRIM(i.INDEXTYPE),
                      KEY 'columns' VALUE JSON_ARRAY((
                          SELECT CASE WHEN ic.COLNAME IS NOT NULL THEN JSON_OBJECT(
                                     KEY 'name' VALUE ic.COLNAME,
                                     KEY 'order' VALUE CASE ic.COLORDER
                                         WHEN 'A' THEN 'ASC' WHEN 'D' THEN 'DESC' WHEN 'I' THEN 'INCLUDE'
                                     END
                                 ) END
                          FROM SYSIBM.SYSDUMMY1
                          LEFT JOIN SYSCAT.INDEXCOLUSE ic ON ic.INDSCHEMA = i.INDSCHEMA AND ic.INDNAME = i.INDNAME
                          ORDER BY ic.COLSEQ
                      ) FORMAT JSON) FORMAT JSON
                  ) END
           FROM SYSIBM.SYSDUMMY1
           LEFT JOIN SYSCAT.INDEXES i
                  ON i.TABSCHEMA = schema_tables.schema_name AND i.TABNAME = schema_tables.table_name
           ORDER BY i.INDSCHEMA, i.INDNAME
       ) FORMAT JSON RETURNING CLOB(100M)) AS indexes,
       JSON_ARRAY((
           SELECT CASE WHEN r.CONSTNAME IS NOT NULL THEN JSON_OBJECT(
                      KEY 'name' VALUE r.CONSTNAME,
                      KEY 'columns' VALUE JSON_ARRAY((
                          SELECT k.COLNAME
                          FROM SYSIBM.SYSDUMMY1
                          LEFT JOIN SYSCAT.KEYCOLUSE k
                                 ON k.CONSTNAME = r.CONSTNAME AND k.TABSCHEMA = r.TABSCHEMA AND k.TABNAME = r.TABNAME
                          ORDER BY k.COLSEQ
                      )) FORMAT JSON,
                      KEY 'referenced_schema' VALUE RTRIM(r.REFTABSCHEMA),
                      KEY 'referenced_table' VALUE r.REFTABNAME,
                      KEY 'referenced_columns' VALUE JSON_ARRAY((
                          SELECT k.COLNAME
                          FROM SYSIBM.SYSDUMMY1
                          LEFT JOIN SYSCAT.KEYCOLUSE k
                                 ON k.CONSTNAME = r.REFKEYNAME AND k.TABSCHEMA = r.REFTABSCHEMA
                                AND k.TABNAME = r.REFTABNAME
                          ORDER BY k.COLSEQ
                      )) FORMAT JSON,
                      KEY 'delete_rule' VALUE CASE r.DELETERULE
                          WHEN 'A' THEN 'NO ACTION' WHEN 'C' THEN 'CASCADE'
                          WHEN 'N' THEN 'SET NULL' WHEN 'R' THEN 'RESTRICT'
                      END,
                      KEY 'update_rule' VALUE CASE r.UPDATERULE WHEN 'A' THEN 'NO ACTION' WHEN 'R' THEN 'RESTRICT' END
                  ) END
           FROM SYSIBM.SYSDUMMY1
           LEFT JOIN SYSCAT.REFERENCES r
                  ON r.TABSCHEMA = schema_tables.schema_name AND r.TABNAME = schema_tables.table_name
           ORDER BY r.CONSTNAME
       ) FORMAT JSON RETURNING CLOB(100M)) AS foreign_keys,
       JSON_ARRAY((
           SELECT CAST(e.DATAPARTITIONEXPRESSION AS VARCHAR(1024))
           FROM SYSIBM.SYSDUMMY1
           LEFT JOIN SYSCAT.DATAPARTITIONEXPRESSION e
                  ON e.TABSCHEMA = schema_tables.schema_name AND e.TABNAME = schema_tables.table_name
           ORDER BY e.DATAPARTITIONKEYSEQ
       ) RETURNING CLOB(100M)) AS partition_key,
       (SELECT COUNT(*)
        FROM SYSCAT.DATAPARTITIONS p
        WHERE p.TABSCHEMA = schema_tables.schema_name AND p.TABNAME = schema_tables.table_name) AS num_partitions
FROM schema_tables
ORDER BY schema_tables.schema_name, schema_tables.table_name
"""

TABLE_TYPES = {'T': 'TABLE', 'N': 'NICKNAME'}


def regex_exclude_clauses(column: str, patterns: tuple[str, ...]) -> str:
    return "".join(" AND NOT REGEXP_LIKE({}, ?)".format(column) for _ in patterns)


def regex_include_clause(column: str, patterns: tuple[str, ...]) -> str:
    if not patterns:
        return ""
    return " AND ({})".format(" OR ".join("REGEXP_LIKE({}, ?)".format(column) for _ in patterns))


class Db2SchemaCollectorConfig(SchemaCollectorConfig):
    def __init__(self, config: CollectSchemas):
        super().__init__()
        self.enabled = config.enabled
        self.collection_interval = int(config.collection_interval)
        self.max_tables = int(config.max_tables)
        self.max_columns = int(config.max_columns)
        self.max_query_duration = int(config.max_query_duration)
        self.include_schemas = config.include_schemas
        self.exclude_schemas = config.exclude_schemas
        self.include_tables = config.include_tables
        self.exclude_tables = config.exclude_tables


def build_schema_tables_query(config: Db2SchemaCollectorConfig) -> tuple[str, list[str]]:
    schema_filters = regex_exclude_clauses('s.SCHEMANAME', config.exclude_schemas) + regex_include_clause(
        's.SCHEMANAME', config.include_schemas
    )
    table_filters = regex_exclude_clauses('t.TABNAME', config.exclude_tables) + regex_include_clause(
        't.TABNAME', config.include_tables
    )
    query = SCHEMA_TABLES_QUERY.format(
        system_schemas_filter=SYSTEM_SCHEMAS_FILTER,
        schema_filters=schema_filters,
        table_filters=table_filters,
        max_tables=config.max_tables,
        max_columns=config.max_columns,
    )
    # Collapse whitespace so the statement sent to Db2 (and seen in its monitoring views) stays compact.
    query = ' '.join(query.split())
    params = [*config.exclude_schemas, *config.include_schemas, *config.exclude_tables, *config.include_tables]
    return query, params


class Db2SchemaCollector(SchemaCollector):
    _check: IbmDb2Check
    _config: Db2SchemaCollectorConfig

    def __init__(self, check: IbmDb2Check, db_name: str, config: Db2SchemaCollectorConfig, connection: Db2Connection):
        super().__init__(check, config)
        self._db_name = db_name
        self._connection = connection

    @property
    def kind(self) -> str:
        return "ibm_db2_databases"

    def _get_databases(self) -> list[DatabaseInfo]:
        return [{'name': self._db_name}]

    @contextlib.contextmanager
    def _get_cursor(self, _database_name):
        query, params = build_schema_tables_query(self._config)
        stmt = ibm_db.prepare(
            self._connection.conn, query, {ibm_db.SQL_ATTR_QUERY_TIMEOUT: self._config.max_query_duration}
        )
        try:
            ibm_db.execute(stmt, tuple(params))
            yield stmt
        finally:
            ibm_db.free_stmt(stmt)

    def _get_next(self, cursor: Any) -> dict | None:
        return ibm_db.fetch_assoc(cursor) or None

    def _map_row(self, database: DatabaseInfo, row: dict) -> dict:
        schema = {'name': row['schema_name'], 'owner': row['schema_owner'].strip(), 'tables': []}
        if row['table_name'] is not None:
            table = {
                'name': row['table_name'],
                'owner': row['table_owner'].strip(),
                'type': TABLE_TYPES.get(row['table_type'], row['table_type']),
                'row_count': row['row_count'] if row['row_count'] >= 0 else None,
                'columns': json.loads(row['columns']),
                'indexes': json.loads(row['indexes']),
                'foreign_keys': json.loads(row['foreign_keys']),
            }
            partition_key = json.loads(row['partition_key'])
            if partition_key:
                table['partition_key'] = partition_key
                table['num_partitions'] = row['num_partitions']
            schema['tables'].append(table)
        return {**database, 'schemas': [schema]}


class Db2SchemaCollectionJob(DBMAsyncJob):
    def __init__(self, check: IbmDb2Check, config: InstanceConfig):
        collector_config = Db2SchemaCollectorConfig(config.collect_schemas)
        super().__init__(
            check,
            config_host=config.host,
            min_collection_interval=config.min_collection_interval,
            rate_limit=1 / float(collector_config.collection_interval),
            dbms=check.dbms,
            enabled=collector_config.enabled,
            job_name='schema-collection',
        )
        self._check = check
        # The job runs on its own thread, so it can't share the check's connection.
        self._connection = Db2Connection(check, config)
        self._collector = Db2SchemaCollector(check, config.db, collector_config, self._connection)

    def run_job(self):
        if self._connection.conn is not None and not ibm_db.active(self._connection.conn):
            self._connection.close()
        if self._connection.conn is None:
            self._connection.connect()
            if self._connection.conn is None:
                return
        self._collector.collect_schemas()

    def shutdown(self) -> None:
        self._connection.close()
