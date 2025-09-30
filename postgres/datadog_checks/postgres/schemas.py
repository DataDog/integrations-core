import time

import orjson as json

from datadog_checks.postgres.postgres import PostgreSql

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent


class SchemaCollector:
    def __init__(self, check: PostgreSql):
        self._check = check
        self._log = check.log
        self._config = check._config.schemas_metadata_config

        self._include_databases = self._config.get("include_databases", [])
        self._include_schemas = self._config.get("include_schemas", [])
        self._include_tables = self._config.get("include_tables", [])
        self._exclude_databases = self._config.get("exclude_databases", [])
        self._exclude_schemas = self._config.get("exclude_schemas", [])
        self._exclude_tables = self._config.get("exclude_tables", [])

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
                "collection_interval": self._config.schemas_metadata_config.get("collection_interval"),
                "dbms_version": self._check.version,
                "tags": self._check.tags,
                "cloud_metadata": self._check.cloud_metadata,
                "metadata": self._queued_rows,
                "collection_started_at": self._collection_started_at,
            }
            self._collection_payloads_count += 1
            if is_last_payload:
                event["collection_payloads_count"] = self._payloads_count
            self._check.database_monitoring_metadata(json.dumps(event))

            self._queued_rows = []

    def _get_databases(self):
        pass

    def _get_cursor(self, database):
        pass

    def _get_next(self, cursor):
        pass


class PostgresSchemaCollector(SchemaCollector):
    def __init__(self, check):
        super().__init__(check)

    def collect_schemas(self):
        pass

    def _get_databases(self):
        with self._check._get_main_db() as conn:
            with conn.cursor() as cursor:
                query = "SELECT datname FROM pg_database WHERE 1=1"
                for exclude_regex in self._exclude_databases:
                    query += " AND datname !~ '{}'".format(exclude_regex)
                for include_regex in self._include_databases:
                    query += " AND datname ~ '{}'".format(include_regex)
                cursor.execute(query)
                return [row[0] for row in cursor.fetchall()]

    def _get_cursor(self):
        cursor = self._check.db_pool.get_connection(self._config.dbname).cursor()
        cursor.execute("SELECT nspname FROM pg_namespaceMONSTER SQL STATEMENT GOES HERE")
        return cursor

    def _get_next(self, cursor):
        return cursor.fetchone()
