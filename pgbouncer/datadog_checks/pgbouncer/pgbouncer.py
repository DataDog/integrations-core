# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re

import psycopg2 as pg
from psycopg2 import extras as pgextras
from six.moves.urllib.parse import urlparse

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.pgbouncer.metrics import DATABASES_METRICS, POOLS_METRICS, STATS_METRICS


class ShouldRestartException(Exception):
    pass


class PgBouncer(AgentCheck):
    """Collects metrics from pgbouncer"""

    DB_NAME = 'pgbouncer'
    SERVICE_CHECK_NAME = 'pgbouncer.can_connect'

    def __init__(self, name, init_config, instances):
        super(PgBouncer, self).__init__(name, init_config, instances)
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

    def _get_service_checks_tags(self):
        host = self.host
        port = self.port
        if self.database_url:
            parsed_url = urlparse(self.database_url)
            host = parsed_url.hostname
            port = parsed_url.port

        service_checks_tags = ["host:%s" % host, "port:%s" % port, "db:%s" % self.DB_NAME]
        service_checks_tags.extend(self.tags)
        service_checks_tags = list(set(service_checks_tags))

        return service_checks_tags

    def _collect_stats(self, db):
        """Query pgbouncer for various metrics"""

        metric_scope = [STATS_METRICS, POOLS_METRICS, DATABASES_METRICS]

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

                            tags = list(self.tags)
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

        args = {
            'host': self.host,
            'user': self.user,
            'password': self.password,
            'database': self.DB_NAME,
        }
        if self.port:
            args['port'] = self.port

        return args

    def _get_connection(self, use_cached=None):
        """Get and memoize connections to instances"""
        use_cached = use_cached if use_cached is not None else self.use_cached
        if self.connection and use_cached:
            return self.connection
        try:
            connect_kwargs = self._get_connect_kwargs()
            connection = pg.connect(**connect_kwargs)
            connection.set_isolation_level(pg.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        except Exception:
            redacted_url = self._get_redacted_dsn()
            message = u'Cannot establish connection to {}'.format(redacted_url)

            self.service_check(
                self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self._get_service_checks_tags(), message=message
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

    def check(self, _):
        try:
            db = self._get_connection()
            self._collect_stats(db)
        except ShouldRestartException:
            self.log.info("Resetting the connection")
            db = self._get_connection(use_cached=False)
            self._collect_stats(db)

        redacted_dsn = self._get_redacted_dsn()
        message = u'Established connection to {}'.format(redacted_dsn)
        self.service_check(
            self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=self._get_service_checks_tags(), message=message
        )
        self._set_metadata()

    def _set_metadata(self):
        if self.is_metadata_collection_enabled():
            pgbouncer_version = self.get_version()
            if pgbouncer_version:
                self.set_metadata('version', pgbouncer_version)

    def get_version(self):
        db = self._get_connection()
        regex = r'\d+\.\d+\.\d+'
        with db.cursor(cursor_factory=pgextras.DictCursor) as cursor:
            cursor.execute('SHOW VERSION;')
            if db.notices:
                data = db.notices[0]
            else:
                data = cursor.fetchone()[0]
            res = re.findall(regex, data)
            if res:
                return res[0]
            self.log.debug("Couldn't detect version from %s", data)
