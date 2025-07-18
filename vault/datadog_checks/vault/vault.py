# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

import requests

from datadog_checks.base import OpenMetricsBaseCheck, is_affirmative

from .check import VaultCheckV2
from .common import API_METHODS, DEFAULT_API_VERSION, SYS_HEALTH_DEFAULT_CODES, SYS_LEADER_DEFAULT_CODES, Api, Leader
from .errors import ApiUnreachable
from .metrics import METRIC_MAP, METRIC_ROLLBACK_COMPAT_MAP, ROUTE_METRICS_TO_TRANSFORM

try:
    from json import JSONDecodeError
except ImportError:
    from simplejson import JSONDecodeError


class Vault(OpenMetricsBaseCheck):
    DEFAULT_METRIC_LIMIT = 0
    CHECK_NAME = 'vault'
    EVENT_LEADER_CHANGE = 'vault.leader_change'
    SERVICE_CHECK_CONNECT = 'vault.can_connect'
    SERVICE_CHECK_UNSEALED = 'vault.unsealed'
    SERVICE_CHECK_INITIALIZED = 'vault.initialized'

    HTTP_CONFIG_REMAPPER = {
        'ssl_verify': {'name': 'tls_verify'},
        'ssl_cert': {'name': 'tls_cert'},
        'ssl_private_key': {'name': 'tls_private_key'},
        'ssl_ca_cert': {'name': 'tls_ca_cert'},
        'ssl_ignore_warning': {'name': 'tls_ignore_warning'},
    }

    def __new__(cls, name, init_config, instances):
        instance = instances[0]

        if is_affirmative(instance.get('use_openmetrics', False)):
            return VaultCheckV2(name, init_config, instances)
        else:
            return super(Vault, cls).__new__(cls)

    def __init__(self, name, init_config, instances):
        super(Vault, self).__init__(
            name,
            init_config,
            instances,
            default_instances={
                self.CHECK_NAME: {'namespace': self.CHECK_NAME, 'metrics': [METRIC_MAP] + ROUTE_METRICS_TO_TRANSFORM},
            },
            default_namespace=self.CHECK_NAME,
        )

        self._api_url = self.instance.get('api_url', '')
        self._client_token = self.instance.get('client_token')
        self._client_token_path = self.instance.get('client_token_path')
        self._no_token = is_affirmative(self.instance.get('no_token', False))
        self._tags = list(self.instance.get('tags', []))
        self._tags.append('api_url:{}'.format(self._api_url))
        self._disable_legacy_cluster_tag = is_affirmative(self.instance.get('disable_legacy_cluster_tag', False))
        self._collect_secondary_dr = is_affirmative(self.instance.get('collect_secondary_dr', False))

        # Keep track of the previous cluster leader to detect changes
        self._previous_leader = None
        self._detect_leader = is_affirmative(self.instance.get('detect_leader', False))

        # Determine the appropriate methods later
        self._api = None

        # Only collect OpenMetrics if we are given tokens
        self._scraper_config = None

        # Avoid error on the first attempt to refresh tokens
        self._refreshing_token = False

        # we skip metric collection for DR if Vault is in replication mode
        # and collect_secondary_dr is not enabled
        self._skip_dr_metric_collection = False

        # The Agent only makes one attempt to instantiate each AgentCheck so any errors occurring
        # in `__init__` are logged just once, making it difficult to spot. Therefore, we emit
        # potential configuration errors as part of the check run phase.
        self.check_initializations.append(self.parse_config)

        self._metric_transformers = {
            'vault_route_create_*': self.transform_route_metrics,
            'vault_route_delete_*': self.transform_route_metrics,
            'vault_route_list_*': self.transform_route_metrics,
            'vault_route_read_*': self.transform_route_metrics,
            'vault_route_rollback_*': self.transform_route_metrics,
        }

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

        if (self._client_token or self._no_token) and not self._skip_dr_metric_collection:
            self._scraper_config['_metric_tags'] = dynamic_tags
            try:
                self.process(self._scraper_config, self._metric_transformers)
            except Exception as e:
                error = str(e)
                if self._client_token_path and error.startswith('403 Client Error: Forbidden for url'):
                    message = 'Permission denied, refreshing the client token...'
                    self.log.warning(message)
                    self.renew_client_token()

                    if not self._refreshing_token:
                        self._refreshing_token = True
                        self.service_check(self.SERVICE_CHECK_CONNECT, self.WARNING, message=message, tags=self._tags)
                        return

                self.service_check(self.SERVICE_CHECK_CONNECT, self.CRITICAL, message=error, tags=self._tags)
                raise
            else:
                self._refreshing_token = False

        self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self._tags)

    def check_leader_v1(self, submission_queue, dynamic_tags):
        url = self._api_url + '/sys/leader'
        leader_data = self.access_api(url, ignore_status_codes=SYS_LEADER_DEFAULT_CODES)
        errors = leader_data.get('errors')
        if errors:
            error_msg = ';'.join(errors)
            self.log.error('Unable to fetch leader data from vault. Reason: %s', error_msg)
            return

        is_leader = is_affirmative(leader_data.get('is_self'))
        dynamic_tags.append('is_leader:{}'.format('true' if is_leader else 'false'))

        submission_queue.append(lambda tags: self.gauge('vault.is_leader', int(is_leader), tags=tags))

        current_leader = Leader(leader_data.get('leader_address'), leader_data.get('leader_cluster_address'))
        has_leader = any(current_leader)  # At least one address is set

        if self._detect_leader and has_leader:
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
                    "Leader changed from %s to %s but not reporting an event as the current node is not the leader.",
                    self._previous_leader,
                    current_leader,
                )
                return

            if current_leader.leader_addr != self._previous_leader.leader_addr:
                # The main leader address has changed
                event_message = "Leader address changed from `{}` to `{}`.".format(
                    self._previous_leader.leader_addr, current_leader.leader_addr
                )
            else:
                # The leader_cluster_addr changed (usually happen when the leader address points to a load balancer
                event_message = "Leader cluster address changed from `{}` to `{}`.".format(
                    self._previous_leader.leader_cluster_addr, current_leader.leader_cluster_addr
                )

            self.log.debug("Leader changed from %s to %s, sending the event.", self._previous_leader, current_leader)
            submission_queue.append(
                lambda tags: self.event(
                    {
                        'timestamp': time.time(),
                        'event_type': self.EVENT_LEADER_CHANGE,
                        'msg_title': 'Leader change',
                        'msg_text': event_message,
                        'alert_type': 'info',
                        'source_type_name': self.CHECK_NAME,
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
            dynamic_tags.append('vault_cluster:{}'.format(cluster_name))
            if not self._disable_legacy_cluster_tag:
                dynamic_tags.append('cluster_name:{}'.format(cluster_name))

        replication_mode = health_data.get('replication_dr_mode', '').lower()
        if replication_mode == 'secondary':
            if self._collect_secondary_dr:
                self._skip_dr_metric_collection = False
                self.log.debug(
                    'Detected vault in replication DR secondary mode but also detected that '
                    '`collect_secondary_dr` is enabled, Prometheus metric collection will still occur.'
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
            dynamic_tags.append('vault_version:{}'.format(vault_version))
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
            status_code = response.status_code
            if status_code >= 400 and status_code not in ignore_status_codes:
                msg = 'The Vault endpoint `{}` returned {}'.format(url, status_code)
                self.service_check(self.SERVICE_CHECK_CONNECT, self.CRITICAL, message=msg, tags=self._tags)
                raise ApiUnreachable(msg)
            json_data = response.json()
        except JSONDecodeError as e:
            msg = 'The Vault endpoint `{}` returned invalid json data: {}.'.format(url, e)
            self.service_check(self.SERVICE_CHECK_CONNECT, self.CRITICAL, message=msg, tags=self._tags)
            raise ApiUnreachable(msg)
        except requests.exceptions.Timeout:
            msg = 'Vault endpoint `{}` timed out after {} seconds'.format(url, self.http.options['timeout'][0])
            self.service_check(self.SERVICE_CHECK_CONNECT, self.CRITICAL, message=msg, tags=self._tags)
            raise ApiUnreachable(msg)
        except (requests.exceptions.RequestException, requests.exceptions.ConnectionError) as e:
            msg = 'Error accessing Vault endpoint `{}`: {}'.format(url, e)
            self.service_check(self.SERVICE_CHECK_CONNECT, self.CRITICAL, message=msg, tags=self._tags)
            raise ApiUnreachable(msg)

        return json_data

    def parse_config(self):
        api_version = self._api_url[-1]
        if api_version not in ('1',):
            self.log.warning('Unknown Vault API version `%s`, using version `%s`', api_version, DEFAULT_API_VERSION)
            api_version = DEFAULT_API_VERSION
            self._api_url = self._api_url[:-1] + api_version

        methods = {method: getattr(self, '{}_v{}'.format(method, api_version)) for method in API_METHODS}
        self._api = Api(**methods)

        if self._client_token_path or self._client_token or self._no_token:
            instance = self.instance.copy()
            instance['prometheus_url'] = '{}/sys/metrics?format=prometheus'.format(self._api_url)

            # Send histograms & summaries counts as monotonic_counter
            instance['send_distribution_counts_as_monotonic'] = True

            # Remap important options until OpenMetricsBaseCheck uses the RequestsWrapper
            instance['ssl_verify'] = instance.pop('tls_verify', None)
            instance['ssl_cert'] = instance.pop('tls_cert', None)
            instance['ssl_private_key'] = instance.pop('tls_private_key', None)
            instance['ssl_ca_cert'] = instance.pop('tls_ca_cert', None)

            self._scraper_config = self.create_scraper_configuration(instance)

            # Global static tags
            self._scraper_config['custom_tags'] = self._tags

            # https://www.vaultproject.io/api/overview#the-x-vault-request-header
            self._set_header(self.get_http_handler(self._scraper_config), 'X-Vault-Request', 'true')

            if not self._no_token:
                if self._client_token_path:
                    self.renew_client_token()
                else:
                    self.set_client_token(self._client_token)

        # https://www.vaultproject.io/api-docs#the-x-vault-request-header
        self._set_header(self.http, 'X-Vault-Request', 'true')

    def set_client_token(self, client_token):
        self._client_token = client_token
        self._set_header(self.http, 'X-Vault-Token', client_token)
        self._set_header(self.get_http_handler(self._scraper_config), 'X-Vault-Token', client_token)

    def renew_client_token(self):
        with open(self._client_token_path, 'rb') as f:
            self.set_client_token(f.read().decode('utf-8'))

    def _set_header(self, http_wrapper, header, value):
        http_wrapper.options['headers'][header] = value

    def get_scraper_config(self, instance):
        # This validation is called during `__init__` but we don't need it
        pass

    def transform_route_metrics(self, metric, scraper_config, transformerkey):
        # Backward compatibility: submit old metric
        if metric.name in METRIC_ROLLBACK_COMPAT_MAP:
            self.submit_openmetric(METRIC_ROLLBACK_COMPAT_MAP[metric.name], metric, scraper_config)

        metric_name = metric.name.replace('_', '.').rstrip('.')

        # Remove extra vault prefix
        if metric_name.startswith('vault.'):
            metric_name = metric_name[len('vault.') :]

        metric_tag = metric.name[len(transformerkey) - 1 : -1]
        for i in metric.samples:
            i.labels['mountpoint'] = metric_tag

        normalized_metric_name = metric_name.replace('.' + metric_tag, '')
        self.submit_openmetric(normalized_metric_name, metric, scraper_config)
