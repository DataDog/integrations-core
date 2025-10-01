import contextlib
import time

import orjson as json
from psycopg.rows import dict_row

from datadog_checks.postgres.postgres import PostgreSql

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent


class SchemaCollector:
    def __init__(self, check: PostgreSql):
        self._check = check
        self._log = check.log
        self._config = check._config.collect_schemas

        self._reset()

    def _reset(self):
        self._collection_started_at = None
        self._collection_payloads_count = 0
        self._queued_rows = []

    def collect_schemas(self) -> bool:
        if self._collection_started_at is not None:
            return False
        self._collection_started_at = time.time() * 1000
        databases = self._get_databases()
        for database in databases:
            with self._get_cursor(database) as cursor:
                next = self._get_next(cursor)
                while next:
                    self._queued_rows.append(next)
                    next = self._get_next(cursor)
                    is_last_payload = database is databases[-1] and next is None
                    self.maybe_flush(is_last_payload)

        self._reset()
        return True

    def maybe_flush(self, is_last_payload):
        if len(self._queued_rows) > 10 or is_last_payload:
            event = {
                "host": self._check.reported_hostname,
                "agent_version": datadog_agent.get_version(),
                "dbms": "postgres",
                "kind": "pg_databases",
                "collection_interval": self._config.collection_interval,
                "dbms_version": self._check.version,
                "tags": self._check.tags,
                "cloud_metadata": self._check.cloud_metadata,
                "metadata": self._queued_rows,
                "collection_started_at": self._collection_started_at,
            }
            self._collection_payloads_count += 1
            if is_last_payload:
                event["collection_payloads_count"] = self._collection_payloads_count
            self._check.database_monitoring_metadata(json.dumps(event))

            self._queued_rows = []

    def _get_databases(self):
        pass

    def _get_cursor(self, database):
        pass

    def _get_next(self, cursor):
        pass


PG_TABLES_QUERY_V10_PLUS = """
SELECT c.oid                 AS id,
       c.relname             AS name,
       c.relhasindex         AS has_indexes,
       c.relowner :: regrole AS owner,
       ( CASE
           WHEN c.relkind = 'p' THEN TRUE
           ELSE FALSE
         END )               AS has_partitions,
       t.relname             AS toast_table
FROM   pg_class c
       left join pg_class t
              ON c.reltoastrelid = t.oid
WHERE  c.relkind IN ( 'r', 'p', 'f' )
       AND c.relispartition != 't'
       AND c.relnamespace = {schema_oid}
       {filter};
"""

PG_TABLES_QUERY_V9 = """
SELECT c.oid                 AS id,
       c.relname             AS name,
       c.relhasindex         AS has_indexes,
       c.relowner :: regrole AS owner,
       t.relname             AS toast_table
FROM   pg_class c
       left join pg_class t
              ON c.reltoastrelid = t.oid
WHERE  c.relkind IN ( 'r', 'f' )
       AND c.relnamespace = {schema_oid}
       {filter};
"""


SCHEMA_QUERY = """
SELECT nsp.oid                 AS schema_id,
       nspname             AS schema_name,
       nspowner :: regrole AS schema_owner
FROM   pg_namespace nsp
       LEFT JOIN pg_roles r on nsp.nspowner = r.oid
WHERE  nspname NOT IN ( 'information_schema', 'pg_catalog' )
       AND nspname NOT LIKE 'pg_toast%'
       AND nspname NOT LIKE 'pg_temp_%'
"""

PG_INDEXES_QUERY = """
SELECT
    c.relname AS name,
    ix.indrelid AS table_id,
    pg_get_indexdef(c.oid) AS definition,
    ix.indisunique AS is_unique,
    ix.indisexclusion AS is_exclusion,
    ix.indimmediate AS is_immediate,
    ix.indisclustered AS is_clustered,
    ix.indisvalid AS is_valid,
    ix.indcheckxmin AS is_checkxmin,
    ix.indisready AS is_ready,
    ix.indislive AS is_live,
    ix.indisreplident AS is_replident,
    ix.indpred IS NOT NULL AS is_partial
FROM
    pg_index ix
JOIN
    pg_class c
ON
    c.oid = ix.indexrelid
WHERE
    ix.indrelid IN ({table_ids});
"""

PG_CHECK_FOR_FOREIGN_KEY = """
SELECT count(conname)
FROM   pg_constraint
WHERE  contype = 'f'
       AND conrelid = {oid};
"""

PG_CONSTRAINTS_QUERY = """
SELECT conname                   AS name,
       pg_get_constraintdef(oid) AS definition,
       conrelid AS id
FROM   pg_constraint
WHERE  contype = 'f'
       AND conrelid IN ({table_ids});
"""

COLUMNS_QUERY = """
SELECT attname                          AS name,
       Format_type(atttypid, atttypmod) AS data_type,
       NOT attnotnull                   AS nullable,
       pg_get_expr(adbin, adrelid)      AS default,
       attrelid AS id
FROM   pg_attribute
       LEFT JOIN pg_attrdef ad
              ON adrelid = attrelid
                 AND adnum = attnum
WHERE  attrelid IN ({table_ids})
       AND attnum > 0
       AND NOT attisdropped;
"""


class PostgresSchemaCollector(SchemaCollector):
    def __init__(self, check):
        super().__init__(check)

    def collect_schemas(self):
        pass

    def _get_databases(self):
        with self._check._get_main_db() as conn:
            with conn.cursor() as cursor:
                query = "SELECT datname FROM pg_database WHERE 1=1"
                for exclude_regex in self._config.exclude_databases:
                    query += " AND datname !~ '{}'".format(exclude_regex)
                for include_regex in self._config.include_databases:
                    query += " AND datname ~ '{}'".format(include_regex)
                cursor.execute(query)
                return [row[0] for row in cursor.fetchall()]

    @contextlib.contextmanager
    def _get_cursor(self, database_name):
        with self._check.db_pool.get_connection(database_name) as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                schemas_query = self._get_schemas_query()
                query = f"""
                    WITH schemas AS(
                        {schemas_query}
                    )

                    SELECT * FROM schemas
                """
                print(query)
                cursor.execute(query)
                yield cursor

    def _get_schemas_query(self):
        query = SCHEMA_QUERY
        for exclude_regex in self._config.exclude_schemas:
            query += " AND nspname !~ '{}'".format(exclude_regex)
        for include_regex in self._config.include_schemas:
            query += " AND nspname ~ '{}'".format(include_regex)
        return query

    def _get_next(self, cursor):
        return cursor.fetchone()
