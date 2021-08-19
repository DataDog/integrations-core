import psycopg2

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.db.utils import DatabaseSetting, DBMAsyncJob

PG_STAT_STATMENTS_MAX_UNKNOWN_VALUE = -1
TRACK_ACTIVITY_QUERY_SIZE_UNKNOWN_VALUE = -1


class PostgresSettings(DBMAsyncJob):
    """PostgresSettings holds settings queried from the pg_settings table."""

    # Setting names
    PG_STAT_STATEMENTS_MAX = "pg_stat_statements.max"
    TRACK_ACTIVITY_QUERY_SIZE = "track_activity_query_size"

    # Queries
    PG_SETTINGS_QUERY = ("SELECT name, setting FROM pg_settings WHERE name IN ('{}', '{}')").format(
        PG_STAT_STATEMENTS_MAX, TRACK_ACTIVITY_QUERY_SIZE
    )
    PG_STAT_STATEMENTS_COUNT_QUERY = "SELECT COUNT(*) FROM pg_stat_statements"

    # Defaults
    DEFAULT_COLLECTION_INTERVAL = 300  # 5 min in seconds

    def __init__(self, check, config, shutdown_callback=None):
        collection_interval = config.query_settings.get('collection_interval', self.DEFAULT_COLLECTION_INTERVAL)
        super(PostgresSettings, self).__init__(
            check=check,
            rate_limit=1 / collection_interval,
            run_sync=is_affirmative(config.query_settings.get('run_sync', False)),
            enabled=is_affirmative(config.query_settings.get('monitor_settings', True)),
            dbms="postgres",
            min_collection_interval=collection_interval,
            config_host=config.host,
            expected_db_exceptions=(psycopg2.DatabaseError, psycopg2.OperationalError),
            job_name="query-settings",
            shutdown_callback=shutdown_callback,
        )
        self.pg_stat_statements_max = DatabaseSetting(self.PG_STAT_STATEMENTS_MAX, PG_STAT_STATMENTS_MAX_UNKNOWN_VALUE)
        self.track_activity_query_size = DatabaseSetting(
            self.TRACK_ACTIVITY_QUERY_SIZE, TRACK_ACTIVITY_QUERY_SIZE_UNKNOWN_VALUE
        )
        self._config = config
        self._db = None

    def init(self, tags, hostname=None):
        """
        init must run regardless of the `monitor_settings` value.
        Note, a database connection must be established before this is invoked.
        """
        self._tags = tags
        if not self._db:
            self._db = self._check._get_db(self._config.dbname)
        try:
            with self._db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                self._log.debug("Running query [%s]", self.PG_SETTINGS_QUERY)
                cursor.execute(self.PG_SETTINGS_QUERY)
                rows = cursor.fetchall()
                for setting in rows:
                    name, val = setting
                    if name == self.PG_STAT_STATEMENTS_MAX:
                        self.pg_stat_statements_max.set_value(int(val))
                    elif name == self.TRACK_ACTIVITY_QUERY_SIZE:
                        self.track_activity_query_size.set_value(int(val))
        except self._expected_db_exceptions as err:
            self._log.warning("Failed to query for pg_settings: %s", repr(err))
            self._check.count(
                "dd.postgres.settings.error", 1, tags=tags + ["error:init-db-{}".format(repr(err))], hostname=hostname
            )
        except Exception as err:
            self._log.exception("Received an unexpected database exception: %s", repr(err))
            self._check.count(
                "dd.postgres.settings.error",
                1,
                tags=tags + ["error:init-db-unexpected-{}".format(repr(err))],
                hostname=hostname,
            )

    def _emit_tracked_value_metric(self, setting, value):
        self._check.count(
            "dd.postgres.settings.{}".format(setting),
            value,
            tags=self._tags,
            hostname=self._db_hostname,
        )

    def run_job(self):
        """
        run_job implements DBMAsyncJob's run_job.
        The job executes queries for settings that need to be periodically checked.
        """
        try:
            self._query_pg_stat_statements_count()
        except Exception as err:
            raise err

    def _query_pg_stat_statements_count(self):
        try:
            with self._db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                self._log.debug("Running query [%s]", self.PG_STAT_STATEMENTS_COUNT_QUERY)
                cursor.execute(self.PG_STAT_STATEMENTS_COUNT_QUERY)
                row = cursor.fetchone()
                if len(row) > 0:
                    count = row[0]
                    self.pg_stat_statements_max.set_tracked_value(count)
                    self._emit_tracked_value_metric(self.PG_STAT_STATEMENTS_MAX, count)
        except Exception as err:
            self._log.warning("Failed to query for pg_stat_statements count: %s", repr(err))
            raise err
