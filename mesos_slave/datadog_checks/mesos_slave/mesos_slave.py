# (C) Datadog, Inc. 2015-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

"""Mesos Slave check

Collects metrics from mesos slave node.
"""

from requests.exceptions import Timeout
from six import iteritems
from six.moves.urllib.parse import urlparse

from datadog_checks.checks import AgentCheck
from datadog_checks.errors import CheckException

DEFAULT_MASTER_PORT = 5050


class MesosSlave(AgentCheck):
    GAUGE = AgentCheck.gauge
    MONOTONIC_COUNT = AgentCheck.monotonic_count
    SERVICE_CHECK_NAME = "mesos_slave.can_connect"
    service_check_needed = True
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
        self.tags = []

        url = self.instance.get('url', '')
        parsed_url = urlparse(url)
        if self.http.options['verify'] and parsed_url.scheme == 'https':
            self.log.warning('Skipping TLS cert validation for %s based on configuration.' % url)
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

    # def _get_json(self, url, failure_expected=False, tags=None):
    #     tags = tags + ["url:%s" % url] if tags else ["url:%s" % url]
    #     msg = None
    #     status = None
    #     timeout = self.http.options['timeout']
    #     response = None
    #
    #     try:
    #         response = self.http.get(url)
    #         if response.status_code != 200:
    #             status = AgentCheck.CRITICAL
    #             msg = "Got %s when hitting %s" % (response.status_code, url)
    #         else:
    #             status = AgentCheck.OK
    #             msg = "Mesos master instance detected at %s " % url
    #     except requests.exceptions.Timeout:
    #         # If there's a timeout
    #         msg = "%s seconds timeout when hitting %s" % (timeout, url)
    #         status = AgentCheck.CRITICAL
    #     except Exception as e:
    #         msg = str(e)
    #         status = AgentCheck.CRITICAL
    #     finally:
    #         self.log.debug('Request to url : {0}, timeout: {1}, message: {2}'.format(url, timeout, msg))
    #         self._send_service_check(url, status, failure_expected=failure_expected, tags=tags, message=msg)
    #
    #     if response is None:
    #         return None
    #
    #     if response.encoding is None:
    #         response.encoding = 'UTF8'
    #
    #     return response.json()

    # def _send_service_check(self, , tags=None):
    #     #     status = None
    #     #     if resp:
    #     #         if resp.status_code == 200:
    #     #             status = AgentCheck.OK
    #     #     else:
    #     #         status = AgentCheck.CRITICAL
    #     #
    #     #     if self.service_check_needed:
    #     #         self.service_check(self.SERVICE_CHECK_NAME, status, tags=tags)
    #     #         self.service_check_needed = False

    def _get_json(self, url):
        try:
            resp = self.http.get(url)
            resp.raise_for_status()
        except Exception as e:
            if e.__class__ == Timeout:
                self.warning(
                    "Timeout for {} seconds when connecting to URL: {}".format(self.http.options['timeout'], url)
                )
            self.warning("Couldn't connect to URL: {} with exception: {}".format(url, str(e)))
            # bubble up the exception
            raise CheckException

        self.log.debug("request to url {} returned: {}".format(url, resp))
        return resp.json()

    # def _get_state(self, url, tags):
    #     # Mesos version >= 0.25
    #     endpoint = url + '/state'
    #     try:
    #         master_state = self._get_json(endpoint)
    #     # if it failed with new endpoint, then catch exception here and try old endpoint
    #     except CheckException:
    #         # Mesos version < 0.25
    #         old_endpoint = endpoint + '.json'
    #         self.log.info(
    #             'Unable to fetch state from {0}. Retrying with the deprecated endpoint: {1}.'.format(
    #                 endpoint, old_endpoint
    #             )
    #         )
    #         master_state = self._get_json(old_endpoint)
    #     return master_state

    def _get_state_metrics(self, url):
        # Mesos version >= 0.25
        endpoint = url + '/state'
        try:
            state_metrics = self._get_json(endpoint)
        except CheckException:
            # Mesos version < 0.25
            old_endpoint = endpoint + '.json'
            self.log.info(
                'Unable to fetch state from {}, retrying with deprecated endpoint {}'.format(endpoint, old_endpoint)
            )
            state_metrics = self._get_json(old_endpoint)

        return state_metrics

    def _get_stats_metrics(self, url):
        endpoint = url + '/metrics/snapshot' if self.version >= [0, 22, 0] else url + '/stats.json'
        return self._get_json(endpoint)

    def _set_version(self, state_metrics):
        #TODO: something is wrong with the state_metrics object in testing as it doesn't contain version info so this endpoint fails 
        if 'version' in state_metrics:
            self.version = [int(i) for i in state_metrics['version'].split('.')]
            # TODO: also set metadata here

    def _set_cluster_name(self, url, master_port, state_metrics):
        if 'master_hostname' in state_metrics:
            master_url = '{0}://{1}:{2}'.format(urlparse(url).scheme, state_metrics['master_hostname'], master_port)
            master_state = self._get_state_metrics(master_url)
            if master_state:
                self.cluster_name = master_state.get('cluster')

    def _set_tags(self, state_metrics, instance_tags):
        self.tags = ['mesos_pid:{0}'.format(state_metrics['pid']), 'mesos_node:slave'] + instance_tags
        if self.cluster_name:
            self.tags.append('mesos_cluster:{0}'.format(self.cluster_name))

    # def _get_constant_attributes(self, url, master_port, tags):
    #     state_metrics = None
    #     parsed_url = urlparse(url)
    #     if self.cluster_name is None:
    #         state_metrics = self._get_state(url, tags)
    #         if state_metrics:
    #             self.version = [int(i) for i in state_metrics['version'].split('.')]
    #             if 'master_hostname' in state_metrics:
    #                 master_state = self._get_state(
    #                     '{0}://{1}:{2}'.format(parsed_url.scheme, state_metrics['master_hostname'], master_port), tags
    #                 )
    #                 if master_state is not None:
    #                     self.cluster_name = master_state.get('cluster')
    #
    #     return state_metrics

    def _process_tasks(self, tasks, state_metrics, tags):
        for task in tasks:
            for framework in state_metrics['frameworks']:
                for executor in framework['executors']:
                    for t in executor['tasks']:
                        if task.lower() in t['name'].lower() and t['slave_id'] == state_metrics['id']:
                            task_tags = ['task_name:' + t['name']] + tags
                            self.service_check(t['name'] + '.ok', self.TASK_STATUS[t['state']], tags=task_tags)
                            for key_name, (metric_name, metric_func) in iteritems(self.TASK_METRICS):
                                metric_func(self, metric_name, t['resources'][key_name], tags=task_tags)

    def _process_state_info(self, url, tasks, master_port, instance_tags):
        state_metrics = self._get_state_metrics(url)
        if state_metrics:
            self._set_cluster_name(url, master_port, state_metrics)
            self._set_version(state_metrics)
            self._set_tags(state_metrics, instance_tags)
            self._process_tasks(tasks, state_metrics, self.tags)

    def _process_stats_info(self, url):
        stats_metrics = self._get_stats_metrics(url)
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
                        metric_func(self, metric_name, stats_metrics[key_name], tags=self.tags)

    def check(self, instance):
        if 'url' not in instance:
            raise Exception('Mesos instance missing "url" value.')

        url = instance['url']
        instance_tags = instance.get('tags', [])
        tasks = instance.get('tasks', [])
        master_port = instance.get("master_port", DEFAULT_MASTER_PORT)

        try:
            self._process_state_info(url, tasks, master_port, instance_tags)
            self._process_stats_info(url)
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=self.tags)

        except Exception as e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self.tags, message=str(e))
            raise CheckException
