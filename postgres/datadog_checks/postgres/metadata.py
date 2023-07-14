# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import time
from typing import Dict, Optional, Tuple  # noqa: F401

import psycopg
from psycopg.rows import dict_row

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
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
SELECT st.relname as name,seq_scan,idx_scan,relhasindex as hasindexes,relowner::regrole as owner,relispartition as is_partition
FROM pg_stat_all_tables st  
LEFT JOIN pg_class c ON c.relname = st.relname
AND relkind IN ('r', 'p')
WHERE schemaname = '{schemaname}'
ORDER BY coalesce(seq_scan, 0) + coalesce(idx_scan, 0) DESC;
"""

PG_TABLES_QUERY = """
SELECT tablename as name, hasindexes,relowner::regrole as owner,relispartition as is_partition, (case when relkind = 'p' then true else false end) as is_partitioned
FROM pg_tables st  
LEFT JOIN pg_class c ON relname = tablename
AND relkind IN ('r', 'p')
WHERE schemaname = '{schemaname}';
"""


SCHEMA_QUERY = """
    SELECT nspname as name, nspowner::regrole as owner FROM
    pg_namespace 
    WHERE nspname not in ('information_schema', 'pg_catalog') 
    AND nspname NOT LIKE 'pg_toast%' and nspname NOT LIKE 'pg_temp_%';
"""

PG_INDEXES_QUERY = """
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename LIKE '{tablename}';
"""

PG_CONSTRAINTS_QUERY = """
SELECT conrelid::regclass AS table_name, conname AS foreign_key, contype, pg_get_constraintdef(oid) 
FROM   pg_constraint 
WHERE  contype = 'f'
AND conrelid =
'{tablename}'::regclass; 
"""

COLUMNS_QUERY = """
SELECT attname as name, format_type(atttypid, atttypmod) AS data_type, attnotnull as not_nullable, pg_get_expr(adbin, adrelid) as default
FROM   pg_attribute LEFT JOIN pg_attrdef ad ON adrelid=attrelid
WHERE  attrelid = '{tablename}'::regclass
AND    attnum > 0
AND    NOT attisdropped;
"""
# SELECT *
# FROM   pg_attribute
# WHERE  attrelid = 'apm_activity'::regclass
# AND    attnum > 0
# AND    NOT attisdropped;


PARTITION_PARENT_AND_RANGE_QUERY = """
SELECT parent, child, pg_get_expr(c.relpartbound, c.oid, true) as partition_range
    FROM 
        (SELECT inhparent::regclass as parent, inhrelid::regclass as child 
        FROM pg_inherits 
        WHERE inhrelid = '{tablename}'::regclass::oid) AS inherits
    LEFT JOIN pg_class c ON c.oid = child::regclass::oid;
"""

PARTITION_KEY_QUERY = """
    SELECT relname, pg_get_partkeydef(oid) as partition_key 
FROM pg_class WHERE '{parent}' = relname; 
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
        if elapsed_s >= self.schemas_collection_interval:
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
        
        for database in databases:
            self._collect_info_for_database(database)
            

    def _collect_info_for_database(self, dbname):
        with self._conn_pool.get_connection(dbname, ttl_ms=self._conn_ttl_ms) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    # collect database info
                    cursor.execute(DATABASE_INFORMATION_QUERY.format(dbname=dbname))
                    rows = cursor.fetchall() 
                    postgres_logical_database = [dict(row) for row in rows]

                    self._log.warning(postgres_logical_database)
                    ## Collect user schemas. Returns
                    # name: str
                    # owner: str
                    cursor.execute(SCHEMA_QUERY)
                    rows = cursor.fetchall()
                    schemas = [dict(row) for row in rows]

                    self._log.warning(schemas)
                    for schema in schemas:
                        ## Collect tables for schema. Returns
                        # name: str 
                        # hasindexes: bool
                        # owner: str 
                        # is_partition: bool
                        cursor.execute(PG_TABLES_QUERY.format(schemaname=schema['name']))
                        rows = cursor.fetchall()
                        tables_info =  [dict(row) for row in rows]
                        self._log.warning(tables_info)
                        table_to_payloads = {}
                        partitioned_tables = []
                        for table in tables_info:
                            name = table['name']
                            self._log.warning("Parsing table {}".format(name))
                            table_to_payloads[name] = {'name': name}
                            if table["hasindexes"]:
                                cursor.execute(PG_INDEXES_QUERY.format(tablename=name))
                                rows = cursor.fetchall()
                                indexes = {row[0]:row[1] for row in rows}
                                table_to_payloads[name].update({'indexes': indexes})

                            if table['is_partition']:
                                cursor.execute(PARTITION_PARENT_AND_RANGE_QUERY.format(tablename=name))
                                row =  cursor.fetchone()
                                partition_of = row['parent']
                                partition_range = row['partition_range']
                                partitioned_tables.append(partition_of)
                                table_to_payloads[name].update({'partition_of': partition_of})
                                table_to_payloads[name].update({'partition_range': partition_range})

                            if table['is_partitioned']:
                                cursor.execute(PARTITION_KEY_QUERY.format(parent=name))
                                row = cursor.fetchone()
                                self._log.warning(row)
                                table_to_payloads[name].update({'partition_key':row['partition_key']})

                            # get foreign keys
                            cursor.execute(PG_CONSTRAINTS_QUERY.format(tablename=table['name']))
                            rows = cursor.fetchall()
                            if rows:
                                table_to_payloads[name].update({'foreign_keys': {}})
                                
                            ## Get columns
                            # name: str
                            # data_type: str 
                            # default: str
                            # is_nullable: bool
                            cursor.execute(COLUMNS_QUERY.format(tablename=name))
                            rows = cursor.fetchall()
                            self._log.warning(rows)
                            columns = [dict(row) for row in rows]
                            table_to_payloads[name].update({'columns': columns})


                        self._log.warning(table_to_payloads)


                    
                        


    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_postgres_settings(self):
        with self._check.get_main_db().cursor(row_factory=dict_row) as cursor:
            self._log.debug("Running query [%s]", PG_SETTINGS_QUERY)
            self._time_since_last_settings_query = time.time()
            cursor.execute(PG_SETTINGS_QUERY)
            rows = cursor.fetchall()
            self._log.debug("Loaded %s rows from pg_settings", len(rows))
            return [dict(row) for row in rows]
