# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import division

import requests
from six import iteritems

from datadog_checks.base.checks import AgentCheck
from datadog_checks.base.utils.common import round_value

try:
    from tagger import get_tags
except ImportError:
    import logging

    log = logging.getLogger(__name__)
    log.warning('This check is only supported on Agent 6')

    def get_tags(name, card):
        return []


# Fargate related constants
EVENT_TYPE = SOURCE_TYPE_NAME = 'ecs.fargate'
API_ENDPOINT = 'http://169.254.170.2/v2'
METADATA_ROUTE = '/metadata'
STATS_ROUTE = '/stats'
DEFAULT_TIMEOUT = 5

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
IO_METRICS = {'io_service_bytes_recursive': 'ecs.fargate.io.bytes.', 'io_serviced_recursive': 'ecs.fargate.io.ops.'}


class FargateCheck(AgentCheck):

    HTTP_CONFIG_REMAPPER = {'timeout': {'name': 'timeout', 'default': DEFAULT_TIMEOUT}}

    def check(self, instance):
        metadata_endpoint = API_ENDPOINT + METADATA_ROUTE
        stats_endpoint = API_ENDPOINT + STATS_ROUTE
        custom_tags = instance.get('tags', [])

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

        metadata = {}
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

        container_tags = {}
        for container in metadata['Containers']:
            c_id = container['DockerId']
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
            self.submit_perf_metrics(instance, container_tags, container_id, container_stats)

        self.service_check('fargate_check', AgentCheck.OK, tags=custom_tags)

    def submit_perf_metrics(self, instance, container_tags, container_id, container_stats):
        try:
            if container_stats is None:
                self.log.debug("Empty stats for container %s", container_id)
                return

            tags = container_tags[container_id]

            # CPU metrics
            cpu_stats = container_stats.get('cpu_stats', {})
            prev_cpu_stats = container_stats.get('precpu_stats', {})

            value_system = cpu_stats.get('system_cpu_usage')
            if value_system is not None:
                self.gauge('ecs.fargate.cpu.system', value_system, tags)

            value_total = cpu_stats.get('cpu_usage', {}).get('total_usage')
            if value_total is not None:
                self.gauge('ecs.fargate.cpu.user', value_total, tags)

            prevalue_total = prev_cpu_stats.get('cpu_usage', {}).get('total_usage')
            prevalue_system = prev_cpu_stats.get('system_cpu_usage')

            if prevalue_system is not None and prevalue_total is not None:
                cpu_delta = float(value_total) - float(prevalue_total)
                system_delta = float(value_system) - float(prevalue_system)
            else:
                cpu_delta = 0.0
                system_delta = 0.0

            active_cpus = float(cpu_stats.get('online_cpus', 0.0))

            cpu_percent = 0.0
            if system_delta > 0 and cpu_delta > 0 and active_cpus > 0:
                cpu_percent = (cpu_delta / system_delta) * active_cpus * 100.0
                cpu_percent = round_value(cpu_percent, 2)
                self.gauge('ecs.fargate.cpu.percent', cpu_percent, tags)

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
            if value is not None:
                self.gauge('ecs.fargate.mem.limit', value, tags)

            # I/O metrics
            for blkio_cat, metric_name in iteritems(IO_METRICS):
                read_counter = write_counter = 0
                for blkio_stat in container_stats.get("blkio_stats", {}).get(blkio_cat, []):
                    if blkio_stat["op"] == "Read" and "value" in blkio_stat:
                        read_counter += blkio_stat["value"]
                    elif blkio_stat["op"] == "Write" and "value" in blkio_stat:
                        write_counter += blkio_stat["value"]
                self.rate(metric_name + 'read', read_counter, tags)
                self.rate(metric_name + 'write', write_counter, tags)

        except Exception as e:
            self.warning("Cannot retrieve metrics for %s: %s", container_id, e)
