# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
from typing import Dict, List, Optional, Tuple, Union  # noqa: F401

import psycopg
from psycopg.rows import dict_row

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method

# default collection intervals in seconds
DEFAULT_SETTINGS_COLLECTION_INTERVAL = 600
DEFAULT_SCHEMAS_COLLECTION_INTERVAL = 600
DEFAULT_RESOURCES_COLLECTION_INTERVAL = 300

PG_SETTINGS_QUERY = """
SELECT name, setting FROM pg_settings
"""

DATABASE_INFORMATION_QUERY = """
SELECT db.oid as id, datname as name, pg_encoding_to_char(encoding) as encoding, rolname as owner, description
    FROM pg_catalog.pg_database db
    LEFT JOIN pg_catalog.pg_description dc ON dc.objoid = db.oid
    JOIN pg_roles a on datdba = a.oid
    WHERE datname LIKE '{dbname}';
"""


PG_STAT_TABLES_QUERY = """
SELECT st.relname as name,seq_scan,idx_scan,c.relhasindex as hasindexes,c.relowner::regrole as owner,
(CASE WHEN c.relkind = 'p' THEN true ELSE false END) AS has_partitions,
(CASE WHEN pg_relation_size(c.reltoastrelid) > 500000 THEN t.relname ELSE null END) AS toast_table
FROM pg_class c
LEFT JOIN pg_stat_all_tables st ON c.relname = st.relname
LEFT JOIN pg_class t on c.reltoastrelid = t.oid
WHERE schemaname = '{schemaname}'
AND c.relkind IN ('r', 'p')
AND c.relispartition != 't'
ORDER BY coalesce(seq_scan, 0) + coalesce(idx_scan, 0) DESC;
"""

PG_TABLES_QUERY = """
SELECT tablename as name, hasindexes, c.relowner::regrole AS owner,
(CASE WHEN c.relkind = 'p' THEN true ELSE false END) AS has_partitions,
(CASE WHEN pg_relation_size(c.reltoastrelid) > 500000 THEN t.relname ELSE null END) AS toast_table
FROM pg_tables st
LEFT JOIN pg_class c ON relname = tablename
LEFT JOIN pg_class t on c.reltoastrelid = t.oid
WHERE c.relkind IN ('r', 'p')
AND c.relispartition != 't'
AND schemaname = '{schemaname}';
"""

SCHEMA_QUERY = """
    SELECT nspname as name, nspowner::regrole as owner FROM
    pg_namespace
    WHERE nspname not in ('information_schema', 'pg_catalog')
    AND nspname NOT LIKE 'pg_toast%' and nspname NOT LIKE 'pg_temp_%';
"""

PG_INDEXES_QUERY = """
SELECT indexname as name, indexdef as definition
FROM pg_indexes
WHERE tablename LIKE '{tablename}';
"""

PG_CONSTRAINTS_QUERY = """
SELECT conname AS name, pg_get_constraintdef(oid) as definition
FROM   pg_constraint
WHERE  contype = 'f'
AND conrelid =
'{tablename}'::regclass;
"""

COLUMNS_QUERY = """
SELECT attname as name,
format_type(atttypid, atttypmod) AS data_type,
NOT attnotnull as nullable, pg_get_expr(adbin, adrelid) as default
FROM   pg_attribute LEFT JOIN pg_attrdef ad ON adrelid=attrelid AND adnum=attnum
WHERE  attrelid = '{tablename}'::regclass
AND    attnum > 0
AND    NOT attisdropped;
"""

PARTITION_KEY_QUERY = """
    SELECT relname, pg_get_partkeydef(oid) as partition_key
FROM pg_class WHERE '{parent}' = relname;
"""

NUM_PARTITIONS_QUERY = """
SELECT count(inhrelid::regclass) as num_partitions
        FROM pg_inherits
        WHERE inhparent = '{parent}'::regclass::oid
"""

PARTITION_ACTIVITY_QUERY = """
SELECT
   pi.inhparent::regclass AS parent_table_name,
   SUM(psu.seq_scan + psu.idx_scan) AS total_activity
FROM pg_catalog.pg_stat_user_tables psu
   JOIN pg_class pc ON psu.relname = pc.relname
   JOIN pg_inherits pi ON pi.inhrelid = pc.oid
WHERE pi.inhparent = '{parent}'::regclass::oid
GROUP BY pi.inhparent;
"""


def agent_check_getter(self):
    return self._check


class PostgresMetadata(DBMAsyncJob):
    """
    Collects database metadata. Supports:
        1. cloud metadata collection for resource creations
        2. collection of pg_settings
    """

    def __init__(self, check, config):
        self.pg_settings_collection_interval = config.settings_metadata_config.get(
            'collection_interval', DEFAULT_SETTINGS_COLLECTION_INTERVAL
        )
        self.schemas_collection_interval = config.schemas_metadata_config.get(
            'collection_interval', DEFAULT_SETTINGS_COLLECTION_INTERVAL
        )

        collection_interval = config.resources_metadata_config.get(
            'collection_interval', DEFAULT_RESOURCES_COLLECTION_INTERVAL
        )

        # by default, send resources every 5 minutes
        self.collection_interval = min(collection_interval, self.pg_settings_collection_interval)

        super(PostgresMetadata, self).__init__(
            check,
            rate_limit=1 / self.collection_interval,
            run_sync=is_affirmative(config.settings_metadata_config.get('run_sync', False)),
            enabled=is_affirmative(config.resources_metadata_config.get('enabled', True)),
            dbms="postgres",
            min_collection_interval=config.min_collection_interval,
            expected_db_exceptions=(psycopg.errors.DatabaseError,),
            job_name="database-metadata",
        )
        self._check = check
        self._config = config
        self.db_pool = self._check.db_pool
        self._collect_pg_settings_enabled = is_affirmative(config.settings_metadata_config.get('enabled', False))
        self._collect_schemas_enabled = is_affirmative(config.schemas_metadata_config.get('enabled', False))
        self._pg_settings_cached = None
        self._time_since_last_settings_query = 0
        self._time_since_last_schemas_query = 0
        self._conn_ttl_ms = self._config.idle_connection_timeout
        self._tags_no_db = None
        self.tags = None

    def _dbtags(self, db, *extra_tags):
        """
        Returns the default instance tags with the initial "db" tag replaced with the provided tag
        """
        t = ["db:" + db]
        if extra_tags:
            t.extend(extra_tags)
        if self._tags_no_db:
            t.extend(self._tags_no_db)
        return t

    def run_job(self):
        # do not emit any dd.internal metrics for DBM specific check code
        self.tags = [t for t in self._tags if not t.startswith('dd.internal')]
        self._tags_no_db = [t for t in self.tags if not t.startswith('db:')]
        self.report_postgres_metadata()
        self._check.db_pool.prune_connections()

    @tracked_method(agent_check_getter=agent_check_getter)
    def report_postgres_metadata(self):
        # Only query for settings if configured to do so &&
        # don't report more often than the configured collection interval
        elapsed_s = time.time() - self._time_since_last_settings_query
        if elapsed_s >= self.pg_settings_collection_interval and self._collect_pg_settings_enabled:
            self._pg_settings_cached = self._collect_postgres_settings()
        event = {
            "host": self._check.resolved_hostname,
            "agent_version": datadog_agent.get_version(),
            "dbms": "postgres",
            "kind": "pg_settings",
            "collection_interval": self.collection_interval,
            'dbms_version': self._payload_pg_version(),
            "tags": self._tags_no_db,
            "timestamp": time.time() * 1000,
            "cloud_metadata": self._config.cloud_metadata,
            "metadata": self._pg_settings_cached,
        }
        self._check.database_monitoring_metadata(json.dumps(event, default=default_json_event_encoding))

        elapsed_s = time.time() - self._time_since_last_schemas_query
        if elapsed_s >= self.schemas_collection_interval and self._collect_schemas_enabled:
            self._collect_schema_info()

    def _payload_pg_version(self):
        version = self._check.version
        if not version:
            return ""
        return 'v{major}.{minor}.{patch}'.format(major=version.major, minor=version.minor, patch=version.patch)

    def _collect_schema_info(self):
        databases = []
        if self._check.autodiscovery:
            databases = self._check.autodiscovery.get_items()
        elif self._config.dbname != 'postgres':
            databases.append(self._config.dbname)
        else:
            # if we are only connecting to 'postgres' database, not worth reporting data model
            return

        metadata = []
        for database in databases:
            metadata.append(self._collect_metadata_for_database(database))
        event = {
            "host": self._check.resolved_hostname,
            "agent_version": datadog_agent.get_version(),
            "dbms": "postgres",
            "kind": "pg_databases",
            "collection_interval": self.schemas_collection_interval,
            "dbms_version": self._payload_pg_version(),
            "tags": self._tags_no_db,
            "timestamp": time.time() * 1000,
            "cloud_metadata": self._config.cloud_metadata,
            "metadata": metadata,
        }
        self._check.database_monitoring_metadata(json.dumps(event, default=default_json_event_encoding))

    def _query_database_information(
        self, cursor: psycopg2.extensions.cursor, dbname: str
    ) -> Dict[str, Union[str, int]]:
        """
        Collect database info. Returns
            description: str
            name: str
            id: int
            encoding: str
            owner: str
        """
        cursor.execute(DATABASE_INFORMATION_QUERY.format(dbname=dbname))
        row = cursor.fetchone()
        print(row)
        return row

    def _query_schema_information(self, cursor: psycopg2.extensions.cursor, dbname: str) -> Dict[str, str]:
        """
        Collect user schemas. Returns
            name: str
            owner: str
        """
        cursor.execute(SCHEMA_QUERY)
        rows = cursor.fetchall()
        schemas = [dict(row) for row in rows]
        return schemas

    def _get_table_info(self, cursor, dbname, schemaname, limit):
        """
        If relation metrics is enabled, sort tables by the number of total accesses (index_rel_scans + seq_scans).
        If they are not enabled, the table list will be retrieved from pg_stat_all_tables and sorted in the query.

        If any tables are partitioned, the partitioned table will be returned and not counted against the limit.
        However, partitions of the table are counted against the limit.
        """
        if self._config.relations:
            cursor.execute(PG_TABLES_QUERY.format(schemaname=schemaname))
            rows = cursor.fetchall()
            table_info = [dict(row) for row in rows]
            return self._sort_and_limit_table_info(cursor, dbname, table_info, limit)

        else:
            raise NotImplementedError()
            # table_info = cursor.execute(PG_STAT_TABLES_QUERY.format(schemaname=schemaname))

    def _sort_and_limit_table_info(
        self, cursor, dbname, table_info: List[Dict[str, Union[str, bool]]], limit: int
    ) -> List[Dict[str, Union[str, bool]]]:
        def sort_tables(info):
            cache = self._check.metrics_cache.table_activity_metrics
            # partition master tables won't get any metrics reported on them,
            # so we have to grab the total partition activity
            if not info["has_partitions"]:
                return (
                    cache[dbname][info['name']]['postgresql.index_scans']
                    + cache[dbname][info['name']]['postgresql.seq_scans']
                )
            else:
                # get activity
                cursor.execute(PARTITION_ACTIVITY_QUERY.format(parent=info['name']))
                row = cursor.fetchone()
                return row['total_activity']

        # if relation metrics are enabled, sorted based on last activity information
        table_metrics_cache = self._check.metrics_cache.table_activity_metrics
        self._log.warning(table_metrics_cache)

        table_info = sorted(table_info, key=sort_tables, reverse=True)
        return table_info[:limit]

    def _query_table_information_for_schema(
        self, cursor: psycopg2.extensions.cursor, schemaname: str, dbname: str
    ) -> List[Dict[str, Union[str, Dict]]]:
        """
        Collect table information per schema. Returns a list of dictionaries
        with key/values:
            "name": str
            "owner": str
            "foreign_keys": dict (if has foreign keys)
                name: str
                definition: str
            "indexes": dict (if has indexes)
                name: str
                definition: str
            "columns": dict
                name: str
                data_type: str
                default: str
                nullable: bool
            "toast_table": str (if associated toast table is > 500kb)
            "partition_key": str (if has partitions)
            "num_partitions": int (if has partitions)
        """
        tables_info = self._get_table_info(cursor, dbname, schemaname, 1000)
        self._log.warning(tables_info)
        table_payloads = []
        for table in tables_info:
            this_payload = {}
            name = table['name']
            self._log.warning("Parsing table {}".format(name))
            this_payload.update({'name': name})
            if table["hasindexes"]:
                cursor.execute(PG_INDEXES_QUERY.format(tablename=name))
                rows = cursor.fetchall()
                indexes = {row[0]: row[1] for row in rows}
                this_payload.update({'indexes': indexes})

            if table['has_partitions']:
                cursor.execute(PARTITION_KEY_QUERY.format(parent=name))
                row = cursor.fetchone()
                self._log.warning(row)
                this_payload.update({'partition_key': row['partition_key']})

                cursor.execute(NUM_PARTITIONS_QUERY.format(parent=name))
                row = cursor.fetchone()
                this_payload.update({'num_partitions': row['num_partitions']})

            if table['toast_table'] is not None:
                this_payload.update({'toast_table': row['toast_table']})

            # Get foreign keys
            cursor.execute(PG_CONSTRAINTS_QUERY.format(tablename=table['name']))
            rows = cursor.fetchall()
            self._log.warning("foreign keys {}".format(rows))
            if rows:
                this_payload.update({'foreign_keys': {}})

            # Get columns
            cursor.execute(COLUMNS_QUERY.format(tablename=name))
            rows = cursor.fetchall()
            self._log.warning(rows)
            columns = [dict(row) for row in rows]
            this_payload.update({'columns': columns})

            table_payloads.append(this_payload)

        return table_payloads

    def _collect_metadata_for_database(self, dbname):
        metadata = {}
        with self.db_pool.get_connection(dbname, self._config.idle_connection_timeout) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                database_info = self._query_database_information(cursor, dbname)
                metadata.update(
                    {
                        "description": database_info['description'],
                        "name": database_info['name'],
                        "id": database_info['id'],
                        "encoding": database_info['encoding'],
                        "owner": database_info['owner'],
                        "schemas": [],
                    }
                )
                self._log.warning(database_info)
                schema_info = self._query_schema_information(cursor, dbname)
                self._log.warning(schema_info)
                for schema in schema_info:
                    tables_info = self._query_table_information_for_schema(cursor, schema['name'], dbname)
                    self._log.warning(tables_info)
                    metadata['schemas'].append(
                        {"name": schema['name'], "owner": schema['owner'], "tables": tables_info}
                    )

        return metadata

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_postgres_settings(self):
        with self._check.get_main_db().cursor(row_factory=dict_row) as cursor:
            self._log.debug("Running query [%s]", PG_SETTINGS_QUERY)
            self._time_since_last_settings_query = time.time()
            cursor.execute(PG_SETTINGS_QUERY)
            rows = cursor.fetchall()
            self._log.debug("Loaded %s rows from pg_settings", len(rows))
            return [dict(row) for row in rows]
