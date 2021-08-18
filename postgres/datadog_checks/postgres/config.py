# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
# cursor. https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-PARAMKEYWORDS
import psycopg2
from six import PY2, PY3, iteritems

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.utils.aws import rds_parse_tags_from_endpoint
from datadog_checks.base.utils.db.utils import DBMAsyncJob

SSL_MODES = {'disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full'}
TABLE_COUNT_LIMIT = 200

DEFAULT_IGNORE_DATABASES = [
    'template%',
    'rdsadmin',
    'azure_maintenance',
    'postgres',
]

PG_STAT_STATMENTS_MAX_UNKNOWN_VALUE = -1
TRACK_ACTIVITY_QUERY_SIZE_UNKNOWN_VALUE = -1


class DatabaseSetting:
    """
    DatabaseSetting represents a single database setting and a tracked value (if applicable).

    The tracked value is typically used in conjunction with the setting value for scenarios
    where a setting sets a limit and a value must be tracked to check against the set limit.
    """

    def __init__(self, name, value):
        self._name = name
        self._value = value
        self._tracked_value = None

    def get_name(self):
        """get_name returns the name of the setting."""
        return self._name

    def set_value(self, value):
        """set_value sets the value of the setting."""
        self._value = value

    def get_value(self):
        """get_value returns the value of the setting."""
        return self._value

    def set_tracked_value(self, value):
        """set_tracked_value sets the value of the tracked value for this setting."""
        self._tracked_value = value

    def get_tracked_value(self):
        """get_tracked_value returns the tracked value for this setting."""
        return self._tracked_value


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

    def init(self):
        """
        init must run regardless of the collection loop being enabled if `dbm` is enabled.
        Note, a database connection must be established before this is invoked.
        """
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
                "dd.postgres.settings.error",
                1,
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

    def _emit_tracked_value_metric(self, setting, value):
        self._check.count(
            "dd.postgres.settings.{}".format(setting),
            value,
            tags=self._tags,
            hostname=self._db_hostname,
        )


class PostgresConfig:
    RATE = AgentCheck.rate
    GAUGE = AgentCheck.gauge
    MONOTONIC = AgentCheck.monotonic_count

    def __init__(self, instance):
        self.host = instance.get('host', '')
        if not self.host:
            raise ConfigurationError('Specify a Postgres host to connect to.')
        self.port = instance.get('port', '')
        if self.port != '':
            self.port = int(self.port)
        self.user = instance.get('username', '')
        if not self.user:
            raise ConfigurationError('Please specify a user to connect to Postgres.')
        self.password = instance.get('password', '')
        self.dbname = instance.get('dbname', 'postgres')
        self.dbstrict = is_affirmative(instance.get('dbstrict', False))

        self.application_name = instance.get('application_name', 'datadog-agent')
        if not self.isascii(self.application_name):
            raise ConfigurationError("Application name can include only ASCII characters: %s", self.application_name)

        self.query_timeout = int(instance.get('query_timeout', 5000))
        self.relations = instance.get('relations', [])
        if self.relations and not self.dbname:
            raise ConfigurationError('"dbname" parameter must be set when using the "relations" parameter.')

        self.tags = self._build_tags(instance.get('tags', []))

        ssl = instance.get('ssl', False)
        if ssl in SSL_MODES:
            self.ssl_mode = ssl
        else:
            self.ssl_mode = 'require' if is_affirmative(ssl) else 'disable'

        self.table_count_limit = instance.get('table_count_limit', TABLE_COUNT_LIMIT)
        self.collect_function_metrics = is_affirmative(instance.get('collect_function_metrics', False))
        # Default value for `count_metrics` is True for backward compatibility
        self.collect_count_metrics = is_affirmative(instance.get('collect_count_metrics', True))
        self.collect_activity_metrics = is_affirmative(instance.get('collect_activity_metrics', False))
        self.collect_database_size_metrics = is_affirmative(instance.get('collect_database_size_metrics', True))
        self.collect_wal_metrics = is_affirmative(instance.get('collect_wal_metrics', False))
        self.data_directory = instance.get('data_directory', None)
        self.ignore_databases = instance.get('ignore_databases', DEFAULT_IGNORE_DATABASES)
        if is_affirmative(instance.get('collect_default_database', False)):
            self.ignore_databases = [d for d in self.ignore_databases if d != 'postgres']
        self.custom_queries = instance.get('custom_queries', [])
        self.tag_replication_role = is_affirmative(instance.get('tag_replication_role', False))
        self.custom_metrics = self._get_custom_metrics(instance.get('custom_metrics', []))
        self.max_relations = int(instance.get('max_relations', 300))
        self.min_collection_interval = instance.get('min_collection_interval', 15)
        # database monitoring adds additional telemetry for query metrics & samples
        self.dbm_enabled = is_affirmative(instance.get('dbm', instance.get('deep_database_monitoring', False)))
        self.full_statement_text_cache_max_size = instance.get('full_statement_text_cache_max_size', 10000)
        self.full_statement_text_samples_per_hour_per_query = instance.get(
            'full_statement_text_samples_per_hour_per_query', 1
        )
        # Support a custom view when datadog user has insufficient privilege to see queries
        self.pg_stat_statements_view = instance.get('pg_stat_statements_view', 'pg_stat_statements')
        # statement samples & execution plans
        self.pg_stat_activity_view = instance.get('pg_stat_activity_view', 'pg_stat_activity')
        self.statement_samples_config = instance.get('query_samples', instance.get('statement_samples', {})) or {}
        self.statement_metrics_config = instance.get('query_metrics', {}) or {}
        self.query_settings = instance.get('query_settings', {}) or {}
        self.obfuscator_options = instance.get('obfuscator_options', {}) or {}

    def _build_tags(self, custom_tags):
        # Clean up tags in case there was a None entry in the instance
        # e.g. if the yaml contains tags: but no actual tags
        if custom_tags is None:
            tags = []
        else:
            tags = list(set(custom_tags))

        # preset tags to host
        tags.append('server:{}'.format(self.host))
        if self.port:
            tags.append('port:{}'.format(self.port))
        else:
            tags.append('port:socket')

        # preset tags to the database name
        tags.extend(["db:%s" % self.dbname])

        rds_tags = rds_parse_tags_from_endpoint(self.host)
        if rds_tags:
            tags.extend(rds_tags)
        return tags

    @staticmethod
    def _get_custom_metrics(custom_metrics):
        # Otherwise pre-process custom metrics and verify definition
        required_parameters = ("descriptors", "metrics", "query", "relation")

        for m in custom_metrics:
            for param in required_parameters:
                if param not in m:
                    raise ConfigurationError('Missing {} parameter in custom metric'.format(param))

            # Old formatting to new formatting. The first params is always the columns names from which to
            # read metrics. The `relation` param instructs the check to replace the next '%s' with the list of
            # relations names.
            if m['relation']:
                m['query'] = m['query'] % ('{metrics_columns}', '{relations_names}')
            else:
                m['query'] = m['query'] % '{metrics_columns}'

            try:
                for ref, (_, mtype) in iteritems(m['metrics']):
                    cap_mtype = mtype.upper()
                    if cap_mtype not in ('RATE', 'GAUGE', 'MONOTONIC'):
                        raise ConfigurationError(
                            'Collector method {} is not known. '
                            'Known methods are RATE, GAUGE, MONOTONIC'.format(cap_mtype)
                        )

                    m['metrics'][ref][1] = getattr(PostgresConfig, cap_mtype)
            except Exception as e:
                raise Exception('Error processing custom metric `{}`: {}'.format(m, e))
        return custom_metrics

    @staticmethod
    def isascii(application_name):
        if PY3:
            return application_name.isascii()
        elif PY2:
            try:
                application_name.encode('ascii')
                return True
            except UnicodeEncodeError:
                return False
