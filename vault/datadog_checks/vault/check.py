# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

from datadog_checks.base import OpenMetricsBaseCheckV2, is_affirmative
from datadog_checks.base.checks.openmetrics.v2.transform import NATIVE_TRANSFORMERS
from datadog_checks.base.utils.time import get_timestamp

from .common import API_METHODS, DEFAULT_API_VERSION, SYS_HEALTH_DEFAULT_CODES, SYS_LEADER_DEFAULT_CODES, Api, Leader
from .config_models import ConfigMixin
from .metrics import METRIC_MAP, ROUTE_METRICS_TO_TRANSFORM, construct_metrics_config


class VaultCheckV2(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'vault'

    DEFAULT_METRIC_LIMIT = 0
    CHECK_NAME = 'vault'
    EVENT_LEADER_CHANGE = 'leader_change'
    SERVICE_CHECK_CONNECT = 'can_connect'
    SERVICE_CHECK_UNSEALED = 'unsealed'
    SERVICE_CHECK_INITIALIZED = 'initialized'

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)

        self._api_url = ''
        self._metrics_url = ''
        self._tags = ()

        # Determine the appropriate methods later
        self._api = None

        # Keep track of the previous cluster leader to detect changes
        self._previous_leader = None

        # we skip metric collection for DR if Vault is in replication mode
        # and collect_secondary_dr is not enabled
        self._skip_dr_metric_collection = False

        # Might not be configured for metric collection
        self.scraper_configs.clear()

        # https://www.vaultproject.io/api-docs#the-x-vault-request-header
        self.http.options['headers']['X-Vault-Request'] = 'true'

        # Before scrapers are configured
        self.check_initializations.insert(-1, self.parse_config)

        self.check_initializations.append(self.configure_additional_transformers)

    @property
    def metric_collection_enabled(self):
        return self.config.no_token or self.config.client_token_path or self.config.client_token

    def check(self, _):
        submission_queue = []
        dynamic_tags = []

        # Useful data comes from multiple endpoints so we collect the
        # tags and then submit everything with access to all tags
        try:
            self._api.check_leader(submission_queue, dynamic_tags)
            self._api.check_health(submission_queue, dynamic_tags)
        finally:
            tags = list(self._tags)
            tags.extend(dynamic_tags)
            for submit_function in submission_queue:
                submit_function(tags=tags)

        if self.metric_collection_enabled and not self._skip_dr_metric_collection:
            self.set_dynamic_tags(*dynamic_tags)
            super().check(_)

        self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self._tags)

    def check_leader_v1(self, submission_queue, dynamic_tags):
        url = self._api_url + '/sys/leader'
        leader_data = self.access_api(url, ignore_status_codes=SYS_LEADER_DEFAULT_CODES)
        errors = leader_data.get('errors')
        if errors:
            error_msg = ';'.join(errors)
            self.log.error('Unable to fetch leader data from Vault. Reason: %s', error_msg)
            return

        is_leader = is_affirmative(leader_data.get('is_self'))
        dynamic_tags.append(f'is_leader:{str(is_leader).lower()}')

        submission_queue.append(lambda tags: self.gauge('is_leader', int(is_leader), tags=tags))

        current_leader = Leader(leader_data.get('leader_address'), leader_data.get('leader_cluster_address'))
        has_leader = any(current_leader)  # At least one address is set

        if self.config.detect_leader and has_leader:
            if self._previous_leader is None:
                # First check run, let's set the previous leader variable.
                self._previous_leader = current_leader
                return
            if self._previous_leader == current_leader:
                # Leader hasn't changed
                return
            if not is_leader:
                # Leader has changed but the monitored vault node is not the leader. Because the agent monitors
                # each vault node in the cluster, let's use this condition to submit a single event.
                self._previous_leader = current_leader
                self.log.debug(
                    'Leader changed from %s to %s but not reporting an event as the current node is not the leader.',
                    self._previous_leader,
                    current_leader,
                )
                return

            if current_leader.leader_addr != self._previous_leader.leader_addr:
                # The main leader address has changed
                event_message = (
                    f'Leader address changed from `{self._previous_leader.leader_addr}` to '
                    f'`{current_leader.leader_addr}`.'
                )
            else:
                # The leader_cluster_addr changed (usually happen when the leader address points to a load balancer
                event_message = (
                    f'Leader cluster address changed from `{self._previous_leader.leader_cluster_addr}` to '
                    f'`{current_leader.leader_cluster_addr}`.'
                )

            self.log.debug('Leader changed from %s to %s, sending the event.', self._previous_leader, current_leader)
            submission_queue.append(
                lambda tags: self.event(
                    {
                        'timestamp': get_timestamp(),
                        'event_type': self.EVENT_LEADER_CHANGE,
                        'msg_title': 'Leader change',
                        'msg_text': event_message,
                        'alert_type': 'info',
                        'host': self.hostname,
                        'tags': tags,
                    }
                )
            )
            # Update _previous_leader for the next run
            self._previous_leader = current_leader

    def check_health_v1(self, submission_queue, dynamic_tags):
        url = self._api_url + '/sys/health'
        health_data = self.access_api(url, ignore_status_codes=SYS_HEALTH_DEFAULT_CODES)
        cluster_name = health_data.get('cluster_name')
        if cluster_name:
            dynamic_tags.append(f'vault_cluster:{cluster_name}')

        replication_mode = health_data.get('replication_dr_mode', '').lower()
        if replication_mode == 'secondary':
            if self.config.collect_secondary_dr:
                self._skip_dr_metric_collection = False
                self.log.debug(
                    'Detected vault in replication DR secondary mode but also detected that '
                    '`collect_secondary_dr` is enabled, OpenMetrics metric collection will still occur.'
                )
            else:
                self._skip_dr_metric_collection = True
                self.log.debug(
                    'Detected vault in replication DR secondary mode, skipping Prometheus metric collection.'
                )
        else:
            self._skip_dr_metric_collection = False

        vault_version = health_data.get('version')
        if vault_version:
            dynamic_tags.append(f'vault_version:{vault_version}')
            self.set_metadata('version', vault_version)

        unsealed = not is_affirmative(health_data.get('sealed'))
        if unsealed:
            submission_queue.append(lambda tags: self.service_check(self.SERVICE_CHECK_UNSEALED, self.OK, tags=tags))
        else:
            submission_queue.append(
                lambda tags: self.service_check(self.SERVICE_CHECK_UNSEALED, self.CRITICAL, tags=tags)
            )

        initialized = is_affirmative(health_data.get('initialized'))
        if initialized:
            submission_queue.append(lambda tags: self.service_check(self.SERVICE_CHECK_INITIALIZED, self.OK, tags=tags))
        else:
            submission_queue.append(
                lambda tags: self.service_check(self.SERVICE_CHECK_INITIALIZED, self.CRITICAL, tags=tags)
            )

    def access_api(self, url, ignore_status_codes=None):
        if ignore_status_codes is None:
            ignore_status_codes = []

        try:
            response = self.http.get(url)
            if response.status_code not in ignore_status_codes:
                response.raise_for_status()

            return response.json()
        except Exception as e:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.CRITICAL, message=str(e), tags=self._tags)
            raise

    def parse_config(self):
        self._api_url = self.config.api_url
        api_version = self._api_url[-1]
        if api_version not in ('1',):
            self.log.warning('Unknown Vault API version `%s`, using version `%s`', api_version, DEFAULT_API_VERSION)
            api_version = DEFAULT_API_VERSION
            self._api_url = self._api_url[:-1] + api_version

        self._metrics_url = f'{self._api_url}/sys/metrics?format=prometheus'

        methods = {method: getattr(self, f'{method}_v{api_version}') for method in API_METHODS}
        self._api = Api(**methods)

        tags = [f'api_url:{self._api_url}']
        tags.extend(self.config.tags)
        self._tags = tuple(tags)

    def configure_scrapers(self):
        if self.metric_collection_enabled:
            config = deepcopy(self.instance)

            config['openmetrics_endpoint'] = self._metrics_url
            config['tags'] = list(self._tags)

            # https://www.vaultproject.io/api-docs#the-x-vault-request-header
            config.setdefault('headers', {})['X-Vault-Request'] = 'true'

            if not self.config.no_token:
                if self.config.client_token_path:
                    self.HTTP_CONFIG_REMAPPER = {
                        'auth_token': {
                            'name': 'auth_token',
                            'default': {
                                'reader': {'type': 'file', 'path': self.config.client_token_path},
                                'writer': {'type': 'header', 'name': 'X-Vault-Token'},
                            },
                        }
                    }
                if self.config.client_token:
                    config['headers']['X-Vault-Token'] = self.config.client_token

            self.scraper_configs.clear()
            self.scraper_configs.append(config)

        super().configure_scrapers()

    def get_default_config(self):
        return {'metrics': construct_metrics_config(METRIC_MAP, {})}

    def configure_transformer_route_metrics(self):
        cached_metric_data = {}

        def route_metrics_transformer(metric, sample_data, runtime_data):
            if metric.name in cached_metric_data:
                transformer, metric_name, mount_tag = cached_metric_data[metric.name]
            else:
                parts = metric.name.rstrip('_').split('_')
                metric_name = '.'.join(parts[:3])
                mount_tag = f'mountpoint:{"_".join(parts[3:])}'
                transformer = NATIVE_TRANSFORMERS[metric.type](self, metric_name, {}, {})
                cached_metric_data[metric.name] = transformer, metric_name, mount_tag

            new_sample_data = []
            for sample, tags, hostname in sample_data:
                tags.append(mount_tag)
                new_sample_data.append((sample, tags, hostname))

            transformer(metric, new_sample_data, runtime_data)

        return route_metrics_transformer

    def configure_additional_transformers(self):
        if not self.scrapers:
            return

        metric_transformer = self.scrapers[self._metrics_url].metric_transformer
        metric_transformer.add_custom_transformer(
            '|'.join(f'{prefix}.+' for prefix in ROUTE_METRICS_TO_TRANSFORM),
            self.configure_transformer_route_metrics(),
            pattern=True,
        )
