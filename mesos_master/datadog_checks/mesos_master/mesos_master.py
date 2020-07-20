# (C) Datadog, Inc. 2015-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

"""Mesos Master check

Collects metrics from mesos master node, only the leader is sending metrics.
"""
import requests
from six import iteritems
from six.moves.urllib.parse import urlparse

from datadog_checks.base import AgentCheck
from datadog_checks.base.errors import CheckException


class MesosMaster(AgentCheck):
    GAUGE = AgentCheck.gauge
    MONOTONIC_COUNT = AgentCheck.monotonic_count
    SERVICE_CHECK_NAME = "mesos_master.can_connect"
    service_check_needed = True
    DEFAULT_TIMEOUT = 5

    FRAMEWORK_METRICS = {
        'cpus': ('mesos.framework.cpu', GAUGE),
        'mem': ('mesos.framework.mem', GAUGE),
        'disk': ('mesos.framework.disk', GAUGE),
    }

    ROLE_RESOURCES_METRICS = {
        'cpus': ('mesos.role.cpu', GAUGE),
        'mem': ('mesos.role.mem', GAUGE),
        'disk': ('mesos.role.disk', GAUGE),
    }

    # These metrics are aggregated only on the elected master
    CLUSTER_TASKS_METRICS = {
        'master/tasks_error': ('mesos.cluster.tasks_error', GAUGE),
        'master/tasks_failed': ('mesos.cluster.tasks_failed', MONOTONIC_COUNT),
        'master/tasks_finished': ('mesos.cluster.tasks_finished', MONOTONIC_COUNT),
        'master/tasks_killed': ('mesos.cluster.tasks_killed', MONOTONIC_COUNT),
        'master/tasks_lost': ('mesos.cluster.tasks_lost', MONOTONIC_COUNT),
        'master/tasks_running': ('mesos.cluster.tasks_running', GAUGE),
        'master/tasks_staging': ('mesos.cluster.tasks_staging', GAUGE),
        'master/tasks_starting': ('mesos.cluster.tasks_starting', GAUGE),
    }

    # These metrics are aggregated only on the elected master
    CLUSTER_SLAVES_METRICS = {
        'master/slave_registrations': ('mesos.cluster.slave_registrations', GAUGE),
        'master/slave_removals': ('mesos.cluster.slave_removals', GAUGE),
        'master/slave_reregistrations': ('mesos.cluster.slave_reregistrations', GAUGE),
        'master/slave_shutdowns_canceled': ('mesos.cluster.slave_shutdowns_canceled', GAUGE),
        'master/slave_shutdowns_scheduled': ('mesos.cluster.slave_shutdowns_scheduled', GAUGE),
        'master/slaves_active': ('mesos.cluster.slaves_active', GAUGE),
        'master/slaves_connected': ('mesos.cluster.slaves_connected', GAUGE),
        'master/slaves_disconnected': ('mesos.cluster.slaves_disconnected', GAUGE),
        'master/slaves_inactive': ('mesos.cluster.slaves_inactive', GAUGE),
        'master/recovery_slave_removals': ('mesos.cluster.recovery_slave_removals', GAUGE),
    }

    # These metrics are aggregated only on the elected master
    CLUSTER_RESOURCES_METRICS = {
        'master/cpus_percent': ('mesos.cluster.cpus_percent', GAUGE),
        'master/cpus_total': ('mesos.cluster.cpus_total', GAUGE),
        'master/cpus_used': ('mesos.cluster.cpus_used', GAUGE),
        'master/gpus_percent': ('mesos.cluster.gpus_percent', GAUGE),
        'master/gpus_total': ('mesos.cluster.gpus_total', GAUGE),
        'master/gpus_used': ('mesos.cluster.gpus_used', GAUGE),
        'master/disk_percent': ('mesos.cluster.disk_percent', GAUGE),
        'master/disk_total': ('mesos.cluster.disk_total', GAUGE),
        'master/disk_used': ('mesos.cluster.disk_used', GAUGE),
        'master/mem_percent': ('mesos.cluster.mem_percent', GAUGE),
        'master/mem_total': ('mesos.cluster.mem_total', GAUGE),
        'master/mem_used': ('mesos.cluster.mem_used', GAUGE),
    }

    # These metrics are aggregated only on the elected master
    CLUSTER_REGISTRAR_METRICS = {
        'registrar/queued_operations': ('mesos.registrar.queued_operations', GAUGE),
        'registrar/registry_size_bytes': ('mesos.registrar.registry_size_bytes', GAUGE),
        'registrar/state_fetch_ms': ('mesos.registrar.state_fetch_ms', GAUGE),
        'registrar/state_store_ms': ('mesos.registrar.state_store_ms', GAUGE),
        'registrar/state_store_ms/count': ('mesos.registrar.state_store_ms.count', GAUGE),
        'registrar/state_store_ms/max': ('mesos.registrar.state_store_ms.max', GAUGE),
        'registrar/state_store_ms/min': ('mesos.registrar.state_store_ms.min', GAUGE),
        'registrar/state_store_ms/p50': ('mesos.registrar.state_store_ms.p50', GAUGE),
        'registrar/state_store_ms/p90': ('mesos.registrar.state_store_ms.p90', GAUGE),
        'registrar/state_store_ms/p95': ('mesos.registrar.state_store_ms.p95', GAUGE),
        'registrar/state_store_ms/p99': ('mesos.registrar.state_store_ms.p99', GAUGE),
        'registrar/state_store_ms/p999': ('mesos.registrar.state_store_ms.p999', GAUGE),
        'registrar/state_store_ms/p9999': ('mesos.registrar.state_store_ms.p9999', GAUGE),
    }

    # These metrics are aggregated only on the elected master
    CLUSTER_FRAMEWORK_METRICS = {
        'master/frameworks_active': ('mesos.cluster.frameworks_active', GAUGE),
        'master/frameworks_connected': ('mesos.cluster.frameworks_connected', GAUGE),
        'master/frameworks_disconnected': ('mesos.cluster.frameworks_disconnected', GAUGE),
        'master/frameworks_inactive': ('mesos.cluster.frameworks_inactive', GAUGE),
    }

    # These metrics are aggregated on all nodes in the cluster
    SYSTEM_METRICS = {
        'system/cpus_total': ('mesos.stats.system.cpus_total', GAUGE),
        'system/load_15min': ('mesos.stats.system.load_15min', GAUGE),
        'system/load_1min': ('mesos.stats.system.load_1min', GAUGE),
        'system/load_5min': ('mesos.stats.system.load_5min', GAUGE),
        'system/mem_free_bytes': ('mesos.stats.system.mem_free_bytes', GAUGE),
        'system/mem_total_bytes': ('mesos.stats.system.mem_total_bytes', GAUGE),
        'master/elected': ('mesos.stats.elected', GAUGE),
        'master/uptime_secs': ('mesos.stats.uptime_secs', GAUGE),
        'registrar/log/recovered': ('mesos.registrar.log.recovered', GAUGE),
    }

    # These metrics are aggregated only on the elected master
    STATS_METRICS = {
        'master/dropped_messages': ('mesos.cluster.dropped_messages', GAUGE),
        'master/outstanding_offers': ('mesos.cluster.outstanding_offers', GAUGE),
        'master/event_queue_dispatches': ('mesos.cluster.event_queue_dispatches', GAUGE),
        'master/event_queue_http_requests': ('mesos.cluster.event_queue_http_requests', GAUGE),
        'master/event_queue_messages': ('mesos.cluster.event_queue_messages', GAUGE),
        'master/invalid_framework_to_executor_messages': (
            'mesos.cluster.invalid_framework_to_executor_messages',
            GAUGE,
        ),
        'master/invalid_status_update_acknowledgements': (
            'mesos.cluster.invalid_status_update_acknowledgements',
            GAUGE,
        ),
        'master/invalid_status_updates': ('mesos.cluster.invalid_status_updates', GAUGE),
        'master/valid_framework_to_executor_messages': ('mesos.cluster.valid_framework_to_executor_messages', GAUGE),
        'master/valid_status_update_acknowledgements': ('mesos.cluster.valid_status_update_acknowledgements', GAUGE),
        'master/valid_status_updates': ('mesos.cluster.valid_status_updates', GAUGE),
    }

    HTTP_CONFIG_REMAPPER = {'disable_ssl_validation': {'name': 'tls_verify', 'invert': True, 'default': False}}

    def __init__(self, name, init_config, instances):
        super(MesosMaster, self).__init__(name, init_config, instances)
        if self.instance is not None:
            url = self.instance.get('url', '')
            parsed_url = urlparse(url)

            if not self.http.options['verify'] and parsed_url.scheme == 'https':
                self.log.warning('Skipping TLS cert validation for %s based on configuration.', url)
            if not ('read_timeout' in self.instance or 'connect_timeout' in self.instance):
                # `default_timeout` config option will be removed with Agent 5
                timeout = (
                    self.instance.get('timeout')
                    or self.instance.get('default_timeout')
                    or self.init_config.get('timeout')
                    or self.init_config.get('default_timeout')
                    or self.DEFAULT_TIMEOUT
                )

                self.http.options['timeout'] = (timeout, timeout)

    def _get_json(self, url, failure_expected=False, tags=None):
        tags = tags + ["url:%s" % url] if tags else ["url:%s" % url]
        msg = None
        status = None
        timeout = self.http.options['timeout']
        response = None
        try:
            response = self.http.get(url)
            if response.status_code != 200:
                status = AgentCheck.CRITICAL
                msg = "Got %s when hitting %s" % (response.status_code, url)
            else:
                status = AgentCheck.OK
                msg = "Mesos master instance detected at %s " % url
        except requests.exceptions.Timeout:
            # If there's a timeout
            msg = "%s seconds timeout when hitting %s" % (timeout, url)
            status = AgentCheck.CRITICAL
        except Exception as e:
            msg = str(e)
            status = AgentCheck.CRITICAL
        finally:
            self.log.debug('Request to url : %s, timeout: %s, message: %s', url, timeout, msg)
            self._send_service_check(url, status, failure_expected=failure_expected, tags=tags, message=msg)

        if response.encoding is None:
            response.encoding = 'UTF8'

        return response.json()

    def _send_service_check(self, url, status, failure_expected=False, tags=None, message=None):
        skip_service_check = False
        if status is AgentCheck.CRITICAL and failure_expected:
            # skip service check when failure is expected
            skip_service_check = True
            message = "Error when calling {}: {}".format(url, message)
        elif status is AgentCheck.CRITICAL and not failure_expected:
            message = 'Cannot connect to mesos. Error: {0}'.format(message)
        if self.service_check_needed and not skip_service_check:
            self.service_check(self.SERVICE_CHECK_NAME, status, tags=tags, message=message)
            self.service_check_needed = False

        if status is AgentCheck.CRITICAL:
            raise CheckException(message)

    def _get_master_state(self, url, tags):
        # Mesos version >= 0.25
        endpoint = url + '/state'
        try:
            master_state = self._get_json(endpoint, failure_expected=True, tags=tags)
        except CheckException:
            # Mesos version < 0.25
            old_endpoint = endpoint + '.json'
            self.log.info(
                'Unable to fetch state from %s. Retrying with the deprecated endpoint: %s.', endpoint, old_endpoint
            )
            master_state = self._get_json(old_endpoint, tags=tags)
        return master_state

    def _get_master_stats(self, url, tags):
        if self.version >= [0, 22, 0]:
            endpoint = url + '/metrics/snapshot'
        else:
            endpoint = url + '/stats.json'
        return self._get_json(endpoint, tags=tags)

    def _get_master_roles(self, url, tags):
        if self.version >= [1, 8, 0]:
            endpoint = url + '/roles'
        else:
            endpoint = url + '/roles.json'
        return self._get_json(endpoint, tags=tags)

    def _check_leadership(self, url, tags=None):
        state_metrics = self._get_master_state(url, tags)
        self.leader = False

        if state_metrics is not None:
            self.version = [int(i) for i in state_metrics['version'].split('.')]
            self.set_metadata('version', state_metrics['version'])
            if state_metrics['leader'] == state_metrics['pid']:
                self.leader = True

        return state_metrics

    def check(self, instance):
        if 'url' not in instance:
            raise Exception('Mesos instance missing "url" value.')

        url = instance['url']
        instance_tags = instance.get('tags', [])
        if instance_tags is None:
            instance_tags = []

        state_metrics = self._check_leadership(url, instance_tags)
        if state_metrics:
            tags = ['mesos_pid:{0}'.format(state_metrics['pid']), 'mesos_node:master']
            if 'cluster' in state_metrics:
                tags.append('mesos_cluster:{0}'.format(state_metrics['cluster']))

            tags += instance_tags

            if self.leader:
                self.GAUGE('mesos.cluster.total_frameworks', len(state_metrics['frameworks']), tags=tags)

                for framework in state_metrics['frameworks']:
                    framework_tags = ['framework_name:' + framework['name']] + tags
                    self.GAUGE('mesos.framework.total_tasks', len(framework['tasks']), tags=framework_tags)
                    resources = framework['used_resources']
                    for key_name, (metric_name, metric_func) in iteritems(self.FRAMEWORK_METRICS):
                        metric_func(self, metric_name, resources[key_name], tags=framework_tags)

                role_metrics = self._get_master_roles(url, instance_tags)
                if role_metrics is not None:
                    for role in role_metrics['roles']:
                        role_tags = ['mesos_role:' + role['name']] + tags
                        self.GAUGE('mesos.role.frameworks.count', len(role['frameworks']), tags=role_tags)
                        self.GAUGE('mesos.role.weight', role['weight'], tags=role_tags)
                        for key_name, (metric_name, metric_func) in iteritems(self.ROLE_RESOURCES_METRICS):
                            try:
                                metric_func(self, metric_name, role['resources'][key_name], tags=role_tags)
                            except KeyError:
                                self.log.debug(
                                    'Unable to access metrics for master role resource: {}.  Skipping.', key_name
                                )

            stats_metrics = self._get_master_stats(url, instance_tags)
            if stats_metrics is not None:
                metrics = [self.SYSTEM_METRICS]
                if self.leader:
                    metrics += [
                        self.CLUSTER_TASKS_METRICS,
                        self.CLUSTER_SLAVES_METRICS,
                        self.CLUSTER_RESOURCES_METRICS,
                        self.CLUSTER_REGISTRAR_METRICS,
                        self.CLUSTER_FRAMEWORK_METRICS,
                        self.STATS_METRICS,
                    ]
                for m in metrics:
                    for key_name, (metric_name, metric_func) in iteritems(m):
                        if key_name in stats_metrics:
                            metric_func(self, metric_name, stats_metrics[key_name], tags=tags)

        self.service_check_needed = True
