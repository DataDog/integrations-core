# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# 3rd party
import requests

# project
from checks import AgentCheck

# Fargate related constants
EVENT_TYPE = SOURCE_TYPE_NAME = 'ecs.fargate'
API_ENDPOINT = 'http://169.254.170.2/v2'
METADATA_ROUTE = '/metadata'
STATS_ROUTE = '/stats'
DEFAULT_TIMEOUT = 5

# Default value is maxed out for some cgroup metrics
CGROUP_NO_VALUE = 0x7ffffffffffff000

# Do not collect these labels are we already have the info as tags
LABEL_BLACKLIST = ["com.amazonaws.ecs.cluster", "com.amazonaws.ecs.container-name", "com.amazonaws.ecs.task-arn",
                   "com.amazonaws.ecs.task-definition-family", "com.amazonaws.ecs.task-definition-version",
                   "com.datadoghq.ad.check_names", "com.datadoghq.ad.init_configs", "com.datadoghq.ad.instances"]

# Metrics constants
MEMORY_GAUGE_METRICS = ['cache','mapped_file','rss','hierarchical_memory_limit','active_anon',
                        'active_file','inactive_file','hierarchical_memsw_limit']
MEMORY_RATE_METRICS = ['pgpgin', 'pgpgout', 'pgmajfault','pgfault']
IO_METRICS = {'io_service_bytes_recursive':'ecs.fargate.io.bytes.', 'io_serviced_recursive':'ecs.fargate.io.ops.'}

class FargateCheck(AgentCheck):

    def check(self, instance):
        timeout = float(instance.get('timeout', DEFAULT_TIMEOUT))
        metadata_endpoint = API_ENDPOINT + METADATA_ROUTE
        stats_endpoint = API_ENDPOINT + STATS_ROUTE

        try:
            request = requests.get(metadata_endpoint, timeout=timeout)
        except requests.exceptions.Timeout:
            msg = 'Fargate {} endpoint timed out after {} seconds'.format(metadata_endpoint, timeout)
            self.service_check('fargate_check', AgentCheck.CRITICAL, message=msg)
            self.log.exception(msg)
            return
        except requests.exceptions.RequestException:
            msg = 'Error fetching Fargate {} endpoint'.format(metadata_endpoint)
            self.service_check('fargate_check', AgentCheck.CRITICAL, message=msg)
            self.log.exception(msg)
            return

        if request.status_code != 200:
            msg = 'Fargate {} endpoint responded with {} HTTP code'.format(metadata_endpoint, request.status_code)
            self.service_check('fargate_check', AgentCheck.CRITICAL, message=msg)
            self.log.warning(msg)
            return

        metadata = {}
        try:
            metadata = request.json()
        except ValueError:
            msg = 'Cannot decode Fargate {} endpoint response'.format(metadata_endpoint)
            self.service_check('fargate_check', AgentCheck.WARNING, message=msg)
            self.log.warning(msg, exc_info=True)
            return

        if not all(k in metadata for k in ["Cluster","Containers"]):
            msg = 'Missing critical metadata in {} endpoint response'.format(metadata_endpoint)
            self.service_check('fargate_check', AgentCheck.WARNING, message=msg)
            self.log.warning(msg)
            return

        common_tags = instance.get('tags', [])
        common_tags.append('ecs_cluster:' + metadata['Cluster'])
        common_tags.append('ecs_task_family:' + metadata['Family'])
        common_tags.append('ecs_task_version:' + metadata['Version'])
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

            if container['Limits']['CPU'] > 0:
                self.gauge('ecs.fargate.cpu.limit', container['Limits']['CPU'], container_tags[c_id])

        try:
            request = requests.get(stats_endpoint, timeout=timeout)
        except requests.exceptions.Timeout:
            msg = 'Fargate {} endpoint timed out after {} seconds'.format(stats_endpoint, timeout)
            self.service_check('fargate_check', AgentCheck.WARNING, message=msg)
            self.log.warning(msg, exc_info=True)
            return
        except requests.exceptions.RequestException:
            msg = 'Error fetching Fargate {} endpoint'.format(stats_endpoint)
            self.service_check('fargate_check', AgentCheck.WARNING, message=msg)
            self.log.warning(msg, exc_info=True)
            return

        if request.status_code != 200:
            msg = 'Fargate {} endpoint responded with {} HTTP code'.format(stats_endpoint, request.status_code)
            self.service_check('fargate_check', AgentCheck.WARNING, message=msg)
            self.log.warning(msg)
            return

        stats = {}
        try:
            stats = request.json()
        except ValueError:
            msg = 'Cannot decode Fargate {} endpoint response'.format(stats_endpoint)
            self.service_check('fargate_check', AgentCheck.WARNING, message=msg)
            self.log.warning(msg, exc_info=True)

        for container_id, container_stats in stats.iteritems():
            # CPU metrics
            tags = container_tags[container_id]
            self.rate('ecs.fargate.cpu.system', container_stats['cpu_stats']['system_cpu_usage'], tags)
            self.rate('ecs.fargate.cpu.user', container_stats['cpu_stats']['cpu_usage']['total_usage'], tags)
            # Memory metrics
            for metric in MEMORY_GAUGE_METRICS:
                value = container_stats['memory_stats']['stats'][metric]
                if value < CGROUP_NO_VALUE:
                    self.gauge('ecs.fargate.mem.' + metric, value, tags)
            for metric in MEMORY_RATE_METRICS:
                value = container_stats['memory_stats']['stats'][metric]
                self.rate('ecs.fargate.mem.' + metric, value, tags)
            self.gauge('ecs.fargate.mem.max_usage', container_stats['memory_stats']['max_usage'], tags)
            self.gauge('ecs.fargate.mem.usage', container_stats['memory_stats']['usage'], tags)
            self.gauge('ecs.fargate.mem.limit', container_stats['memory_stats']['limit'], tags)
            # I/O metrics
            for blkio_cat, metric_name in IO_METRICS.iteritems():
                read_counter = write_counter = 0
                for blkio_stat in container_stats["blkio_stats"][blkio_cat]:
                    if blkio_stat["op"] == "Read" and "value" in blkio_stat:
                        read_counter += blkio_stat["value"]
                    elif blkio_stat["op"] == "Write" and "value" in blkio_stat:
                        write_counter += blkio_stat["value"]
                self.rate(metric_name + 'read', read_counter, tags)
                self.rate(metric_name + 'write', write_counter, tags)

        self.service_check('fargate_check', AgentCheck.OK)
