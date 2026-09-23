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

from .__about__ import __version__
from .config import build_config
from .connection import Db2Connection
from .custom_metrics import CustomMetricsCollector
from .metrics import MetricsCollector
from .utils import get_version


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
        self._connection = Db2Connection(self, self._config, on_reconnect=self.emit_connection_service_checks)
        self._metrics = MetricsCollector(self, self._connection)
        self._query_methods = (
            self._metrics.query_instance,
            self._metrics.query_database,
            self._metrics.query_buffer_pool,
            self._metrics.query_table_space,
            self._metrics.query_transaction_log,
        )
        self._custom_metrics = self.register_async_job(CustomMetricsCollector(self, self._config))

    def check(self, instance):
        if self._connection.conn is None:
            self._connection.connect()
        self.emit_connection_service_checks()
        if self._connection.conn is None:
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

        self.run_async_jobs(self.tags)

    def shutdown(self) -> None:
        self._connection.close()

    @AgentCheck.metadata_entrypoint
    def collect_metadata(self):
        try:
            raw_version = get_version(self._connection.conn)
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
    def database_identifier_params(self) -> dict:
        return {
            'resolved_hostname': self.reported_hostname,
            'host': str(self._config.host),
            'port': str(self._config.port),
        }

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

    def emit_connection_service_checks(self):
        if self._connection.conn is None:
            self.service_check(
                self.SERVICE_CHECK_CONNECT,
                self.CRITICAL,
                tags=self.tags,
                message="Unable to create new connection to database: {}".format(self._config.db),
            )
        else:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self.tags)

    @classmethod
    def m(cls, metric):
        return '{}.{}'.format(cls.METRIC_PREFIX, metric)
