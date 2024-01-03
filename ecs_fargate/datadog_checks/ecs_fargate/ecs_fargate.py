# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import division

import os

import requests
from dateutil import parser
from six import iteritems

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.common import round_value

try:
    from tagger import get_tags
except ImportError:
    import logging

    log = logging.getLogger(__name__)
    log.warning('This check is only supported on Agent 6')

    def get_tags(name, card):
        return []


try:
    from containers import is_excluded as c_is_excluded
except ImportError:
    # Don't fail on < 6.2
    import logging

    log = logging.getLogger(__name__)
    log.info('Agent does not provide filtering logic, disabling container filtering')

    def c_is_excluded(name, image, namespace=""):
        return False


# Fargate related constants
EVENT_TYPE = SOURCE_TYPE_NAME = 'ecs.fargate'
DEFAULT_TIMEOUT = 5

# Fargate ECS Endpoint v2
API_ENDPOINT_V2 = 'http://169.254.170.2/v2'
METADATA_ROUTE_V2 = '/metadata'
STATS_ROUTE_V2 = '/stats'

# Fargate ECS Endpoint v4
API_ENDPOINT_V4_ENV_VAR = 'ECS_CONTAINER_METADATA_URI_V4'
METADATA_ROUTE_V4 = '/task'
STATS_ROUTE_V4 = '/task/stats'

# Default value is maxed out for some cgroup metrics
CGROUP_NO_VALUE = 0x7FFFFFFFFFFFF000

# Metrics constants
MEMORY_GAUGE_METRICS = [
    'cache',
    'mapped_file',
    'rss',
    'hierarchical_memory_limit',
    'active_anon',
    'active_file',
    'inactive_file',
    'hierarchical_memsw_limit',
]
MEMORY_RATE_METRICS = ['pgpgin', 'pgpgout', 'pgmajfault', 'pgfault']
# Linux-only IO metrics
IO_METRICS = {'io_service_bytes_recursive': 'ecs.fargate.io.bytes.', 'io_serviced_recursive': 'ecs.fargate.io.ops.'}
# Windows-only IO metrics
STORAGE_STATS_METRICS = {
    'read_count_normalized': 'ecs.fargate.io.ops.read',
    'read_size_bytes': 'ecs.fargate.io.bytes.read',
    'write_count_normalized': 'ecs.fargate.io.ops.write',
    'write_size_bytes': 'ecs.fargate.io.bytes.write',
}
NETWORK_GAUGE_METRICS = {
    'rx_errors': 'ecs.fargate.net.rcvd_errors',
    'tx_errors': 'ecs.fargate.net.sent_errors',
    'rx_dropped': 'ecs.fargate.net.packet.in_dropped',
    'tx_dropped': 'ecs.fargate.net.packet.out_dropped',
}
NETWORK_RATE_METRICS = {'rx_bytes': 'ecs.fargate.net.bytes_rcvd', 'tx_bytes': 'ecs.fargate.net.bytes_sent'}
TASK_TAGGER_ENTITY_ID = "internal://global-entity-id"

EPHEMERAL_STORAGE_GAUGE_METRICS = {
    'Utilized': 'ecs.fargate.ephemeral_storage.utilized',
    'Reserved': 'ecs.fargate.ephemeral_storage.reserved',
}


class FargateCheck(AgentCheck):

    HTTP_CONFIG_REMAPPER = {'timeout': {'name': 'timeout', 'default': DEFAULT_TIMEOUT}}

    def __init__(self, name, init_config, instances):
        # Fargate metadata endpoint https://docs.aws.amazon.com/AmazonECS/latest/userguide/task-metadata-endpoint-v4-fargate.html
        self.API_ENDPOINT = os.environ.get(API_ENDPOINT_V4_ENV_VAR)

        if self.API_ENDPOINT is None:
            # If v4 endpoint is not available, fall back to v2
            self.API_ENDPOINT = API_ENDPOINT_V2
            self.METADATA_ROUTE = METADATA_ROUTE_V2
            self.STATS_ROUTE = STATS_ROUTE_V2
        else:
            # Otherwise set v4 routes
            self.METADATA_ROUTE = METADATA_ROUTE_V4
            self.STATS_ROUTE = STATS_ROUTE_V4

        super(FargateCheck, self).__init__(name, init_config, instances)

    def check(self, _):
        metadata_endpoint = self.API_ENDPOINT + self.METADATA_ROUTE
        stats_endpoint = self.API_ENDPOINT + self.STATS_ROUTE

        custom_tags = self.instance.get('tags', [])

        try:
            request = self.http.get(metadata_endpoint)
        except requests.exceptions.Timeout:
            msg = 'Fargate {} endpoint timed out after {} seconds'.format(
                metadata_endpoint, self.http.options['timeout']
            )
            self.service_check('fargate_check', AgentCheck.CRITICAL, message=msg, tags=custom_tags)
            self.log.exception(msg)
            return
        except requests.exceptions.RequestException:
            msg = 'Error fetching Fargate {} endpoint'.format(metadata_endpoint)
            self.service_check('fargate_check', AgentCheck.CRITICAL, message=msg, tags=custom_tags)
            self.log.exception(msg)
            return

        if request.status_code != 200:
            msg = 'Fargate {} endpoint responded with {} HTTP code'.format(metadata_endpoint, request.status_code)
            self.service_check('fargate_check', AgentCheck.CRITICAL, message=msg, tags=custom_tags)
            self.log.warning(msg)
            return

        try:
            metadata = request.json()
        except ValueError:
            msg = 'Cannot decode Fargate {} endpoint response'.format(metadata_endpoint)
            self.service_check('fargate_check', AgentCheck.WARNING, message=msg, tags=custom_tags)
            self.log.warning(msg, exc_info=True)
            return

        if not all(k in metadata for k in ['Cluster', 'Containers']):
            msg = 'Missing critical metadata in {} endpoint response'.format(metadata_endpoint)
            self.service_check('fargate_check', AgentCheck.WARNING, message=msg, tags=custom_tags)
            self.log.warning(msg)
            return

        exlcuded_cid = set()
        container_tags = {}
        for container in metadata['Containers']:
            c_id = container['DockerId']
            # Check if container is excluded
            if c_is_excluded(container.get("Name", ""), container.get("Image", "")):
                exlcuded_cid.add(c_id)
                continue

            tagger_tags = get_tags('container_id://%s' % c_id, True) or []

            # Compatibility with previous versions of the check
            compat_tags = []
            for tag in tagger_tags:
                if tag.startswith(("task_family:", "task_version:")):
                    compat_tags.append("ecs_" + tag)
                elif tag.startswith("cluster_name:"):
                    compat_tags.append(tag.replace("cluster_name:", "ecs_cluster:"))
                elif tag.startswith("container_name:"):
                    compat_tags.append(tag.replace("container_name:", "docker_name:"))

            container_tags[c_id] = tagger_tags + compat_tags + custom_tags

            if container.get('Limits', {}).get('CPU', 0) > 0:
                self.gauge('ecs.fargate.cpu.limit', container['Limits']['CPU'], container_tags[c_id])

        # Create task tags
        task_tags = get_tags(TASK_TAGGER_ENTITY_ID, True) or []
        # Compatibility with previous versions of the check
        compat_tags = []
        for tag in task_tags:
            if tag.startswith(("task_family:", "task_version:")):
                compat_tags.append("ecs_" + tag)
            elif tag.startswith("cluster_name:"):
                compat_tags.append(tag.replace("cluster_name:", "ecs_cluster:"))

        task_tags = task_tags + compat_tags + custom_tags

        ## Ephemeral Storage Metrics
        if 'EphemeralStorageMetrics' in metadata:
            es_metrics = metadata['EphemeralStorageMetrics']
            for field_name, metric_value in iteritems(es_metrics):
                metric_name = EPHEMERAL_STORAGE_GAUGE_METRICS.get(field_name)
                self.gauge(metric_name, metric_value, task_tags)

        if metadata.get('Limits', {}).get('CPU', 0) > 0:
            self.gauge('ecs.fargate.cpu.task.limit', metadata['Limits']['CPU'] * 10**9, task_tags)

        if metadata.get('Limits', {}).get('Memory', 0) > 0:
            self.gauge('ecs.fargate.mem.task.limit', metadata['Limits']['Memory'] * 1024**2, task_tags)

        try:
            request = self.http.get(stats_endpoint)
        except requests.exceptions.Timeout:
            msg = 'Fargate {} endpoint timed out after {} seconds'.format(stats_endpoint, self.http.options['timeout'])
            self.service_check('fargate_check', AgentCheck.WARNING, message=msg, tags=custom_tags)
            self.log.warning(msg, exc_info=True)
            return
        except requests.exceptions.RequestException:
            msg = 'Error fetching Fargate {} endpoint'.format(stats_endpoint)
            self.service_check('fargate_check', AgentCheck.WARNING, message=msg, tags=custom_tags)
            self.log.warning(msg, exc_info=True)
            return

        if request.status_code != 200:
            msg = 'Fargate {} endpoint responded with {} HTTP code'.format(stats_endpoint, request.status_code)
            self.service_check('fargate_check', AgentCheck.WARNING, message=msg, tags=custom_tags)
            self.log.warning(msg)
            return

        stats = {}
        try:
            stats = request.json()
        except ValueError:
            msg = 'Cannot decode Fargate {} endpoint response'.format(stats_endpoint)
            self.service_check('fargate_check', AgentCheck.WARNING, message=msg, tags=custom_tags)
            self.log.warning(msg, exc_info=True)

        for container_id, container_stats in iteritems(stats):
            if container_id not in exlcuded_cid:
                self.submit_perf_metrics(container_tags, container_id, container_stats)

        self.service_check('fargate_check', AgentCheck.OK, tags=custom_tags)

    def submit_perf_metrics(self, container_tags, container_id, container_stats):
        try:
            if container_stats is None:
                self.log.debug("Empty stats for container %s", container_id)
                return

            tags = container_tags[container_id]

            # CPU metrics
            cpu_stats = container_stats.get('cpu_stats', {})
            prev_cpu_stats = container_stats.get('precpu_stats', {})

            value_system = cpu_stats.get('cpu_usage', {}).get('usage_in_kernelmode')
            if value_system is not None:
                self.rate('ecs.fargate.cpu.system', value_system, tags)

            value_user = cpu_stats.get('cpu_usage', {}).get('usage_in_usermode')
            if value_user is not None:
                self.rate('ecs.fargate.cpu.user', value_user, tags)

            value_total = cpu_stats.get('cpu_usage', {}).get('total_usage')
            if value_total is not None:
                self.rate('ecs.fargate.cpu.usage', value_total, tags)

            available_cpu = cpu_stats.get('system_cpu_usage')
            preavailable_cpu = prev_cpu_stats.get('system_cpu_usage')
            prevalue_total = prev_cpu_stats.get('cpu_usage', {}).get('total_usage')

            # This is always false on Windows because the available cpu is not exposed
            if (
                available_cpu is not None
                and preavailable_cpu is not None
                and value_total is not None
                and prevalue_total is not None
            ):
                cpu_delta = float(value_total) - float(prevalue_total)
                system_delta = float(available_cpu) - float(preavailable_cpu)
            else:
                cpu_delta = 0.0
                system_delta = 0.0

            # Not reported on Windows
            active_cpus = float(cpu_stats.get('online_cpus', 0.0))

            cpu_percent = 0.0
            if system_delta > 0 and cpu_delta > 0 and active_cpus > 0:
                if system_delta > cpu_delta:
                    cpu_percent = (cpu_delta / system_delta) * active_cpus * 100.0
                    cpu_percent = round_value(cpu_percent, 2)
                    self.gauge('ecs.fargate.cpu.percent', cpu_percent, tags)
                else:
                    # There is a bug where container CPU usage is occasionally reported as greater than system
                    # CPU usage (which, in fact, represents the maximum available CPU time during this timeframe),
                    # leading to a non-sensical CPU percentage to be reported. To mitigate this we substitute the
                    # system_delta with (t1 - t0)*active_cpus (with a scale factor to convert to nanoseconds)

                    self.log.debug(
                        "Anomalous CPU value for container_id: %s. cpu_percent: %f",
                        container_id,
                        cpu_percent,
                    )
                    self.log.debug("ECS container_stats for container_id %s: %s", container_id, container_stats)

                    # example format: '2021-09-22T04:55:52.490012924Z',
                    t1 = container_stats.get('read', '')
                    t0 = container_stats.get('preread', '')
                    try:
                        t_delta = int((parser.isoparse(t1) - parser.isoparse(t0)).total_seconds())
                        # Simplified formula for cpu_percent where system_delta = t_delta * active_cpus * (10 ** 9)
                        cpu_percent = (cpu_delta / (t_delta * (10**9))) * 100.0
                        cpu_percent = round_value(cpu_percent, 2)
                        self.gauge('ecs.fargate.cpu.percent', cpu_percent, tags)
                    except ValueError:
                        pass

            # Memory metrics
            memory_stats = container_stats.get('memory_stats', {})

            for metric in MEMORY_GAUGE_METRICS:
                value = memory_stats.get('stats', {}).get(metric)
                if value is not None and value < CGROUP_NO_VALUE:
                    self.gauge('ecs.fargate.mem.' + metric, value, tags)
            for metric in MEMORY_RATE_METRICS:
                value = memory_stats.get('stats', {}).get(metric)
                if value is not None:
                    self.rate('ecs.fargate.mem.' + metric, value, tags)

            value = memory_stats.get('max_usage')
            if value is not None:
                self.gauge('ecs.fargate.mem.max_usage', value, tags)

            value = memory_stats.get('usage')
            if value is not None:
                self.gauge('ecs.fargate.mem.usage', value, tags)

            value = memory_stats.get('limit')
            # When there is no hard-limit defined, the ECS API returns that value of 8 EiB
            # It's not exactly 2^63, but a rounded value of it most probably because of a int->float->int conversion
            if value is not None and value != 9223372036854771712:
                self.gauge('ecs.fargate.mem.limit', value, tags)

            # I/O metrics
            for blkio_cat, metric_name in iteritems(IO_METRICS):
                read_counter = write_counter = 0

                blkio_stats = container_stats.get("blkio_stats", {}).get(blkio_cat)
                # In Windows is always "None" (string), so don't report anything
                if blkio_stats is None or blkio_stats == 'None':
                    continue

                for blkio_stat in blkio_stats:

                    if blkio_stat["op"] == "Read" and "value" in blkio_stat:
                        read_counter += blkio_stat["value"]
                    elif blkio_stat["op"] == "Write" and "value" in blkio_stat:
                        write_counter += blkio_stat["value"]
                self.rate(metric_name + 'read', read_counter, tags)
                self.rate(metric_name + 'write', write_counter, tags)

            # Windows I/O metrics
            storage_stats = container_stats.get('storage_stats', {})
            for metric, metric_name in STORAGE_STATS_METRICS.items():
                value = storage_stats.get(metric)
                if value:
                    self.rate(metric_name, value, tags)

            # Network metrics
            networks = container_stats.get('networks', {})
            for network_interface, network_stats in iteritems(networks):
                network_tags = tags + ["interface:{}".format(network_interface)]
                for field_name, metric_name in iteritems(NETWORK_GAUGE_METRICS):
                    metric_value = network_stats.get(field_name)
                    if metric_value is not None:
                        self.gauge(metric_name, metric_value, network_tags)
                for field_name, metric_name in iteritems(NETWORK_RATE_METRICS):
                    metric_value = network_stats.get(field_name)
                    if metric_value is not None:
                        self.rate(metric_name, metric_value, network_tags)

        except Exception as e:
            self.warning("Cannot retrieve metrics for %s: %s", container_id, e)
