import time


class SchemaCollector:
    def __init__(self, check, config):
        self._check = check
        self._log = check.log
        self._config = config

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
    def __init__(self, check, config):
        super().__init__(check, config)

    def collect_schemas(self):
        pass

    def _get_databases(self):
        cursor = self._check.get_main_db().cursor()
        cursor.execute("SELECT datname FROM pg_database")
        return [row[0] for row in cursor.fetchall()]

    def _get_cursor(self):
        cursor = self._check.db_pool.get_connection(self._config.dbname).cursor()
        cursor.execute("SELECT nspname FROM pg_namespace"
        "MONSTER SQL STATEMENT GOES HERE"
        )
        return cursor

    def _get_next(self, cursor):
        return cursor.fetchone()