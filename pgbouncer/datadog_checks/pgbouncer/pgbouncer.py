# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import urlparse

import psycopg2 as pg
import psycopg2.extras as pgextras

from datadog_checks.checks import AgentCheck
from datadog_checks.config import is_affirmative
from datadog_checks.errors import CheckException


class ShouldRestartException(Exception):
    pass


class PgBouncer(AgentCheck):
    """Collects metrics from pgbouncer
    """
    RATE = AgentCheck.rate
    GAUGE = AgentCheck.gauge
    DB_NAME = 'pgbouncer'
    SERVICE_CHECK_NAME = 'pgbouncer.can_connect'

    STATS_METRICS = {
        'descriptors': [
            ('database', 'db'),
        ],
        'metrics': [
            ('total_requests',       ('pgbouncer.stats.requests_per_second', RATE)),  # < 1.8
            ('total_xact_count',     ('pgbouncer.stats.transactions_per_second', RATE)),  # >= 1.8
            ('total_query_count',    ('pgbouncer.stats.queries_per_second', RATE)),  # >= 1.8
            ('total_received',       ('pgbouncer.stats.bytes_received_per_second', RATE)),
            ('total_sent',           ('pgbouncer.stats.bytes_sent_per_second', RATE)),
            ('total_query_time',     ('pgbouncer.stats.total_query_time', RATE)),
            ('total_xact_time',      ('pgbouncer.stats.total_transaction_time', RATE)),  # >= 1.8
            ('avg_req',              ('pgbouncer.stats.avg_req', GAUGE)),  # < 1.8
            ('avg_xact_count',       ('pgbouncer.stats.avg_transaction_count', GAUGE)),  # >= 1.8
            ('avg_query_count',      ('pgbouncer.stats.avg_query_count', GAUGE)),  # >= 1.8
            ('avg_recv',             ('pgbouncer.stats.avg_recv', GAUGE)),
            ('avg_sent',             ('pgbouncer.stats.avg_sent', GAUGE)),
            ('avg_query',            ('pgbouncer.stats.avg_query', GAUGE)),  # < 1.8
            ('avg_xact_time',        ('pgbouncer.stats.avg_transaction_time', GAUGE)),  # >= 1.8
            ('avg_query_time',       ('pgbouncer.stats.avg_query_time', GAUGE)),  # >= 1.8
        ],
        'query': """SHOW STATS""",
    }

    POOLS_METRICS = {
        'descriptors': [
            ('database', 'db'),
            ('user', 'user'),
        ],
        'metrics': [
            ('cl_active',            ('pgbouncer.pools.cl_active', GAUGE)),
            ('cl_waiting',           ('pgbouncer.pools.cl_waiting', GAUGE)),
            ('sv_active',            ('pgbouncer.pools.sv_active', GAUGE)),
            ('sv_idle',              ('pgbouncer.pools.sv_idle', GAUGE)),
            ('sv_used',              ('pgbouncer.pools.sv_used', GAUGE)),
            ('sv_tested',            ('pgbouncer.pools.sv_tested', GAUGE)),
            ('sv_login',             ('pgbouncer.pools.sv_login', GAUGE)),
            ('maxwait',              ('pgbouncer.pools.maxwait', GAUGE)),
        ],
        'query': """SHOW POOLS""",
    }

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.dbs = {}

    def _get_service_checks_tags(self, host, port, database_url, tags=None):
        if tags is None:
            tags = []

        if database_url:
            parsed_url = urlparse.urlparse(database_url)
            host = parsed_url.hostname
            port = parsed_url.port

        service_checks_tags = [
            "host:%s" % host,
            "port:%s" % port,
            "db:%s" % self.DB_NAME
        ]
        service_checks_tags.extend(tags)
        service_checks_tags = list(set(service_checks_tags))

        return service_checks_tags

    def _collect_stats(self, db, instance_tags):
        """Query pgbouncer for various metrics
        """

        metric_scope = [self.STATS_METRICS, self.POOLS_METRICS]

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

    def _get_connect_kwargs(self, host, port, user, password, database_url):
        """
        Get the params to pass to psycopg2.connect() based on passed-in vals
        from yaml settings file
        """
        if database_url:
            return {'dsn': database_url}

        if not host:
            raise CheckException(
                "Please specify a PgBouncer host to connect to.")

        if not user:
            raise CheckException(
                "Please specify a user to connect to PgBouncer as.")

        if host in ('localhost', '127.0.0.1') and password == '':
            return {  # Use ident method
                'dsn': "user={} dbname={}".format(user, self.DB_NAME)
            }

        if port:
            return {'host': host, 'user': user, 'password': password,
                    'database': self.DB_NAME, 'port': port}

        return {'host': host, 'user': user, 'password': password,
                'database': self.DB_NAME}

    def _get_connection(self, key, host='', port='', user='',
                        password='', database_url='', tags=None, use_cached=True):
        "Get and memoize connections to instances"
        if key in self.dbs and use_cached:
            return self.dbs[key]
        try:
            connect_kwargs = self._get_connect_kwargs(
                host=host, port=port, user=user,
                password=password, database_url=database_url
            )

            connection = pg.connect(**connect_kwargs)
            connection.set_isolation_level(
                pg.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

        # re-raise the CheckExceptions raised by _get_connect_kwargs()
        except CheckException:
            raise

        except Exception:
            redacted_url = self._get_redacted_dsn(host, port, user, database_url)
            message = u'Cannot establish connection to {}'.format(redacted_url)

            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                               tags=self._get_service_checks_tags(host, port, database_url, tags),
                               message=message)
            raise

        self.dbs[key] = connection
        return connection

    def _get_redacted_dsn(self, host, port, user, database_url):
        if not database_url:
            return u'pgbouncer://%s:******@%s:%s/%s' % (user, host, port, self.DB_NAME)

        parsed_url = urlparse.urlparse(database_url)
        if parsed_url.password:
            return database_url.replace(parsed_url.password, '******')
        return database_url

    def check(self, instance):
        host = instance.get('host', '')
        port = instance.get('port', '')
        user = instance.get('username', '')
        password = instance.get('password', '')
        tags = instance.get('tags', [])
        database_url = instance.get('database_url')
        use_cached = is_affirmative(instance.get('use_cached', True))

        if database_url:
            key = database_url
        else:
            key = '%s:%s' % (host, port)

        if tags is None:
            tags = []
        else:
            tags = list(set(tags))

        try:
            db = self._get_connection(key, host, port, user, password, tags=tags,
                                      database_url=database_url, use_cached=use_cached)
            self._collect_stats(db, tags)
        except ShouldRestartException:
            self.log.info("Resetting the connection")
            db = self._get_connection(key, host, port, user, password, tags=tags, use_cached=False)
            self._collect_stats(db, tags)

        redacted_dsn = self._get_redacted_dsn(host, port, user, database_url)
        message = u'Established connection to {}'.format(redacted_dsn)
        self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK,
                           tags=self._get_service_checks_tags(host, port, database_url, tags),
                           message=message)
