# (C) Datadog, Inc. 2015-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

"""Mesos Slave check

Collects metrics from mesos slave node.
"""

from requests.exceptions import Timeout
from six import iteritems
from six.moves.urllib.parse import urlparse

from datadog_checks.base import AgentCheck, ConfigurationError

DEFAULT_MASTER_PORT = 5050


class MesosSlave(AgentCheck):
    GAUGE = AgentCheck.gauge
    MONOTONIC_COUNT = AgentCheck.monotonic_count
    SERVICE_CHECK_NAME = "mesos_slave.can_connect"
    DEFAULT_TIMEOUT = 5

    TASK_STATUS = {
        'TASK_STARTING': AgentCheck.OK,
        'TASK_RUNNING': AgentCheck.OK,
        'TASK_FINISHED': AgentCheck.OK,
        'TASK_FAILED': AgentCheck.CRITICAL,
        'TASK_KILLED': AgentCheck.WARNING,
        'TASK_LOST': AgentCheck.CRITICAL,
        'TASK_STAGING': AgentCheck.OK,
        'TASK_ERROR': AgentCheck.CRITICAL,
    }

    TASK_METRICS = {
        'cpus': ('mesos.state.task.cpu', GAUGE),
        'mem': ('mesos.state.task.mem', GAUGE),
        'disk': ('mesos.state.task.disk', GAUGE),
    }

    SLAVE_TASKS_METRICS = {
        'slave/tasks_failed': ('mesos.slave.tasks_failed', MONOTONIC_COUNT),
        'slave/tasks_finished': ('mesos.slave.tasks_finished', MONOTONIC_COUNT),
        'slave/tasks_killed': ('mesos.slave.tasks_killed', MONOTONIC_COUNT),
        'slave/tasks_lost': ('mesos.slave.tasks_lost', MONOTONIC_COUNT),
        'slave/tasks_running': ('mesos.slave.tasks_running', GAUGE),
        'slave/tasks_staging': ('mesos.slave.tasks_staging', GAUGE),
        'slave/tasks_starting': ('mesos.slave.tasks_starting', GAUGE),
    }

    SYSTEM_METRICS = {
        'system/cpus_total': ('mesos.stats.system.cpus_total', GAUGE),
        'system/load_15min': ('mesos.stats.system.load_15min', GAUGE),
        'system/load_1min': ('mesos.stats.system.load_1min', GAUGE),
        'system/load_5min': ('mesos.stats.system.load_5min', GAUGE),
        'system/mem_free_bytes': ('mesos.stats.system.mem_free_bytes', GAUGE),
        'system/mem_total_bytes': ('mesos.stats.system.mem_total_bytes', GAUGE),
        'slave/registered': ('mesos.stats.registered', GAUGE),
        'slave/uptime_secs': ('mesos.stats.uptime_secs', GAUGE),
    }

    SLAVE_RESOURCE_METRICS = {
        'slave/cpus_percent': ('mesos.slave.cpus_percent', GAUGE),
        'slave/cpus_total': ('mesos.slave.cpus_total', GAUGE),
        'slave/cpus_used': ('mesos.slave.cpus_used', GAUGE),
        'slave/gpus_percent': ('mesos.slave.gpus_percent', GAUGE),  # >= 1.0.0
        'slave/gpus_total': ('mesos.slave.gpus_total', GAUGE),  # >= 1.0.0
        'slave/gpus_used': ('mesos.slave.gpus_used', GAUGE),  # >= 1.0.0
        'slave/disk_percent': ('mesos.slave.disk_percent', GAUGE),
        'slave/disk_total': ('mesos.slave.disk_total', GAUGE),
        'slave/disk_used': ('mesos.slave.disk_used', GAUGE),
        'slave/mem_percent': ('mesos.slave.mem_percent', GAUGE),
        'slave/mem_total': ('mesos.slave.mem_total', GAUGE),
        'slave/mem_used': ('mesos.slave.mem_used', GAUGE),
    }

    SLAVE_EXECUTORS_METRICS = {
        'slave/executors_registering': ('mesos.slave.executors_registering', GAUGE),
        'slave/executors_running': ('mesos.slave.executors_running', GAUGE),
        'slave/executors_terminated': ('mesos.slave.executors_terminated', GAUGE),
        'slave/executors_terminating': ('mesos.slave.executors_terminating', GAUGE),
    }

    STATS_METRICS = {
        'slave/frameworks_active': ('mesos.slave.frameworks_active', GAUGE),
        'slave/invalid_framework_messages': ('mesos.slave.invalid_framework_messages', GAUGE),
        'slave/invalid_status_updates': ('mesos.slave.invalid_status_updates', GAUGE),
        'slave/recovery_errors': ('mesos.slave.recovery_errors', GAUGE),
        'slave/valid_framework_messages': ('mesos.slave.valid_framework_messages', GAUGE),
        'slave/valid_status_updates': ('mesos.slave.valid_status_updates', GAUGE),
    }

    HTTP_CONFIG_REMAPPER = {'disable_ssl_validation': {'name': 'tls_verify', 'invert': True, 'default': False}}

    def __init__(self, name, init_config, instances):
        super(MesosSlave, self).__init__(name, init_config, instances)
        self.cluster_name = None
        self.version = []

        url = self.instance.get('url', '')
        parsed_url = urlparse(url)
        if self.http.options['verify'] and parsed_url.scheme == 'https':
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

    def check(self, _):
        if 'url' not in self.instance:
            raise ConfigurationError('Mesos instance missing "url" value.')

        url = self.instance['url']
        tags = list(self.instance.get('tags', []))
        tasks = self.instance.get('tasks', [])
        master_port = self.instance.get("master_port", DEFAULT_MASTER_PORT)

        self._process_state_info(url, tasks, master_port, tags)
        self._process_stats_info(url, tags)

    def _process_state_info(self, url, tasks, master_port, tags):
        state_tags = list(tags)
        try:
            state_metrics = self._get_state_metrics(url, state_tags)
            if state_metrics:
                if 'pid' in state_metrics:
                    add_tags = ['mesos_pid:{}'.format(state_metrics['pid']), 'mesos_node:slave']
                    # Modify the global tags
                    tags.extend(add_tags)
                    state_tags.extend(add_tags)
                self._set_version(state_metrics)
                self._set_cluster_name(url, master_port, state_metrics, state_tags)
                self._process_tasks(tasks, state_metrics, state_tags)

                self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=state_tags)
        except Exception:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=state_tags)
            raise

    def _process_stats_info(self, url, tags):
        stats_tags = list(tags)
        try:
            stats_metrics = self._get_stats_metrics(url, stats_tags)
            if stats_metrics:
                metrics = [
                    self.SLAVE_TASKS_METRICS,
                    self.SYSTEM_METRICS,
                    self.SLAVE_RESOURCE_METRICS,
                    self.SLAVE_EXECUTORS_METRICS,
                    self.STATS_METRICS,
                ]
                for m in metrics:
                    for key_name, (metric_name, metric_func) in iteritems(m):
                        if key_name in stats_metrics:
                            metric_func(self, metric_name, stats_metrics[key_name], tags=stats_tags)
                self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=stats_tags)
        except Exception:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=stats_tags)
            raise

    def _get_state_metrics(self, url, tags):
        # Mesos version >= 0.25
        endpoint = url + '/state'
        try:
            state_metrics = self._get_json(endpoint)
            tags.append("url:{}".format(endpoint))
        except Exception:
            # Mesos version < 0.25
            old_endpoint = endpoint + '.json'
            tags.append("url:{}".format(old_endpoint))
            self.log.info('Unable to fetch state from %s, retrying with deprecated endpoint %s', endpoint, old_endpoint)
            state_metrics = self._get_json(old_endpoint)
        return state_metrics

    def _get_stats_metrics(self, url, tags):
        endpoint = url + '/metrics/snapshot' if self.version >= [0, 22, 0] else url + '/stats.json'
        tags.append("url:{}".format(endpoint))
        return self._get_json(endpoint)

    def _get_json(self, url):
        try:
            resp = self.http.get(url)
            resp.raise_for_status()
        except Timeout:
            self.warning("Timeout for %s seconds when connecting to URL: %s", self.http.options['timeout'], url)
            raise
        except Exception as e:
            self.warning("Couldn't connect to URL: %s with exception: %s", url, e)
            raise

        self.log.debug("Request to url %s returned: %s", url, resp)
        return resp.json()

    def _set_version(self, state_metrics):
        if 'version' in state_metrics:
            version = state_metrics['version']
            self.version = [int(i) for i in version.split('.')]
            self.set_metadata('version', version)

    def _set_cluster_name(self, url, master_port, state_metrics, tags):
        if 'master_hostname' in state_metrics:
            master_url = '{}://{}:{}'.format(urlparse(url).scheme, state_metrics['master_hostname'], master_port)
            master_state = self._get_state_metrics(master_url, [])
            if master_state:
                self.cluster_name = master_state.get('cluster')
                if self.cluster_name:
                    tags.append('mesos_cluster:{}'.format(self.cluster_name))

    def _process_tasks(self, tasks, state_metrics, tags):
        for task in tasks:
            for framework in state_metrics['frameworks']:
                for executor in framework['executors']:
                    for t in executor['tasks']:
                        if task.lower() in t['name'].lower() and t['slave_id'] == state_metrics['id']:
                            task_tags = ['task_name:' + t['name']]
                            task_tags.extend(tags)
                            self.service_check(t['name'] + '.ok', self.TASK_STATUS[t['state']], tags=task_tags)
                            for key_name, (metric_name, metric_func) in iteritems(self.TASK_METRICS):
                                metric_func(self, metric_name, t['resources'][key_name], tags=task_tags)
