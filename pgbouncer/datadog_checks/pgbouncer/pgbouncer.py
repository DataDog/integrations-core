# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import psycopg2 as pg
import psycopg2.extras as pgextras
from six.moves.urllib.parse import urlparse

from datadog_checks.checks import AgentCheck
from datadog_checks.config import is_affirmative
from datadog_checks.errors import CheckException, ConfigurationError


class ShouldRestartException(Exception):
    pass


class PgBouncer(AgentCheck):
    """Collects metrics from pgbouncer"""
    DB_NAME = 'pgbouncer'
    SERVICE_CHECK_NAME = 'pgbouncer.can_connect'

    def __init__(self, name, init_config, instances):
        AgentCheck.__init__(self, name, init_config, instances)
        self.host = self.instance.get('host', '')
        self.port = self.instance.get('port', '')
        self.user = self.instance.get('username', '')
        self.password = self.instance.get('password', '')
        self.tags = self.instance.get('tags', [])
        self.database_url = self.instance.get('database_url')
        self.use_cached = is_affirmative(self.instance.get('use_cached', True))

        if not self.database_url:
            if not self.host:
                raise ConfigurationError("Please specify a PgBouncer host to connect to.")
            if not self.user:
                raise ConfigurationError("Please specify a user to connect to PgBouncer as.")
        self.connection = None

    def _get_service_checks_tags(self, host, port, database_url, tags=None):
        if tags is None:
            tags = []

        if database_url:
            parsed_url = urlparse(database_url)
            host = parsed_url.hostname
            port = parsed_url.port

        service_checks_tags = ["host:%s" % host, "port:%s" % port, "db:%s" % self.DB_NAME]
        service_checks_tags.extend(tags)
        service_checks_tags = list(set(service_checks_tags))

        return service_checks_tags

    def _collect_stats(self, db, instance_tags):
        """Query pgbouncer for various metrics
        """

        metric_scope = [self.STATS_METRICS, self.POOLS_METRICS, self.DATABASES_METRICS]

        try:
            with db.cursor(cursor_factory=pgextras.DictCursor) as cursor:
                for scope in metric_scope:
                    descriptors = scope['descriptors']
                    metrics = scope['metrics']
                    query = scope['query']

                    try:
                        self.log.debug("Running query: %s", query)
                        cursor.execute(query)

                        rows = cursor.fetchall()

                    except pg.Error:
                        self.log.exception("Not all metrics may be available")

                    else:
                        for row in rows:
                            self.log.debug("Processing row: %r", row)

                            # Skip the "pgbouncer" database
                            if row['database'] == self.DB_NAME:
                                continue

                            tags = list(instance_tags)
                            tags += ["%s:%s" % (tag, row[column]) for (column, tag) in descriptors if column in row]
                            for (column, (name, reporter)) in metrics:
                                if column in row:
                                    reporter(self, name, row[column], tags)

                        if not rows:
                            self.log.warning("No results were found for query: %s", query)

        except pg.Error:
            self.log.exception("Connection error")

            raise ShouldRestartException

    def _get_connect_kwargs(self):
        """
        Get the params to pass to psycopg2.connect() based on passed-in vals
        from yaml settings file
        """
        if self.database_url:
            return {'dsn': self.database_url}

        if self.host in ('localhost', '127.0.0.1') and self.password == '':
            # Use ident method
            return {'dsn': "user={} dbname={}".format(self.user, self.DB_NAME)}

        if self.port:
            return {'host': self.host, 'user': self.user, 'password': self.password, 'database': self.DB_NAME, 'port': self.port}

        return {'host': self.host, 'user': self.user, 'password': self.password, 'database': self.DB_NAME}

    def _get_connection(self, use_cached=True):
        """Get and memoize connections to instances"""
        if self.connection and self.use_cached and use_cached:
            return self.connection
        try:
            connect_kwargs = self._get_connect_kwargs()

            connection = pg.connect(**connect_kwargs)
            connection.set_isolation_level(pg.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

        # re-raise the CheckExceptions raised by _get_connect_kwargs()
        except CheckException:
            raise

        except Exception:
            redacted_url = self._get_redacted_dsn()
            message = u'Cannot establish connection to {}'.format(redacted_url)

            self.service_check(
                self.SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                tags=self._get_service_checks_tags(),
                message=message,
            )
            raise

        self.connection = connection
        return connection

    def _get_redacted_dsn(self):
        if not self.database_url:
            return u'pgbouncer://%s:******@%s:%s/%s' % (self.user, self.host, self.port, self.DB_NAME)

        parsed_url = urlparse(self.database_url)
        if parsed_url.password:
            return self.database_url.replace(parsed_url.password, '******')
        return self.database_url

    def check(self, instance):
        try:
            db = self._get_connection()
            self._collect_stats(db, self.tags)
        except ShouldRestartException:
            self.log.info("Resetting the connection")
            db = self._get_connection(use_cached=False)
            self._collect_stats(db, self.tags)

        redacted_dsn = self._get_redacted_dsn()
        message = u'Established connection to {}'.format(redacted_dsn)
        self.service_check(
            self.SERVICE_CHECK_NAME,
            AgentCheck.OK,
            tags=self._get_service_checks_tags(),
            message=message,
        )
