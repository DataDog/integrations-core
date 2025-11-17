# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from time import time

import clickhouse_connect
from cachetools import TTLCache

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.utils.db import QueryManager
from datadog_checks.base.utils.db.utils import default_json_event_encoding

from . import queries
from .__about__ import __version__
from .statement_samples import ClickhouseStatementSamples
from .statements import ClickhouseStatementMetrics
from .utils import ErrorSanitizer

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent


class ClickhouseCheck(AgentCheck):
    __NAMESPACE__ = 'clickhouse'
    SERVICE_CHECK_CONNECT = 'can_connect'

    def __init__(self, name, init_config, instances):
        super(ClickhouseCheck, self).__init__(name, init_config, instances)

        self._server = self.instance.get('server', '')
        self._port = self.instance.get('port')
        self._db = self.instance.get('db', 'default')
        self._user = self.instance.get('username', self.instance.get('user', 'default'))
        self._password = self.instance.get('password', '')
        self._connect_timeout = float(self.instance.get('connect_timeout', 10))
        self._read_timeout = float(self.instance.get('read_timeout', 10))
        self._compression = self.instance.get('compression', False)
        self._tls_verify = is_affirmative(self.instance.get('tls_verify', False))
        self._tls_ca_cert = self.instance.get('tls_ca_cert', None)
        self._verify = self.instance.get('verify', True)
        self._tags = self.instance.get('tags', [])

        # DBM-related properties
        self._resolved_hostname = None
        self._database_identifier = None
        self._agent_hostname = None

        # Cloud metadata configuration
        self._cloud_metadata = {}

        # AWS cloud metadata
        aws_config = self.instance.get('aws', {})
        if aws_config.get('instance_endpoint'):
            self._cloud_metadata['aws'] = {'instance_endpoint': aws_config['instance_endpoint']}

        # GCP cloud metadata
        gcp_config = self.instance.get('gcp', {})
        if gcp_config.get('project_id') and gcp_config.get('instance_id'):
            self._cloud_metadata['gcp'] = {
                'project_id': gcp_config['project_id'],
                'instance_id': gcp_config['instance_id'],
            }

        # Azure cloud metadata
        azure_config = self.instance.get('azure', {})
        if azure_config.get('deployment_type') and azure_config.get('fully_qualified_domain_name'):
            self._cloud_metadata['azure'] = {
                'deployment_type': azure_config['deployment_type'],
                'fully_qualified_domain_name': azure_config['fully_qualified_domain_name'],
            }
            if azure_config.get('database_name'):
                self._cloud_metadata['azure']['database_name'] = azure_config['database_name']

        # Database instance metadata collection interval
        self._database_instance_collection_interval = float(
            self.instance.get('database_instance_collection_interval', 300)
        )

        # _database_instance_emitted: limit the collection and transmission of the database instance metadata
        self._database_instance_emitted = TTLCache(
            maxsize=1,
            ttl=self._database_instance_collection_interval,
        )

        # Add global tags
        self._tags.append('server:{}'.format(self._server))
        self._tags.append('port:{}'.format(self._port))
        self._tags.append('db:{}'.format(self._db))

        self._error_sanitizer = ErrorSanitizer(self._password)
        self.check_initializations.append(self.validate_config)

        # We'll connect on the first check run
        self._client = None

        self._query_manager = QueryManager(
            self,
            self.execute_query_raw,
            queries=[
                queries.SystemMetrics,
                queries.SystemEventsToDeprecate,
                queries.SystemEvents,
                queries.SystemAsynchronousMetrics,
                queries.SystemParts,
                queries.SystemReplicas,
                queries.SystemDictionaries,
            ],
            tags=self._tags,
            error_handler=self._error_sanitizer.clean,
        )
        self.check_initializations.append(self._query_manager.compile_queries)

        # Initialize DBM components if enabled
        self._dbm_enabled = is_affirmative(self.instance.get('dbm', False))

        # Initialize query metrics (from system.query_log - analogous to pg_stat_statements)
        self._query_metrics_config = self.instance.get('query_metrics', {})
        if self._dbm_enabled and self._query_metrics_config.get('enabled', True):
            # Create a simple config object for query metrics
            class QueryMetricsConfig:
                def __init__(self, config_dict):
                    self.enabled = config_dict.get('enabled', True)
                    self.collection_interval = config_dict.get('collection_interval', 60)
                    self.run_sync = config_dict.get('run_sync', False)
                    self.full_statement_text_cache_max_size = config_dict.get(
                        'full_statement_text_cache_max_size', 10000
                    )
                    self.full_statement_text_samples_per_hour_per_query = config_dict.get(
                        'full_statement_text_samples_per_hour_per_query', 1
                    )

            self.statement_metrics = ClickhouseStatementMetrics(self, QueryMetricsConfig(self._query_metrics_config))
        else:
            self.statement_metrics = None

        # Initialize query samples (from system.processes - analogous to pg_stat_activity)
        self._query_samples_config = self.instance.get('query_samples', {})
        if self._dbm_enabled and self._query_samples_config.get('enabled', True):
            # Create a simple config object for statement samples
            class QuerySamplesConfig:
                def __init__(self, config_dict):
                    self.enabled = config_dict.get('enabled', True)
                    self.collection_interval = config_dict.get('collection_interval', 10)
                    self.run_sync = config_dict.get('run_sync', False)
                    self.samples_per_hour_per_query = config_dict.get('samples_per_hour_per_query', 15)
                    self.seen_samples_cache_maxsize = config_dict.get('seen_samples_cache_maxsize', 10000)
                    # Activity snapshot configuration
                    self.activity_enabled = config_dict.get('activity_enabled', True)
                    self.activity_collection_interval = config_dict.get('activity_collection_interval', 10)
                    self.activity_max_rows = config_dict.get('activity_max_rows', 1000)

            self.statement_samples = ClickhouseStatementSamples(self, QuerySamplesConfig(self._query_samples_config))
        else:
            self.statement_samples = None

    def _send_database_instance_metadata(self):
        """Send database instance metadata to the metadata intake."""
        if self.database_identifier not in self._database_instance_emitted:
            # Get the version for the metadata
            version = None
            try:
                version_result = list(self.execute_query_raw('SELECT version()'))[0][0]
                version = version_result
            except Exception as e:
                self.log.debug("Unable to fetch version for metadata: %s", e)
                version = "unknown"

            event = {
                "host": self.reported_hostname,
                "port": self._port,
                "database_instance": self.database_identifier,
                "database_hostname": self.reported_hostname,
                "agent_version": datadog_agent.get_version(),
                "ddagenthostname": self.agent_hostname,
                "dbms": "clickhouse",
                "kind": "database_instance",
                "collection_interval": self._database_instance_collection_interval,
                "dbms_version": version,
                "integration_version": __version__,
                "tags": [t for t in self._tags if not t.startswith('db:')],
                "timestamp": time() * 1000,
                "metadata": {
                    "dbm": self._dbm_enabled,
                    "connection_host": self._server,
                },
            }

            # Add cloud metadata if available
            if self._cloud_metadata:
                event["cloud_metadata"] = self._cloud_metadata

            self._database_instance_emitted[self.database_identifier] = event
            self.database_monitoring_metadata(json.dumps(event, default=default_json_event_encoding))

    def check(self, _):
        self.connect()
        self._query_manager.execute()
        self.collect_version()

        # Send database instance metadata
        self._send_database_instance_metadata()

        # Run query metrics collection if DBM is enabled (from system.query_log)
        if self.statement_metrics:
            self.statement_metrics.run_job_loop(self._tags)

        # Run statement samples if DBM is enabled (from system.processes)
        if self.statement_samples:
            self.statement_samples.run_job_loop(self._tags)

    @AgentCheck.metadata_entrypoint
    def collect_version(self):
        version = list(self.execute_query_raw('SELECT version()'))[0][0]

        # The version comes in like `19.15.2.2` though sometimes there is no patch part
        version_parts = dict(zip(('year', 'major', 'minor', 'patch'), version.split('.')))

        self.set_metadata('version', version, scheme='parts', final_scheme='calver', part_map=version_parts)

    def execute_query_raw(self, query):
        return self._client.query(query).result_rows

    def _get_debug_tags(self):
        """Return debug tags for metrics"""
        return ['server:{}'.format(self._server)]

    @property
    def reported_hostname(self):
        """
        Get the hostname to be reported in metrics and events.
        """
        if self._resolved_hostname is None:
            self._resolved_hostname = self._server
        return self._resolved_hostname

    @property
    def agent_hostname(self):
        """Get the agent hostname."""
        if self._agent_hostname is None:
            self._agent_hostname = datadog_agent.get_hostname()
        return self._agent_hostname

    @property
    def database_identifier(self):
        """
        Get a unique identifier for this database instance.
        """
        if self._database_identifier is None:
            # Create a unique identifier based on server, port, and database name
            self._database_identifier = "{}:{}:{}".format(self._server, self._port, self._db)
        return self._database_identifier

    def validate_config(self):
        if not self._server:
            raise ConfigurationError('the `server` setting is required')

        # Validate compression type
        if self._compression and self._compression not in ['lz4', 'zstd', 'br', 'gzip']:
            raise ConfigurationError(
                f'Invalid compression type "{self._compression}". Valid values are: lz4, zstd, br, gzip'
            )

    def ping_clickhouse(self):
        return self._client.ping()

    def connect(self):
        if self.instance.get('user'):
            self._log_deprecation('_config_renamed', 'user', 'username')
        if self._client is not None:
            self.log.debug('Clickhouse client already exists. Pinging Clickhouse Server.')
            try:
                if self.ping_clickhouse():
                    self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self._tags)
                    return
                else:
                    self.log.debug('Clickhouse connection ping failed. Attempting to reconnect')
                    self._client = None
            except Exception as e:
                self.log.debug('Unexpected ping response from Clickhouse', exc_info=e)
                self.log.debug('Attempting to reconnect')
                self._client = None

        try:
            client = clickhouse_connect.get_client(
                # https://clickhouse.com/docs/integrations/python#connection-arguments
                host=self._server,
                port=self._port,
                username=self._user,
                password=self._password,
                database=self._db,
                secure=self._tls_verify,
                connect_timeout=self._connect_timeout,
                send_receive_timeout=self._read_timeout,
                client_name=f'datadog-{self.check_id}',
                compress=self._compression,
                ca_cert=self._tls_ca_cert,
                verify=self._verify,
                # https://clickhouse.com/docs/integrations/language-clients/python/driver-api#multi-threaded-applications
                autogenerate_session_id=False,
                # https://clickhouse.com/docs/integrations/python#settings-argument
                settings={},
            )
        except Exception as e:
            error = 'Unable to connect to ClickHouse: {}'.format(
                self._error_sanitizer.clean(self._error_sanitizer.scrub(str(e)))
            )
            self.service_check(self.SERVICE_CHECK_CONNECT, self.CRITICAL, message=error, tags=self._tags)
            raise type(e)(error) from None
        else:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self._tags)
            self._client = client

    def create_dbm_client(self):
        """
        Create a separate ClickHouse client for DBM async jobs.
        This prevents concurrent query errors when multiple jobs run simultaneously.
        """
        try:
            client = clickhouse_connect.get_client(
                host=self._server,
                port=self._port,
                username=self._user,
                password=self._password,
                database=self._db,
                secure=self._tls_verify,
                connect_timeout=self._connect_timeout,
                send_receive_timeout=self._read_timeout,
                client_name=f'datadog-dbm-{self.check_id}',
                compress=self._compression,
                ca_cert=self._tls_ca_cert,
                verify=self._verify,
                settings={},
            )
            return client
        except Exception as e:
            error = 'Unable to create DBM client: {}'.format(
                self._error_sanitizer.clean(self._error_sanitizer.scrub(str(e)))
            )
            self.log.warning(error)
            raise
