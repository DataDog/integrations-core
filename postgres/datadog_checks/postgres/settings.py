import psycopg2

from datadog_checks.base.log import get_check_logger
from datadog_checks.base.utils.db.utils import resolve_db_host

PG_STAT_STATEMENTS_MAX = "pg_stat_statements.max"
PG_STAT_STATEMENTS_MAX_UNKNOWN_VALUE = -1

TRACK_ACTIVITY_QUERY_SIZE = "track_activity_query_size"
TRACK_ACTIVITY_QUERY_SIZE_UNKNOWN_VALUE = -1


class PostgresSettings:
    """PostgresSettings holds settings queried from the pg_settings table."""

    PG_SETTINGS_QUERY = ("SELECT name, setting FROM pg_settings WHERE name IN ('{}', '{}')").format(
        PG_STAT_STATEMENTS_MAX, TRACK_ACTIVITY_QUERY_SIZE
    )
    PG_STAT_STATEMENTS_COUNT_QUERY = "SELECT COUNT(*) FROM pg_stat_statements"

    def __init__(self, check, config):
        self.settings = {
            PG_STAT_STATEMENTS_MAX: {
                'name': PG_STAT_STATEMENTS_MAX,
                'value': PG_STAT_STATEMENTS_MAX_UNKNOWN_VALUE,
                'tracked_value': None,
            },
            TRACK_ACTIVITY_QUERY_SIZE: {
                'name': TRACK_ACTIVITY_QUERY_SIZE,
                'value': TRACK_ACTIVITY_QUERY_SIZE_UNKNOWN_VALUE,
                'tracked_value': None,
            },
        }
        self._check = check
        self._config = config
        self._db = None
        self._db_hostname = None
        self._tags = None
        self._log = get_check_logger()
        self._expected_db_exceptions = (psycopg2.DatabaseError, psycopg2.OperationalError)

    def _init(self):
        self._db = self._check._get_db(self._config.dbname)
        self._db_hostname = resolve_db_host(self._config.host)
        try:
            with self._db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                self._log.debug("Running query [%s]", self.PG_SETTINGS_QUERY)
                cursor.execute(self.PG_SETTINGS_QUERY)
                rows = cursor.fetchall()
                for setting in rows:
                    name, val = setting
                    if name == PG_STAT_STATEMENTS_MAX:
                        self.settings[PG_STAT_STATEMENTS_MAX]['value'] = int(val)
                    elif name == TRACK_ACTIVITY_QUERY_SIZE:
                        self.settings[TRACK_ACTIVITY_QUERY_SIZE]['value'] = int(val)
        except self._expected_db_exceptions as err:
            self._log.warning("Failed to query for pg_settings: %s", repr(err))
        except Exception as err:
            self._log.exception("Received an unexpected database exception: %s", repr(err))

    def query_settings(self, tags):
        if not self._db:
            self._init()
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
                    self.settings[PG_STAT_STATEMENTS_MAX]['tracked_value'] = count
                    self._emit_tracked_value_metric(PG_STAT_STATEMENTS_MAX, count)
        except self._expected_db_exceptions as err:
            self._log.warning("Failed to query for pg_stat_statements count: %s", repr(err))
        except Exception as err:
            self._log.exception("Received an unexpected database exception: %s", repr(err))
