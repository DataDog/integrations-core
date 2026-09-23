# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

from time import time as timestamp

from requests import ConnectionError

from datadog_checks.base import AgentCheck
from datadog_checks.base.checks.db import DatabaseCheck
from datadog_checks.base.utils.db.utils import default_json_event_encoding
from datadog_checks.base.utils.db.utils import resolve_db_host as agent_host_resolver
from datadog_checks.base.utils.platform import Platform
from datadog_checks.base.utils.serialization import json

if Platform.is_windows():
    # After installing ibm_db, dll path of dependent library of clidriver must be set before importing the module
    # Ref: https://github.com/ibmdb/python-ibmdb/#installation
    import os

    embedded_lib = os.path.dirname(os.path.abspath(os.__file__))
    os.add_dll_directory(os.path.join(embedded_lib, 'site-packages', 'clidriver', 'bin'))

import ibm_db

from .__about__ import __version__
from .config import build_config
from .custom_metrics import CustomMetricsCollector
from .metrics import MetricsCollector
from .utils import get_version, scrub_connection_string


class IbmDb2Check(DatabaseCheck):
    DBMS = 'ibm_db2'
    METRIC_PREFIX = 'ibm_db2'
    SERVICE_CHECK_CONNECT = '{}.can_connect'.format(METRIC_PREFIX)
    SERVICE_CHECK_STATUS = '{}.status'.format(METRIC_PREFIX)
    EVENT_TABLE_SPACE_STATE = '{}.tablespace_state_change'.format(METRIC_PREFIX)
    DATABASE_INSTANCE_COLLECTION_INTERVAL = 300

    def __init__(self, name, init_config, instances):
        super(IbmDb2Check, self).__init__(name, init_config, instances)
        self._config = build_config(self)
        self.tag_manager.set_tags_from_list(self._config.tags or (), replace=True)
        self._resolved_hostname = None
        self._version = None
        self._database_instance_last_emitted = None

        # Add global database tag
        self.tag_manager.set_tag('db', self._config.db)

        # We'll connect on the first check run
        self._conn = None
        metrics = MetricsCollector(self)
        custom_metrics = CustomMetricsCollector(self, self._config.custom_queries)
        self._query_methods = (
            metrics.query_instance,
            metrics.query_database,
            metrics.query_buffer_pool,
            metrics.query_table_space,
            metrics.query_transaction_log,
            custom_metrics.query_custom,
        )

    def check(self, instance):
        if self._conn is None:
            self._conn = self.get_connection()
        self.emit_connection_service_checks()
        if self._conn is None:
            return

        self.collect_metadata()
        self._send_database_instance_metadata()
        for query_method in self._query_methods:
            try:
                query_method()
            except ConnectionError:
                raise
            except Exception as e:
                self.log.warning('Encountered error running `%s`: %s', query_method.__name__, str(e))
                continue

    @AgentCheck.metadata_entrypoint
    def collect_metadata(self):
        try:
            raw_version = get_version(self._conn)
        except Exception as e:
            self.log.error("Error getting version: %s", e)
            return

        if raw_version:
            self._version = raw_version
            version_parts = self.parse_version(raw_version)
            self.set_metadata('version', raw_version, scheme='parts', part_map=version_parts)

            self.log.debug('Found ibm_db2 version: %s', raw_version)
        else:
            self.log.warning('Could not retrieve ibm_db2 version info: %s', raw_version)

    @property
    def reported_hostname(self) -> str:
        if self._resolved_hostname is None:
            self._resolved_hostname = agent_host_resolver(self._config.host)
        return self._resolved_hostname

    @property
    def dbms_version(self) -> str | None:
        return self._version

    @property
    def cloud_metadata(self) -> dict:
        return {}

    def _send_database_instance_metadata(self):
        now = timestamp()
        if (
            self._database_instance_last_emitted is None
            or now - self._database_instance_last_emitted >= self.DATABASE_INSTANCE_COLLECTION_INTERVAL
        ):
            event = {
                "host": self.reported_hostname,
                "port": self._config.port,
                "database_instance": self.database_identifier,
                "database_hostname": self.reported_hostname,
                "agent_version": self.agent_version,
                "ddagenthostname": self.agent_hostname,
                "dbms": self.dbms,
                "kind": "database_instance",
                "collection_interval": self.DATABASE_INSTANCE_COLLECTION_INTERVAL,
                "dbms_version": self.dbms_version,
                "integration_version": __version__,
                "tags": self.tag_manager.get_tags(include_internal=False),
                "timestamp": now * 1000,
                "cloud_metadata": self.cloud_metadata,
                "metadata": {
                    "dbm": self._config.dbm,
                    "connection_host": self._config.host,
                },
            }
            self._database_instance_last_emitted = now
            self.database_monitoring_metadata(json.dumps(event, default=default_json_event_encoding))

    def parse_version(self, version):
        """
        Raw version string is in format MM.mm.uuuu.
        Parse version to MM.mm.xx.yy
        where xx is the modification number and yy is the fix pack number
        https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.wn.doc/doc/c0070229.html#c0070229
        """
        major, minor, update = version.split('.')
        modification, fix = update[:2], update[2:]

        # remove leading zeros from raw version parts
        return {
            'major': str(int(major)),
            'minor': str(int(minor)),
            'mod': str(int(modification)),
            'fix': str(int(fix)),
        }

    def get_connection(self):
        target, username, password = self.get_connection_data(
            self._config.db,
            self._config.username,
            self._config.password,
            self._config.host,
            self._config.port,
            self._config.security,
            self._config.tls_cert,
            self._config.connection_timeout,
        )

        # Get column names in lower case
        connection_options = {ibm_db.ATTR_CASE: ibm_db.CASE_LOWER}

        try:
            self.log.debug("Attempting to connect to Db2 with `%s`...", scrub_connection_string(target))
            connection = ibm_db.connect(target, username, password, connection_options)
        except Exception as e:
            if self._config.host:
                self.log.error('Unable to connect with `%s`: %s', scrub_connection_string(target), e)
            else:  # no cov
                self.log.error('Unable to connect to database `%s` as user `%s`: %s', target, username, e)
            connection = None
        return connection

    def emit_connection_service_checks(self):
        if self._conn is None:
            self.service_check(
                self.SERVICE_CHECK_CONNECT,
                self.CRITICAL,
                tags=self.tags,
                message="Unable to create new connection to database: {}".format(self._config.db),
            )
        else:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self.tags)

    @classmethod
    def get_connection_data(cls, db, username, password, host, port, security, tls_cert, connection_timeout):
        if host:
            target = 'database={};hostname={};port={};protocol=tcpip;uid={};pwd={}'.format(
                db, host, port, username, password
            )
            username = ''
            password = ''
            if security == 'ssl':
                target = '{};security=ssl;'.format(target)
            if tls_cert:
                target = '{};security=ssl;sslservercertificate={}'.format(target, tls_cert)
            if connection_timeout:
                target = '{};connecttimeout={}'.format(target, connection_timeout)
        else:  # no cov
            target = db

        return target, username, password

    def iter_rows(self, query, method):
        # https://github.com/ibmdb/python-ibmdb/wiki/APIs
        try:
            cursor = ibm_db.exec_immediate(self._conn, query)
        except Exception as e:
            error = str(e)
            self.log.error("Error executing query: %s.\nAttempting to reconnect", error)
            # ToDo: Probably the best strategy here would be to just set self._conn = None, abort the current check run
            # and retry on the next check run.
            self._conn = self.get_connection()
            self.emit_connection_service_checks()
            if self._conn is None:
                raise ConnectionError("Unable to create new connection")

            cursor = ibm_db.exec_immediate(self._conn, query)

        row = method(cursor)
        while row is not False:
            yield row

            # Get next row, if any
            row = method(cursor)

    @classmethod
    def m(cls, metric):
        return '{}.{}'.format(cls.METRIC_PREFIX, metric)
