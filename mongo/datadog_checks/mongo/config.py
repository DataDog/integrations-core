# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import certifi

from datadog_checks.base import ConfigurationError, is_affirmative
from datadog_checks.base.utils.common import exclude_undefined_keys
from datadog_checks.mongo.common import DEFAULT_TIMEOUT
from datadog_checks.mongo.utils import build_connection_string, parse_mongo_uri


class MongoConfig(object):
    def __init__(self, instance, log, init_config):
        self.log = log
        self.min_collection_interval = int(instance.get('min_collection_interval', 15))

        # x.509 authentication

        cacert_cert_dir = instance.get('tls_ca_file')
        if cacert_cert_dir is None and (
            is_affirmative(instance.get('options', {}).get("tls")) or is_affirmative(instance.get('tls'))
        ):
            cacert_cert_dir = certifi.where()

        self.tls_params = exclude_undefined_keys(
            {
                'tls': instance.get('tls'),
                'tlsCertificateKeyFile': instance.get('tls_certificate_key_file'),
                'tlsCAFile': cacert_cert_dir,
                'tlsAllowInvalidHostnames': instance.get('tls_allow_invalid_hostnames'),
                'tlsAllowInvalidCertificates': instance.get('tls_allow_invalid_certificates'),
            }
        )

        self.log.debug('tls_params: %s', self.tls_params)

        if 'server' in instance:
            self.server = instance['server']
            (
                self.username,
                self.password,
                self.db_name,
                self.hosts,
                _,
                self.auth_source,
            ) = parse_mongo_uri(self.server, sanitize_username=bool(self.tls_params))
            self.scheme = None
            self.additional_options = {}
            self.hosts = ["%s:%s" % (host[0], host[1]) for host in self.hosts]
        else:
            self.server = None
            self.hosts = instance.get('hosts', [])
            if type(self.hosts) == str:
                self.hosts = [self.hosts]
            self.username = instance.get('username')
            self.password = instance.get('password')
            self.scheme = instance.get('connection_scheme', 'mongodb')
            self.db_name = instance.get('database')
            self.additional_options = instance.get('options', {})
            if 'replicaSet' in self.additional_options:
                raise ConfigurationError(
                    'Setting the `replicaSet` option is not supported. '
                    'Configure one check instance for each node instead'
                )
            self.auth_source = self.additional_options.get('authSource') or self.db_name or 'admin'

        if not self.hosts:
            raise ConfigurationError('No `hosts` specified')

        self.clean_server_name = self._get_clean_server_name()
        if self.password and not self.username:
            raise ConfigurationError('`username` must be set when a `password` is specified')

        if not self.db_name:
            self.log.info('No MongoDB database found in URI. Defaulting to admin.')
            self.db_name = 'admin'

        self.db_names = instance.get('dbnames', None)

        self.timeout = float(instance.get('timeout', DEFAULT_TIMEOUT)) * 1000
        self.additional_metrics = instance.get('additional_metrics', [])

        # Authenticate
        self.do_auth = True
        self.use_x509 = self.tls_params and not self.password
        if not self.username:
            self.log.info("Disabling authentication because a username was not provided.")
            self.do_auth = False

        self.replica_check = is_affirmative(instance.get('replica_check', True))
        self.dbstats_tag_dbname = is_affirmative(instance.get('dbstats_tag_dbname', True))

        self.add_node_tag_to_events = is_affirmative(instance.get('add_node_tag_to_events', True))
        self.collections_indexes_stats = is_affirmative(instance.get('collections_indexes_stats'))
        self.coll_names = instance.get('collections', [])
        self.custom_queries = instance.get("custom_queries", [])
        self._metrics_collection_interval = instance.get("metrics_collection_interval", {})

        self._base_tags = list(set(instance.get('tags', [])))

        # DBM config options
        self.dbm_enabled = is_affirmative(instance.get('dbm', False))
        self.database_instance_collection_interval = instance.get('database_instance_collection_interval', 300)
        self.cluster_name = instance.get('cluster_name', None)
        self.cloud_metadata = self._compute_cloud_metadata(instance)
        self._operation_samples_config = instance.get('operation_samples', {})
        self._slow_operations_config = instance.get('slow_operations', {})
        self._schemas_config = instance.get('schemas', {})

        if self.dbm_enabled and not self.cluster_name:
            raise ConfigurationError('`cluster_name` must be set when `dbm` is enabled')

        # MongoDB instance hostname override
        self.reported_database_hostname = instance.get('reported_database_hostname', None)

        # MongoDB database auto-discovery, disabled by default
        self.database_autodiscovery_config = self._get_database_autodiscovery_config(instance)

        # Generate tags for service checks and metrics
        # TODO: service check and metric tags should be updated to be dynamic with auto-discovered databases
        self.service_check_tags = self._compute_service_check_tags()
        self.metric_tags = self._compute_metric_tags()
        self.service = instance.get('service') or init_config.get('service') or ''

    def _get_clean_server_name(self):
        try:
            if not self.server:
                server = build_connection_string(
                    self.hosts,
                    username=self.username,
                    password=self.password,
                    scheme=self.scheme,
                    database=self.db_name,
                    options=self.additional_options,
                )
            else:
                server = self.server

            self.log.debug("Parsing mongo uri with server: %s", server)
            return parse_mongo_uri(server, sanitize_username=bool(self.tls_params))[4]
        except Exception as e:
            raise ConfigurationError(
                "Could not build a mongo uri with the given hosts: %s. Error: %s" % (self.hosts, repr(e))
            )

    def _compute_service_check_tags(self):
        main_host = self.hosts[0]
        main_port = "27017"
        if ':' in main_host:
            main_host, main_port = main_host.split(':')

        service_check_tags = ["db:%s" % self.db_name, "host:%s" % main_host, "port:%s" % main_port] + self._base_tags
        if self.cluster_name:
            service_check_tags.append('clustername:%s' % self.cluster_name)
        return service_check_tags

    def _compute_metric_tags(self):
        tags = self._base_tags + ['server:%s' % self.clean_server_name]
        if self.cluster_name:
            tags.append('clustername:%s' % self.cluster_name)
        return tags

    def _compute_cloud_metadata(self, instance):
        cloud_metadata = {}
        if aws := instance.get('aws'):
            cloud_metadata['aws'] = {
                'instance_endpoint': aws.get('instance_endpoint'),
                'cluster_identifier': aws.get('cluster_identifier') or self.cluster_name,
            }
        return cloud_metadata

    @property
    def operation_samples(self):
        enabled = False
        if self.dbm_enabled is True and self._operation_samples_config.get('enabled') is not False:
            # if DBM is enabled and the operation samples config is not explicitly disabled, then it is enabled
            enabled = True
        return {
            'enabled': enabled,
            'collection_interval': self._operation_samples_config.get('collection_interval', 10),
            'run_sync': is_affirmative(self._operation_samples_config.get('run_sync', False)),
            'explained_operations_cache_maxsize': int(
                self._operation_samples_config.get('explained_operations_cache_maxsize', 5000)
            ),
            'explained_operations_per_hour_per_query': int(
                self._operation_samples_config.get('explained_operations_per_hour_per_query', 10)
            ),
        }

    @property
    def slow_operations(self):
        enabled = False
        if self.dbm_enabled is True and self._slow_operations_config.get('enabled') is not False:
            # if DBM is enabled and the operation metrics config is not explicitly disabled, then it is enabled
            enabled = True
        return {
            'enabled': enabled,
            'collection_interval': self._slow_operations_config.get('collection_interval', 10),
            'run_sync': is_affirmative(self._slow_operations_config.get('run_sync', False)),
            'max_operations': int(self._slow_operations_config.get('max_operations', 1000)),
            'explained_operations_cache_maxsize': int(
                self._slow_operations_config.get('explained_operations_cache_maxsize', 5000)
            ),
            'explained_operations_per_hour_per_query': int(
                self._slow_operations_config.get('explained_operations_per_hour_per_query', 10)
            ),
        }

    @property
    def schemas(self):
        enabled = False
        if self.dbm_enabled is True and self._schemas_config.get('enabled') is not False:
            # if DBM is enabled and the schemas config is not explicitly disabled, then it is enabled
            enabled = True
        max_collections = self._schemas_config.get('max_collections')
        return {
            'enabled': enabled,
            'collection_interval': self._schemas_config.get('collection_interval', 3600),
            'run_sync': is_affirmative(self._schemas_config.get('run_sync', True)),
            'sample_size': int(self._schemas_config.get('sample_size', 10)),
            'max_collections': int(max_collections) if max_collections else None,
            'max_depth': int(self._schemas_config.get('max_depth', 5)),  # Default to 5
            'collect_search_indexes': is_affirmative(self._schemas_config.get('collect_search_indexes', False)),
        }

    def _get_database_autodiscovery_config(self, instance):
        database_autodiscovery_config = instance.get('database_autodiscovery', {"enabled": False})
        if database_autodiscovery_config['enabled']:
            if self.db_name != 'admin':
                # If database_autodiscovery is enabled, the `database` parameter should not be set
                # because we want to monitor all databases. Unless the `database` parameter is set to 'admin'.
                self.log.warning(
                    "The `database` parameter should not be set when `database_autodiscovery` is enabled. "
                    "The `database` parameter will be ignored."
                )
            if self.coll_names:
                self.log.warning(
                    "The `collections` parameter should not be set when `database_autodiscovery` is enabled. "
                    "The `collections` parameter will be ignored."
                )
        if self.db_names:
            # dbnames is deprecated and will be removed in a future version
            self.log.warning(
                "The `dbnames` parameter is deprecated and will be removed in a future version. "
                "To monitor more databases, enable `database_autodiscovery` and use "
                "`database_autodiscovery.include` instead."
            )
            include_list = [f"{db}$" for db in self.db_names]  # Append $ to each db name for exact match
            if not database_autodiscovery_config['enabled']:
                # if database_autodiscovery is not enabled, we should enable it
                database_autodiscovery_config['enabled'] = True
            if not database_autodiscovery_config.get('include'):
                # if database_autodiscovery is enabled but include list is not set, set the include list
                database_autodiscovery_config['include'] = include_list
        # Limit the maximum number of collections per database to monitor
        database_autodiscovery_config["max_collections_per_database"] = int(
            database_autodiscovery_config.get("max_collections_per_database", 100)
        )
        return database_autodiscovery_config

    @property
    def metrics_collection_interval(self):
        '''
        metrics collection interval is used to customize how often to collect different types of metrics
        by default, metrics are collected on every check run with default interval of 15 seconds
        '''
        return {
            # $collStats and $indexStats are collected on every check run but they can get expensive on large databases
            'collection': int(self._metrics_collection_interval.get('collection', self.min_collection_interval)),
            'collections_indexes_stats': int(
                self._metrics_collection_interval.get('collections_indexes_stats', self.min_collection_interval)
            ),
            # $shardDataDistribution stats are collected every 5 minutes by default due to the high resource usage
            'sharded_data_distribution': int(self._metrics_collection_interval.get('sharded_data_distribution', 300)),
        }
