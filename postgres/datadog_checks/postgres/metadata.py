# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import time
from typing import Dict, List, Optional, Tuple, Union  # noqa: F401

import psycopg2

from datadog_checks.postgres.cursor import CommenterDictCursor

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.postgres.util import get_list_chunks

from .util import payload_pg_version
from .version_utils import VersionUtils

# default collection intervals in seconds
DEFAULT_SETTINGS_COLLECTION_INTERVAL = 600
DEFAULT_SCHEMAS_COLLECTION_INTERVAL = 600
DEFAULT_RESOURCES_COLLECTION_INTERVAL = 300
DEFAULT_SETTINGS_IGNORED_PATTERNS = ["plpgsql%"]

# PG_SETTINGS_QURERY is used to collect all the settings from the pg_settings table
# Edge case: If source is 'session', it uses reset_val
# (which represents the value that the setting would revert to on session end or reset),
# otherwise, it uses the current setting value.
PG_SETTINGS_QUERY = """
SELECT
name,
case when source = 'session' then reset_val else setting end as setting,
source,
sourcefile,
pending_restart
FROM pg_settings
"""

DATABASE_INFORMATION_QUERY = """
SELECT db.oid                        AS id,
       datname                       AS NAME,
       pg_encoding_to_char(encoding) AS encoding,
       rolname                       AS owner,
       description
FROM   pg_catalog.pg_database db
       LEFT JOIN pg_catalog.pg_description dc
              ON dc.objoid = db.oid
       JOIN pg_roles a
         ON datdba = a.oid
WHERE  datname LIKE '{dbname}';
"""

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
WHERE  c.relkind IN ( 'r', 'p' )
       AND c.relispartition != 't'
       AND c.relnamespace = {schema_oid};
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
WHERE  c.relkind IN ( 'r' )
       AND c.relnamespace = {schema_oid};
"""


SCHEMA_QUERY = """
SELECT nsp.oid                 AS id,
       nspname             AS name,
       nspowner :: regrole AS owner
FROM   pg_namespace nsp
       LEFT JOIN pg_roles r on nsp.nspowner = r.oid
WHERE  nspname NOT IN ( 'information_schema', 'pg_catalog' )
       AND nspname NOT LIKE 'pg_toast%'
       AND nspname NOT LIKE 'pg_temp_%'
       AND r.rolname  !=       'rds_superuser'
       AND r.rolname  !=       'rdsadmin';
"""

PG_INDEXES_QUERY = """
SELECT indexname AS NAME,
       indexdef  AS definition,
       schemaname,
       tablename
FROM   pg_indexes
WHERE  schemaname='{schema_name}' AND ({table_names_like});
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

PARTITION_KEY_QUERY = """
SELECT relname,
       pg_get_partkeydef(oid) AS partition_key
FROM   pg_class
WHERE  oid in ({table_ids});
"""

NUM_PARTITIONS_QUERY = """
SELECT count(inhrelid :: regclass) AS num_partitions, inhparent as id
FROM   pg_inherits
WHERE  inhparent IN ({table_ids})
GROUP BY inhparent;
"""

PARTITION_ACTIVITY_QUERY = """
SELECT pi.inhparent :: regclass         AS parent_table_name,
       SUM(COALESCE(psu.seq_scan, 0) + COALESCE(psu.idx_scan, 0)) AS total_activity
FROM   pg_catalog.pg_stat_user_tables psu
       join pg_class pc
         ON psu.relname = pc.relname
       join pg_inherits pi
         ON pi.inhrelid = pc.oid
WHERE  pi.inhparent = {parent_oid}
GROUP  BY pi.inhparent;
"""


def agent_check_getter(self):
    return self._check


class PostgresMetadata(DBMAsyncJob):
    """
    Collects database metadata. Supports:
        1. cloud metadata collection for resource creations
        2. collection of pg_settings
    """

    def __init__(self, check, config, shutdown_callback):
        self.pg_settings_ignored_patterns = config.settings_metadata_config.get(
            "ignored_settings_patterns", DEFAULT_SETTINGS_IGNORED_PATTERNS
        )
        self.pg_settings_collection_interval = config.settings_metadata_config.get(
            "collection_interval", DEFAULT_SETTINGS_COLLECTION_INTERVAL
        )
        self.schemas_collection_interval = config.schemas_metadata_config.get(
            "collection_interval", DEFAULT_SCHEMAS_COLLECTION_INTERVAL
        )
        resources_collection_interval = config.resources_metadata_config.get(
            "collection_interval", DEFAULT_RESOURCES_COLLECTION_INTERVAL
        )

        # by default, send resources every 5 minutes
        self.collection_interval = min(
            resources_collection_interval, self.pg_settings_collection_interval, self.schemas_collection_interval
        )

        super(PostgresMetadata, self).__init__(
            check,
            rate_limit=1 / float(self.collection_interval),
            run_sync=is_affirmative(config.settings_metadata_config.get("run_sync", False)),
            enabled=is_affirmative(config.resources_metadata_config.get("enabled", True)),
            dbms="postgres",
            min_collection_interval=config.min_collection_interval,
            expected_db_exceptions=(psycopg2.errors.DatabaseError,),
            job_name="database-metadata",
            shutdown_callback=shutdown_callback,
        )
        self._check = check
        self._config = config
        self.db_pool = self._check.db_pool
        self._collect_pg_settings_enabled = is_affirmative(config.settings_metadata_config.get("enabled", False))
        self._collect_schemas_enabled = is_affirmative(config.schemas_metadata_config.get("enabled", False))
        self._is_schemas_collection_in_progress = False
        self._pg_settings_cached = None
        self._time_since_last_settings_query = 0
        self._last_schemas_query_time = 0
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
        self.tags = [t for t in self._tags if not t.startswith("dd.internal")]
        self._tags_no_db = [t for t in self.tags if not t.startswith("db:")]
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
            "dbms_version": payload_pg_version(self._check.version),
            "tags": self._tags_no_db,
            "timestamp": time.time() * 1000,
            "cloud_metadata": self._config.cloud_metadata,
            "metadata": self._pg_settings_cached,
        }
        self._check.database_monitoring_metadata(json.dumps(event, default=default_json_event_encoding))

        elapsed_s_schemas = time.time() - self._last_schemas_query_time
        if (
            self._collect_schemas_enabled
            and not self._is_schemas_collection_in_progress
            and elapsed_s_schemas >= self.schemas_collection_interval
        ):
            self._is_schemas_collection_in_progress = True
            schema_metadata = self._collect_schema_info()
            # We emit an event for each batch of tables to reduce total data in memory and keep event size reasonable
            base_event = {
                "host": self._check.resolved_hostname,
                "agent_version": datadog_agent.get_version(),
                "dbms": "postgres",
                "kind": "pg_databases",
                "collection_interval": self.schemas_collection_interval,
                "dbms_version": self._payload_pg_version(),
                "tags": self._tags_no_db,
                "cloud_metadata": self._config.cloud_metadata,
            }

            # Tuned from experiments on staging, we may want to make this dynamic based on schema size in the future
            chunk_size = 50

            for database in schema_metadata:
                dbname = database["name"]
                with self.db_pool.get_connection(dbname, self._config.idle_connection_timeout) as conn:
                    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                        for schema in database["schemas"]:
                            tables = self._query_tables_for_schema(cursor, schema["id"], dbname)
                            table_chunks = list(get_list_chunks(tables, chunk_size))

                            buffer_column_count = 0
                            tables_buffer = []

                            for tables in table_chunks:
                                table_info = self._query_table_information(cursor, schema['name'], tables)

                                tables_buffer = [*tables_buffer, *table_info]
                                for t in table_info:
                                    buffer_column_count += len(t.get("columns", []))

                                if buffer_column_count >= 100_000:
                                    self._flush_schema(base_event, database, schema, tables_buffer)
                                    tables_buffer = []
                                    buffer_column_count = 0

                            if len(tables_buffer) > 0:
                                self._flush_schema(base_event, database, schema, tables_buffer)
            self._is_schemas_collection_in_progress = False

    def _flush_schema(self, base_event, database, schema, tables):
        event = {
            **base_event,
            "metadata": [{**database, "schemas": [{**schema, "tables": tables}]}],
            "timestamp": time.time() * 1000,
        }
        json_event = json.dumps(event, default=default_json_event_encoding)
        self._log.debug("Reporting the following payload for schema collection: {}".format(json_event))
        self._check.database_monitoring_metadata(json_event)

    def _payload_pg_version(self):
        version = self._check.version
        if not version:
            return ""
        return "v{major}.{minor}.{patch}".format(major=version.major, minor=version.minor, patch=version.patch)

    def _collect_schema_info(self):
        databases = []
        if self._check.autodiscovery:
            databases = self._check.autodiscovery.get_items()
        else:
            databases.append(self._config.dbname)

        metadata = []
        for database in databases:
            metadata.append(self._collect_metadata_for_database(database))

        self._last_schemas_query_time = time.time()
        return metadata

    def _query_database_information(
        self, cursor: psycopg2.extensions.cursor, dbname: str
    ) -> Dict[str, Union[str, int]]:
        """
        Collect database info. Returns
            description: str
            name: str
            id: str
            encoding: str
            owner: str
        """
        cursor.execute(DATABASE_INFORMATION_QUERY.format(dbname=dbname))
        row = cursor.fetchone()
        return row

    def _query_schema_information(self, cursor: psycopg2.extensions.cursor, dbname: str) -> Dict[str, str]:
        """
        Collect user schemas. Returns
            id: str
            name: str
            owner: str
        """
        cursor.execute(SCHEMA_QUERY)
        rows = cursor.fetchall()
        schemas = []
        for row in rows:
            schemas.append({"id": str(row["id"]), "name": row["name"], "owner": row["owner"]})
        return schemas

    def _get_table_info(self, cursor, dbname, schema_id):
        """
        Tables will be sorted by the number of total accesses (index_rel_scans + seq_scans) and truncated to
        the max_tables limit.

        If any tables are partitioned, only the master paritition table name will be returned, and none of its children.
        """
        limit = self._config.schemas_metadata_config.get("max_tables", 300)
        if self._config.relations:
            if VersionUtils.transform_version(str(self._check.version))["version.major"] == "9":
                cursor.execute(PG_TABLES_QUERY_V9.format(schema_oid=schema_id))
            else:
                cursor.execute(PG_TABLES_QUERY_V10_PLUS.format(schema_oid=schema_id))
            rows = cursor.fetchall()
            table_info = [dict(row) for row in rows]
            return self._sort_and_limit_table_info(cursor, dbname, table_info, limit)

        else:
            # Config error should catch the case where schema collection is enabled
            # and relation metrics aren't, but adding a warning here just in case
            self._check.log.warning("Relation metrics are not configured for {dbname}, so tables cannot be collected")

    def _sort_and_limit_table_info(
        self, cursor, dbname, table_info: List[Dict[str, Union[str, bool]]], limit: int
    ) -> List[Dict[str, Union[str, bool]]]:
        def sort_tables(info):
            cache = self._check.metrics_cache.table_activity_metrics
            # partition master tables won't get any metrics reported on them,
            # so we have to grab the total partition activity
            # note: partitions don't exist in V9, so we have to check this first
            if (
                VersionUtils.transform_version(str(self._check.version))["version.major"] == "9"
                or not info["has_partitions"]
            ):
                # if we don't have metrics in our cache for this table, return 0
                table_data = cache.get(dbname, {}).get(
                    info["name"],
                    {"postgresql.index_scans": 0, "postgresql.seq_scans": 0},
                )
                return table_data.get("postgresql.index_scans", 0) + table_data.get("postgresql.seq_scans", 0)
            else:
                # get activity
                cursor.execute(PARTITION_ACTIVITY_QUERY.format(parent_oid=info["id"]))
                row = cursor.fetchone()
                return row.get("total_activity", 0) if row is not None else 0

        # We only sort to filter by top so no need to waste resources if we're going to return everything
        if len(table_info) <= limit:
            return table_info

        # if relation metrics are enabled, sorted based on last activity information
        table_info = sorted(table_info, key=sort_tables, reverse=True)
        return table_info[:limit]

    def _query_tables_for_schema(
        self, cursor: psycopg2.extensions.cursor, schema_id: str, dbname: str
    ) -> List[Dict[str, Union[str, Dict]]]:
        """
        Collect list of tables for a schema. Returns a list of dictionaries
        with key/values:
            "id": str
            "name": str
            "owner": str
            "has_indexes: bool
            "has_partitions: bool
            "toast_table": str (if associated toast table exists)
            "num_partitions": int (if has partitions)

        """
        tables_info = self._get_table_info(cursor, dbname, schema_id)
        table_payloads = []
        for table in tables_info:
            this_payload = {}
            this_payload.update({"id": str(table["id"])})
            this_payload.update({"name": table["name"]})
            this_payload.update({"owner": table["owner"]})
            this_payload.update({"has_indexes": table["has_indexes"]})
            this_payload.update({"has_partitions": table.get("has_partitions", False)})
            if table["toast_table"] is not None:
                this_payload.update({"toast_table": table["toast_table"]})

            table_payloads.append(this_payload)

        return table_payloads

    def _query_table_information(
        self, cursor: psycopg2.extensions.cursor, schema_name: str, table_info: List[Dict[str, Union[str, bool]]]
    ) -> List[Dict[str, Union[str, Dict]]]:
        """
        Collect table information . Returns a dictionary
        with key/values:
            "id": str
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
            "toast_table": str (if associated toast table exists)
            "partition_key": str (if has partitions)
            "num_partitions": int (if has partitions)
        """
        tables = {t.get("name"): {**t, "num_partitions": 0} for t in table_info}
        table_name_lookup = {t.get("id"): t.get("name") for t in table_info}
        table_ids = ",".join(["'{}'".format(t.get("id")) for t in table_info])
        table_names_like = " OR ".join(["tablename LIKE '{}%'".format(t.get("name")) for t in table_info])

        # Get indexes
        cursor.execute(PG_INDEXES_QUERY.format(schema_name=schema_name, table_names_like=table_names_like))
        rows = cursor.fetchall()
        for row in rows:
            # Partition indexes in some versions of Postgres have appended digits for each partition
            table_name = row.get("tablename")
            while tables.get(table_name) is None and len(table_name) > 1 and table_name[-1].isdigit():
                table_name = table_name[0:-1]
            if tables.get(table_name) is not None:
                tables.get(table_name)["indexes"] = tables.get(table_name).get("indexes", []) + [dict(row)]

        # Get partitions
        if VersionUtils.transform_version(str(self._check.version))["version.major"] != "9":
            cursor.execute(PARTITION_KEY_QUERY.format(table_ids=table_ids))
            rows = cursor.fetchall()
            for row in rows:
                tables.get(row.get("relname"))["partition_key"] = row.get("partition_key")

            cursor.execute(NUM_PARTITIONS_QUERY.format(table_ids=table_ids))
            rows = cursor.fetchall()
            for row in rows:
                table_name = table_name_lookup.get(str(row.get("id")))
                tables.get(table_name)["num_partitions"] = row.get("num_partitions", 0)

        # Get foreign keys
        cursor.execute(PG_CONSTRAINTS_QUERY.format(table_ids=table_ids))
        rows = cursor.fetchall()
        for row in rows:
            table_name = table_name_lookup.get(str(row.get("id")))
            tables.get(table_name)["foreign_keys"] = tables.get(table_name).get("foreign_keys", []) + [dict(row)]

        # Get columns
        cursor.execute(COLUMNS_QUERY.format(table_ids=table_ids))
        rows = cursor.fetchall()
        for row in rows:
            table_name = table_name_lookup.get(str(row.get("id")))
            tables.get(table_name)["columns"] = tables.get(table_name).get("columns", []) + [dict(row)]

        return tables.values()

    def _collect_metadata_for_database(self, dbname):
        metadata = {}
        with self.db_pool.get_connection(dbname, self._config.idle_connection_timeout) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                database_info = self._query_database_information(cursor, dbname)
                metadata.update(
                    {
                        "description": database_info["description"],
                        "name": database_info["name"],
                        "id": str(database_info["id"]),
                        "encoding": database_info["encoding"],
                        "owner": database_info["owner"],
                        "schemas": [],
                    }
                )
                schema_info = self._query_schema_information(cursor, dbname)
                for schema in schema_info:
                    metadata["schemas"].append(schema)

        return metadata

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_postgres_settings(self):
        with self._check._get_main_db() as conn:
            with conn.cursor(cursor_factory=CommenterDictCursor) as cursor:
                if self.pg_settings_ignored_patterns:
                    query = PG_SETTINGS_QUERY + " WHERE name NOT LIKE ALL(%s)"
                else:
                    query = PG_SETTINGS_QUERY
                self._log.debug(
                    "Running query [%s] and patterns are %s",
                    query,
                    self.pg_settings_ignored_patterns,
                )
                self._time_since_last_settings_query = time.time()
                cursor.execute(query, (self.pg_settings_ignored_patterns,))
                rows = cursor.fetchall()
                self._log.debug("Loaded %s rows from pg_settings", len(rows))
                return [dict(row) for row in rows]
