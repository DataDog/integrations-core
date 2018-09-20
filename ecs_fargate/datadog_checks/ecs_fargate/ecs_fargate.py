# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import requests
from six import iteritems

from datadog_checks.checks import AgentCheck

# Fargate related constants
EVENT_TYPE = SOURCE_TYPE_NAME = 'ecs.fargate'
API_ENDPOINT = 'http://169.254.170.2/v2'
METADATA_ROUTE = '/metadata'
STATS_ROUTE = '/stats'
DEFAULT_TIMEOUT = 5

# Default value is maxed out for some cgroup metrics
CGROUP_NO_VALUE = 0x7ffffffffffff000

# Do not collect these labels are we already have the info as tags
LABEL_BLACKLIST = ['com.amazonaws.ecs.cluster', 'com.amazonaws.ecs.container-name', 'com.amazonaws.ecs.task-arn',
                   'com.amazonaws.ecs.task-definition-family', 'com.amazonaws.ecs.task-definition-version',
                   'com.datadoghq.ad.check_names', 'com.datadoghq.ad.init_configs', 'com.datadoghq.ad.instances']

# Metrics constants
MEMORY_GAUGE_METRICS = ['cache', 'mapped_file', 'rss', 'hierarchical_memory_limit', 'active_anon',
                        'active_file', 'inactive_file', 'hierarchical_memsw_limit']
MEMORY_RATE_METRICS = ['pgpgin', 'pgpgout', 'pgmajfault', 'pgfault']
IO_METRICS = {
    'io_service_bytes_recursive': 'ecs.fargate.io.bytes.',
    'io_serviced_recursive': 'ecs.fargate.io.ops.'
}


class FargateCheck(AgentCheck):

    def check(self, instance):
        timeout = float(instance.get('timeout', DEFAULT_TIMEOUT))
        metadata_endpoint = API_ENDPOINT + METADATA_ROUTE
        stats_endpoint = API_ENDPOINT + STATS_ROUTE
        custom_tags = instance.get('tags', [])

        try:
            request = requests.get(metadata_endpoint, timeout=timeout)
        except requests.exceptions.Timeout:
            msg = 'Fargate {} endpoint timed out after {} seconds'.format(metadata_endpoint, timeout)
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

        common_tags = [
            'ecs_cluster:' + metadata['Cluster'],
            'ecs_task_family:' + metadata['Family'],
            'ecs_task_version:' + metadata['Revision']
        ]
        common_tags.extend(custom_tags)
        label_whitelist = instance.get('label_whitelist', [])

        container_tags = {}
        for container in metadata['Containers']:
            c_id = container['DockerId']
            container_tags[c_id] = []
            container_tags[c_id].extend(common_tags)
            container_tags[c_id].append('docker_name:' + container['DockerName'])
            container_tags[c_id].append('docker_image:' + container['Image'])
            image_split = container['Image'].split(':')
            container_tags[c_id].append('image_name:' + ':'.join(image_split[:-1]))
            container_tags[c_id].append('image_tag:' + image_split[-1])
            for label, value in container["Labels"].iteritems():
                if label in label_whitelist or label not in LABEL_BLACKLIST:
                    container_tags[c_id].append(label + ':' + value)

            if container.get('Limits', {}).get('CPU', 0) > 0:
                self.gauge('ecs.fargate.cpu.limit', container['Limits']['CPU'], container_tags[c_id])

        try:
            request = requests.get(stats_endpoint, timeout=timeout)
        except requests.exceptions.Timeout:
            msg = 'Fargate {} endpoint timed out after {} seconds'.format(stats_endpoint, timeout)
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

        for container_id, container_stats in stats.iteritems():
            if container_stats is None:
                self.log.debug("Could not collect stats from {}".format(container_id))
                continue

            tags = container_tags[container_id]

            # CPU metrics
            cpu_stats = container_stats.get('cpu_stats', {})
            prev_cpu_stats = container_stats.get('precpu_stats', {})

            value_system = cpu_stats.get('system_cpu_usage')
            if value_system is not None:
                self.rate('ecs.fargate.cpu.system', value_system, tags)

            value_total = cpu_stats.get('cpu_usage', {}).get('total_usage')
            if value_total is not None:
                self.rate('ecs.fargate.cpu.user', value_total, tags)

            prevalue_total = prev_cpu_stats.get('cpu_usage', {}).get('total_usage')
            prevalue_system = prev_cpu_stats.get('system_cpu_usage')

            if prevalue_system is not None and prevalue_total is not None:
                cpu_delta = float(value_total) - float(prevalue_total)
                system_delta = float(value_system) - float(prevalue_system)

            active_cpus = float(cpu_stats['online_cpus'])

            cpu_percent = 0.0
            if system_delta > 0 and cpu_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * active_cpus * 100.0
                cpu_percent = round(cpu_percent, 2)
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

        self.service_check('fargate_check', AgentCheck.OK, tags=custom_tags)
