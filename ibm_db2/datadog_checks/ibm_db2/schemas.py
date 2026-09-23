# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any, Iterator

import ibm_db

from datadog_checks.base.utils.db.schemas import DatabaseInfo, SchemaCollector, SchemaCollectorConfig
from datadog_checks.base.utils.db.utils import DBMAsyncJob

from .connection import Db2Connection

if TYPE_CHECKING:
    from .config_models import InstanceConfig
    from .config_models.instance import CollectSchemas
    from .ibm_db2 import IbmDb2Check

TableKey = tuple[str, str]

# Db2 reserves schema names starting with SYS for the catalog; NULLID and SQLJ hold driver packages.
SYSTEM_SCHEMAS_FILTER = "s.SCHEMANAME NOT LIKE 'SYS%' AND s.SCHEMANAME NOT IN ('NULLID', 'SQLJ')"

# Schemas left-joined to their tables so that empty schemas are still reported, capped at
# `max_tables` rows. Every query below starts from this CTE so they all see the same objects.
LIMITED_OBJECTS_CTE = """
schemas AS (
    SELECT s.SCHEMANAME AS schema_name, s.OWNER AS schema_owner
    FROM SYSCAT.SCHEMATA s
    WHERE {system_schemas_filter}{schema_filters}
),
tables AS (
    SELECT t.TABSCHEMA, t.TABNAME, t.OWNER, t.TYPE, t.CARD
    FROM SYSCAT.TABLES t
    WHERE t.TYPE IN ('T', 'N'){table_filters}
),
limited_objects AS (
    SELECT schemas.schema_name, schemas.schema_owner,
           tables.TABNAME AS table_name, tables.OWNER AS table_owner,
           tables.TYPE AS table_type, tables.CARD AS row_count
    FROM schemas
    LEFT JOIN tables ON tables.TABSCHEMA = schemas.schema_name
    ORDER BY schemas.schema_name, tables.TABNAME
    FETCH FIRST {max_tables} ROWS ONLY
)
"""

OBJECTS_QUERY = """
WITH {limited_objects_cte},
limited_columns AS (
    SELECT c.TABSCHEMA, c.TABNAME, c.COLNAME, c.TYPENAME, c.LENGTH, c.SCALE, c.NULLS, c.DEFAULT, c.COLNO,
           ROW_NUMBER() OVER (PARTITION BY c.TABSCHEMA, c.TABNAME ORDER BY c.COLNO) AS rn
    FROM SYSCAT.COLUMNS c
    JOIN limited_objects lo ON lo.schema_name = c.TABSCHEMA AND lo.table_name = c.TABNAME
)
SELECT lo.schema_name, lo.schema_owner, lo.table_name, lo.table_owner, lo.table_type, lo.row_count,
       (SELECT COUNT(*)
        FROM SYSCAT.DATAPARTITIONS p
        WHERE p.TABSCHEMA = lo.schema_name AND p.TABNAME = lo.table_name) AS num_partitions,
       lc.COLNAME AS column_name, lc.TYPENAME AS data_type, lc.LENGTH AS length, lc.SCALE AS scale,
       lc.NULLS AS nulls, lc.DEFAULT AS column_default
FROM limited_objects lo
LEFT JOIN limited_columns lc
       ON lc.TABSCHEMA = lo.schema_name AND lc.TABNAME = lo.table_name AND lc.rn <= {max_columns}
ORDER BY lo.schema_name, lo.table_name, lc.COLNO
"""

INDEX_COLUMNS_QUERY = """
WITH {limited_objects_cte}
SELECT i.TABSCHEMA AS schema_name, i.TABNAME AS table_name, i.INDSCHEMA AS index_schema, i.INDNAME AS name,
       i.UNIQUERULE AS unique_rule, i.INDEXTYPE AS index_type,
       ic.COLNAME AS column_name, ic.COLORDER AS column_order
FROM SYSCAT.INDEXES i
JOIN limited_objects lo ON lo.schema_name = i.TABSCHEMA AND lo.table_name = i.TABNAME
JOIN SYSCAT.INDEXCOLUSE ic ON ic.INDSCHEMA = i.INDSCHEMA AND ic.INDNAME = i.INDNAME
ORDER BY i.TABSCHEMA, i.TABNAME, i.INDSCHEMA, i.INDNAME, ic.COLSEQ
"""

FOREIGN_KEY_COLUMNS_QUERY = """
WITH {limited_objects_cte}
SELECT r.TABSCHEMA AS schema_name, r.TABNAME AS table_name, r.CONSTNAME AS name,
       r.REFTABSCHEMA AS referenced_schema, r.REFTABNAME AS referenced_table,
       r.DELETERULE AS delete_rule, r.UPDATERULE AS update_rule,
       k.COLNAME AS column_name, rk.COLNAME AS referenced_column_name
FROM SYSCAT.REFERENCES r
JOIN limited_objects lo ON lo.schema_name = r.TABSCHEMA AND lo.table_name = r.TABNAME
JOIN SYSCAT.KEYCOLUSE k ON k.CONSTNAME = r.CONSTNAME AND k.TABSCHEMA = r.TABSCHEMA AND k.TABNAME = r.TABNAME
LEFT JOIN SYSCAT.KEYCOLUSE rk
       ON rk.CONSTNAME = r.REFKEYNAME AND rk.TABSCHEMA = r.REFTABSCHEMA AND rk.TABNAME = r.REFTABNAME
      AND rk.COLSEQ = k.COLSEQ
ORDER BY r.TABSCHEMA, r.TABNAME, r.CONSTNAME, k.COLSEQ
"""

PARTITION_KEY_QUERY = """
WITH {limited_objects_cte}
SELECT e.TABSCHEMA AS schema_name, e.TABNAME AS table_name,
       CAST(e.DATAPARTITIONEXPRESSION AS VARCHAR(1024)) AS expression
FROM SYSCAT.DATAPARTITIONEXPRESSION e
JOIN limited_objects lo ON lo.schema_name = e.TABSCHEMA AND lo.table_name = e.TABNAME
ORDER BY e.TABSCHEMA, e.TABNAME, e.DATAPARTITIONKEYSEQ
"""

TABLE_TYPES = {'T': 'TABLE', 'N': 'NICKNAME'}

# https://www.ibm.com/docs/en/db2/11.5?topic=views-syscatindexcoluse
INDEX_COLUMN_ORDERS = {'A': 'ASC', 'D': 'DESC', 'I': 'INCLUDE'}

# https://www.ibm.com/docs/en/db2/11.5?topic=views-syscatreferences
REFERENTIAL_RULES = {'A': 'NO ACTION', 'C': 'CASCADE', 'N': 'SET NULL', 'R': 'RESTRICT'}


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


class Db2SchemaQueryBuilder:
    def __init__(self, config: Db2SchemaCollectorConfig):
        self._config = config

    def _limited_objects_cte(self) -> tuple[str, list[str]]:
        config = self._config
        schema_filters = regex_exclude_clauses('s.SCHEMANAME', config.exclude_schemas) + regex_include_clause(
            's.SCHEMANAME', config.include_schemas
        )
        table_filters = regex_exclude_clauses('t.TABNAME', config.exclude_tables) + regex_include_clause(
            't.TABNAME', config.include_tables
        )
        cte = LIMITED_OBJECTS_CTE.format(
            system_schemas_filter=SYSTEM_SCHEMAS_FILTER,
            schema_filters=schema_filters,
            table_filters=table_filters,
            max_tables=config.max_tables,
        ).strip()
        params = [*config.exclude_schemas, *config.include_schemas, *config.exclude_tables, *config.include_tables]
        return cte, params

    def build(self, query: str, **kwargs: Any) -> tuple[str, list[str]]:
        cte, params = self._limited_objects_cte()
        return query.format(limited_objects_cte=cte, **kwargs), params


class Db2SchemaCollector(SchemaCollector):
    _check: IbmDb2Check
    _config: Db2SchemaCollectorConfig

    def __init__(self, check: IbmDb2Check, db_name: str, config: Db2SchemaCollectorConfig, connection: Db2Connection):
        super().__init__(check, config)
        self._db_name = db_name
        self._connection = connection
        self._query_builder = Db2SchemaQueryBuilder(config)

    @property
    def kind(self) -> str:
        return "ibm_db2_databases"

    def _get_databases(self) -> list[DatabaseInfo]:
        return [{'name': self._db_name}]

    def _execute(self, query: str, params: list[str]) -> Any:
        stmt = ibm_db.prepare(
            self._connection.conn, query, {ibm_db.SQL_ATTR_QUERY_TIMEOUT: self._config.max_query_duration}
        )
        ibm_db.execute(stmt, tuple(params))
        return stmt

    def _fetch_rows_by_table(self, query: str) -> dict[TableKey, list[dict]]:
        stmt = self._execute(*self._query_builder.build(query))
        try:
            rows_by_table: dict[TableKey, list[dict]] = {}
            row = ibm_db.fetch_assoc(stmt)
            while row is not False:
                rows_by_table.setdefault((row['schema_name'], row['table_name']), []).append(row)
                row = ibm_db.fetch_assoc(stmt)
            return rows_by_table
        finally:
            ibm_db.free_stmt(stmt)

    def _fetch_indexes(self) -> dict[TableKey, list[dict]]:
        indexes_by_table = {}
        for key, rows in self._fetch_rows_by_table(INDEX_COLUMNS_QUERY).items():
            indexes: dict[tuple[str, str], dict] = {}
            for row in rows:
                index = indexes.setdefault(
                    (row['index_schema'], row['name']),
                    {
                        'schema': row['index_schema'].strip(),
                        'name': row['name'],
                        'is_unique': row['unique_rule'] in ('P', 'U'),
                        'is_primary': row['unique_rule'] == 'P',
                        'index_type': row['index_type'].strip(),
                        'columns': [],
                    },
                )
                index['columns'].append(
                    {'name': row['column_name'], 'order': INDEX_COLUMN_ORDERS.get(row['column_order'])}
                )
            indexes_by_table[key] = list(indexes.values())
        return indexes_by_table

    def _fetch_foreign_keys(self) -> dict[TableKey, list[dict]]:
        foreign_keys_by_table = {}
        for key, rows in self._fetch_rows_by_table(FOREIGN_KEY_COLUMNS_QUERY).items():
            foreign_keys: dict[str, dict] = {}
            for row in rows:
                foreign_key = foreign_keys.setdefault(
                    row['name'],
                    {
                        'name': row['name'],
                        'columns': [],
                        'referenced_schema': row['referenced_schema'].strip(),
                        'referenced_table': row['referenced_table'],
                        'referenced_columns': [],
                        'delete_rule': REFERENTIAL_RULES.get(row['delete_rule']),
                        'update_rule': REFERENTIAL_RULES.get(row['update_rule']),
                    },
                )
                foreign_key['columns'].append(row['column_name'])
                foreign_key['referenced_columns'].append(row['referenced_column_name'])
            foreign_keys_by_table[key] = list(foreign_keys.values())
        return foreign_keys_by_table

    def _fetch_partition_keys(self) -> dict[TableKey, list[str]]:
        return {
            key: [row['expression'] for row in rows]
            for key, rows in self._fetch_rows_by_table(PARTITION_KEY_QUERY).items()
        }

    @contextlib.contextmanager
    def _get_cursor(self, _database_name):
        indexes = self._fetch_indexes()
        foreign_keys = self._fetch_foreign_keys()
        partition_keys = self._fetch_partition_keys()
        stmt = self._execute(*self._query_builder.build(OBJECTS_QUERY, max_columns=self._config.max_columns))
        try:
            yield self._iter_objects(stmt, indexes, foreign_keys, partition_keys)
        finally:
            ibm_db.free_stmt(stmt)

    def _iter_objects(
        self,
        stmt: Any,
        indexes: dict[TableKey, list[dict]],
        foreign_keys: dict[TableKey, list[dict]],
        partition_keys: dict[TableKey, list[str]],
    ) -> Iterator[dict]:
        """
        Group the ordered (schema, table, column) rows into one object per table, or per empty schema.
        """
        row = ibm_db.fetch_assoc(stmt)
        while row is not False:
            key = (row['schema_name'], row['table_name'])
            obj = {**row, 'columns': []}
            while row is not False and (row['schema_name'], row['table_name']) == key:
                if row['column_name'] is not None:
                    obj['columns'].append(
                        {
                            'name': row['column_name'],
                            'data_type': row['data_type'],
                            'length': row['length'],
                            'scale': row['scale'],
                            'nullable': row['nulls'] == 'Y',
                            'default': row['column_default'],
                        }
                    )
                row = ibm_db.fetch_assoc(stmt)
            obj['indexes'] = indexes.get(key, [])
            obj['foreign_keys'] = foreign_keys.get(key, [])
            obj['partition_key'] = partition_keys.get(key)
            yield obj

    def _get_next(self, cursor):
        return next(cursor, None)

    def _map_row(self, database: DatabaseInfo, obj: dict) -> dict:
        schema = {'name': obj['schema_name'], 'owner': obj['schema_owner'].strip(), 'tables': []}
        if obj['table_name'] is not None:
            table = {
                'name': obj['table_name'],
                'owner': obj['table_owner'].strip(),
                'type': TABLE_TYPES.get(obj['table_type'], obj['table_type']),
                'row_count': obj['row_count'] if obj['row_count'] >= 0 else None,
                'columns': obj['columns'],
                'indexes': obj['indexes'],
                'foreign_keys': obj['foreign_keys'],
            }
            if obj['partition_key']:
                table['partition_key'] = obj['partition_key']
                table['num_partitions'] = obj['num_partitions']
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
