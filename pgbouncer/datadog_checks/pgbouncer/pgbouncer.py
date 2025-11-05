# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re
import time
from urllib.parse import urlparse

import psycopg as pg
from psycopg import ClientCursor
from psycopg.rows import dict_row

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.pgbouncer.metrics import (
    CLIENTS_METRICS,
    CONFIG_METRICS,
    DATABASES_METRICS,
    POOLS_METRICS,
    SERVERS_METRICS,
    STATS_METRICS,
)


class ShouldReconnectException(Exception):
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
        self.collect_per_client_metrics = is_affirmative(self.instance.get('collect_per_client_metrics', False))
        self.collect_per_server_metrics = is_affirmative(self.instance.get('collect_per_server_metrics', False))

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

        metric_scope = [STATS_METRICS, POOLS_METRICS, DATABASES_METRICS, CONFIG_METRICS]

        if self.collect_per_client_metrics:
            metric_scope.append(CLIENTS_METRICS)
        if self.collect_per_server_metrics:
            metric_scope.append(SERVERS_METRICS)

        try:
            for scope in metric_scope:
                descriptors = scope['descriptors']
                metrics = scope['metrics']
                query = scope['query']

                try:
                    cursor = db.cursor(row_factory=dict_row)
                    self.log.debug("Running query: %s", query)
                    cursor.execute(query)
                    rows = self.iter_rows(cursor)

                except (pg.InterfaceError, pg.OperationalError) as e:
                    self.log.error("Not all metrics may be available: %s", e)
                    raise ShouldReconnectException

                else:
                    for row in rows:
                        if 'key' in row:  # We are processing "config metrics"
                            # Make a copy of the row to allow mutation
                            row = row.copy()
                            # We flip/rotate the row: row value becomes the column name
                            row[row['key']] = row['value']
                        # Skip the "pgbouncer" database
                        elif row.get('database') == self.DB_NAME:
                            continue

                        tags = list(self.tags)
                        tags += ["%s:%s" % (tag, row[column]) for (column, tag) in descriptors if column in row]
                        for column, (name, reporter) in metrics:
                            if column in row:
                                value = row[column]
                                if column in ['connect_time', 'request_time']:
                                    self.log.debug("Parsing timestamp; original value: %s", value)
                                    # First get rid of any UTC suffix.
                                    value = re.findall(r'^[^ ]+ [^ ]+', value)[0]
                                    value = time.strptime(value, '%Y-%m-%d %H:%M:%S')
                                    value = time.mktime(value)
                                reporter(self, name, value, tags)

                    if not rows:
                        self.log.warning("No results were found for query: %s", query)

        except pg.Error as e:
            self.log.error("Not all metrics may be available: %s", e)
            raise ShouldReconnectException

    def iter_rows(self, cursor):
        row_num = 0
        rows = iter(cursor)
        while True:
            try:
                row = next(rows)
            except StopIteration:
                break
            except Exception as e:
                self.log.error('Error processing row %d: %s', row_num, e)
            else:
                self.log.debug('Processing row: %r', row)
                yield row

            row_num += 1

    def _get_connect_kwargs(self):
        """
        Get the params to pass to psycopg.connect() based on passed-in vals
        from yaml settings file
        """
        # It's important to set the client_encoding to utf-8
        # PGBouncer defaults to an encoding of 'UNICODE`, which will cause psycopg to error out
        if self.database_url:
            return {'conninfo': self.database_url, 'client_encoding': 'utf-8'}

        if self.host in ('localhost', '127.0.0.1') and self.password == '':
            # Use ident method
            return {'conninfo': "user={} dbname={} client_encoding=utf-8".format(self.user, self.DB_NAME)}

        args = {
            'host': self.host,
            'user': self.user,
            'password': self.password,
            'dbname': self.DB_NAME,
            'client_encoding': 'utf-8',
        }
        if self.port:
            args['port'] = self.port

        return args

    def _new_connection(self):
        """Create a new connection to PgBouncer"""
        connection = None
        try:
            connect_kwargs = self._get_connect_kwargs()
            # Somewhat counterintuitively, we need to set autocommit to True to avoid a BEGIN/COMMIT block
            # https://www.psycopg.org/psycopg3/docs/basic/transactions.html#autocommit-transactions
            # We need to set ClientCursor to true to use simple query protocol:
            # https://www.psycopg.org/psycopg3/docs/advanced/cursors.html#simple-query-protocol
            connection = pg.connect(**connect_kwargs, autocommit=True, cursor_factory=ClientCursor)
            return connection
        except Exception:
            if connection:
                try:
                    connection.close()
                except Exception:
                    self.log.debug("Error closing connection after failed creation", exc_info=True)
            redacted_url = self._get_redacted_dsn()
            message = 'Cannot establish connection to {}'.format(redacted_url)

            self.service_check(
                self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self._get_service_checks_tags(), message=message
            )
            raise

    def _ensure_connection(self):
        """Create a connection the the instance if it doesn't exist."""
        if not self.connection:
            self.connection = self._new_connection()

    def _get_redacted_dsn(self):
        if not self.database_url:
            return 'pgbouncer://%s:******@%s:%s/%s' % (self.user, self.host, self.port, self.DB_NAME)

        parsed_url = urlparse(self.database_url)
        if parsed_url.password:
            return self.database_url.replace(parsed_url.password, '******')
        return self.database_url

    def _close_connection(self):
        """Close the connection to PgBouncer"""
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                self.log.debug("Error closing connection", exc_info=True)
            finally:
                self.connection = None

    def _try_collect_data(self, allow_reconnect=True):
        try:
            self._ensure_connection()
            self._collect_stats(self.connection)
            self._collect_metadata(self.connection)
        except ShouldReconnectException:
            self.log.info("Resetting the connection")
            self._close_connection()
            if allow_reconnect:
                self._try_collect_data(allow_reconnect=False)
            else:
                redacted_url = self._get_redacted_dsn()
                message = 'Connection error while collecting data from: {}'.format(redacted_url)
                self.log.error(message)
                self.service_check(
                    self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self._get_service_checks_tags(), message=message
                )
                raise

    def check(self, instance):
        try:
            self._try_collect_data()
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=self._get_service_checks_tags())
        finally:
            if not self.use_cached:
                self._close_connection()

    def _collect_metadata(self, db):
        if self.is_metadata_collection_enabled():
            pgbouncer_version = self.get_version(db)
            if pgbouncer_version:
                self.set_metadata('version', pgbouncer_version)

    def get_version(self, db):
        """
        Get the version of PgBouncer.
        """
        if not db:
            self.log.warning("Cannot get version: no active connection")
            return None

        regex = r'\d+\.\d+\.\d+'
        try:
            with db.cursor() as cursor:
                # This command was added in pgbouncer 1.12
                cursor.execute('SHOW VERSION;')
                result = cursor.fetchone()
                if result:
                    # Result looks like: ['PgBouncer 1.2.3 ...']
                    version_string = result[0]
                    return re.findall(regex, version_string)[0]
                else:
                    self.log.debug("No version found in result: %s", result)
                    return None
        except pg.ProgrammingError as e:
            # This is expected on versions of pgbouncer < 1.12
            self.log.debug("Cannot retrieve pgbouncer version using `SHOW VERSION;`: %s", e)
            return None
        except Exception as e:
            self.log.error("An unexpected error occurred when retrieving pgbouncer version: %s", e)
            return None
        return None
