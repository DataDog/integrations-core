import psycopg2

from datadog_checks.base.log import get_check_logger
from datadog_checks.base.utils.db.utils import resolve_db_host

PG_STAT_STATEMENTS_MAX = "pg_stat_statements.max"
PG_STAT_STATEMENTS_COUNT = "pg_stat_statements_count"

TRACK_ACTIVITY_QUERY_SIZE = "track_activity_query_size"
TRACK_ACTIVITY_QUERY_SIZE_UNKNOWN_VALUE = -1


class MonitorSettings:

    PG_STAT_STATEMENTS_COUNT_QUERY = "SELECT COUNT(*) FROM pg_stat_statements"

    def __init__(self, check, config):
        self.pg_stat_statements_count = None

        self._check = check
        self._config = config
        self._db = None
        self._db_hostname = None
        self._tags = None
        self._log = get_check_logger()
        self._expected_db_exceptions = (psycopg2.DatabaseError, psycopg2.OperationalError)

    def query(self, tags):
        if not self._db:
            self._db = self._check._get_db(self._config.dbname)
            self._db_hostname = resolve_db_host(self._config.host)
        self._tags = tags
        self._query_pg_stat_statements_count()

    def _emit_tracked_value_metric(self, setting, value):
        self._check.count(
            "postgresql.settings.{}".format(setting),
            value,
            tags=self._tags,
            hostname=self._db_hostname,
        )

    def _query_pg_stat_statements_count(self):
        try:
            with self._db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                self._log.debug("Running query [%s]", self.PG_STAT_STATEMENTS_COUNT_QUERY)
                cursor.execute(self.PG_STAT_STATEMENTS_COUNT_QUERY)
                row = cursor.fetchone()
                if len(row) > 0:
                    count = row[0]
                    self.pg_stat_statements_count = count
                    self._emit_tracked_value_metric(PG_STAT_STATEMENTS_COUNT, count)
        except self._expected_db_exceptions as err:
            self._log.warning("Failed to query for pg_stat_statements count: %s", repr(err))
        except Exception as err:
            self._log.exception("Received an unexpected database exception: %s", repr(err))
