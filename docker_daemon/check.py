# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import os
import re
import socket
import urllib2
from collections import defaultdict, Counter, deque
from math import ceil

# project
from checks import AgentCheck
from config import _is_affirmative
from utils.dockerutil import (DockerUtil,
                              MountException,
                              BogusPIDException,
                              SWARM_SVC_LABEL,
                              RANCHER_CONTAINER_NAME,
                              RANCHER_SVC_NAME,
                              RANCHER_STACK_NAME)
from utils.kubernetes import KubeUtil
from utils.platform import Platform
from utils.service_discovery.sd_backend import get_sd_backend
from utils.orchestrator import MetadataCollector


EVENT_TYPE = 'docker'
SERVICE_CHECK_NAME = 'docker.service_up'
HEALTHCHECK_SERVICE_CHECK_NAME = 'docker.container_health'
EXIT_SERVICE_CHECK_NAME = 'docker.exit'
SIZE_REFRESH_RATE = 5  # Collect container sizes every 5 iterations of the check
CONTAINER_ID_RE = re.compile('[0-9a-f]{64}')

DISK_STATS_RE = re.compile('([0-9.]+)\s?([a-zA-Z]+)')

GAUGE = AgentCheck.gauge
RATE = AgentCheck.rate
HISTORATE = AgentCheck.generate_historate_func(["container_name"])
HISTO = AgentCheck.generate_histogram_func(["container_name"])
FUNC_MAP = {
    GAUGE: {True: HISTO, False: GAUGE},
    RATE: {True: HISTORATE, False: RATE}
}

UNIT_MAP = {
    'kb': 1000,
    'mb': 1000000,
    'gb': 1000000000,
    'tb': 1000000000000
}

CGROUP_METRICS = [
    {
        "cgroup": "memory",
        "file": "memory.stat",
        "metrics": {
            "cache": ("docker.mem.cache", GAUGE),
            "rss": ("docker.mem.rss", GAUGE),
            "swap": ("docker.mem.swap", GAUGE),
        },
        "to_compute": {
            # We only get these metrics if they are properly set, i.e. they are a "reasonable" value
            "docker.mem.limit": (["hierarchical_memory_limit"], lambda x: float(x) if float(x) < 2 ** 60 else None, GAUGE),
            "docker.mem.sw_limit": (["hierarchical_memsw_limit"], lambda x: float(x) if float(x) < 2 ** 60 else None, GAUGE),
            "docker.mem.in_use": (["rss", "hierarchical_memory_limit"], lambda x, y: float(x)/float(y) if float(y) < 2 ** 60 else None, GAUGE),
            "docker.mem.sw_in_use": (["swap", "rss", "hierarchical_memsw_limit"], lambda x, y, z: float(x + y)/float(z) if float(z) < 2 ** 60 else None, GAUGE)
        }
    },
    {
        "cgroup": "memory",
        "file": "memory.soft_limit_in_bytes",
        "metrics": {
            "softlimit": ("docker.mem.soft_limit", GAUGE),
        },
    },
    {
        "cgroup": "cpuacct",
        "file": "cpuacct.stat",
        "metrics": {
            "user": ("docker.cpu.user", RATE),
            "system": ("docker.cpu.system", RATE),
        },
    },
    {
        "cgroup": "cpuacct",
        "file": "cpuacct.usage",
        "metrics": {
            "usage": ("docker.cpu.usage", RATE),
        }
    },
    {
        "cgroup": "cpu",
        "file": "cpu.stat",
        "metrics": {
            "nr_throttled": ("docker.cpu.throttled", RATE)
        },
    },
    {
        "cgroup": "blkio",
        "file": 'blkio.throttle.io_service_bytes',
        "metrics": {
            "io_read": ("docker.io.read_bytes", RATE),
            "io_write": ("docker.io.write_bytes", RATE),
        },
    },
]

DEFAULT_CONTAINER_TAGS = [
    "docker_image",
    "image_name",
    "image_tag",
]

DEFAULT_PERFORMANCE_TAGS = [
    "container_name",
    "docker_image",
    "image_name",
    "image_tag",
]

DEFAULT_IMAGE_TAGS = [
    'image_name',
    'image_tag'
]

DEFAULT_LABELS_AS_TAGS = [
    SWARM_SVC_LABEL
]


TAG_EXTRACTORS = {
    "docker_image": lambda c: [DockerUtil().image_name_extractor(c)],
    "image_name": lambda c: DockerUtil().image_tag_extractor(c, 0),
    "image_tag": lambda c: DockerUtil().image_tag_extractor(c, 1),
    "container_command": lambda c: [c["Command"]],
    "container_name": DockerUtil.container_name_extractor,
    "container_id": lambda c: [c["Id"]],
}

# Event attributes not to include as tags since they are collected with e.g. performance tags
EXCLUDED_ATTRIBUTES = [
    'image',
    'name',
    'container',
]
DEFAULT_FILTERED_EVENT_TYPES = [
    'top',
    'exec_create',
    'exec_start',
]

CONTAINER = "container"
PERFORMANCE = "performance"
FILTERED = "filtered"
HEALTHCHECK = "healthcheck"
IMAGE = "image"

ERROR_ALERT_TYPE = ['oom', 'kill']


def compile_filter_rules(rules):
    patterns = []
    tag_names = []

    for rule in rules:
        patterns.append(re.compile(rule))
        tag_names.append(rule.split(':')[0])

    return patterns, tag_names


class DockerDaemon(AgentCheck):
    """Collect metrics and events from Docker API and cgroups."""

    def __init__(self, name, init_config, agentConfig, instances=None):
        if instances is not None and len(instances) > 1:
            raise Exception("Docker check only supports one configured instance.")
        AgentCheck.__init__(self, name, init_config,
                            agentConfig, instances=instances)
        self.init_success = False
        self._service_discovery = agentConfig.get('service_discovery') and \
            agentConfig.get('service_discovery_backend') == 'docker'

        global_labels_as_tags = agentConfig.get('docker_labels_as_tags')
        if global_labels_as_tags:
            self.collect_labels_as_tags = [label.strip() for label in global_labels_as_tags.split(',')]
        else:
            self.collect_labels_as_tags = DEFAULT_LABELS_AS_TAGS
        self.init()

    def init(self):
        try:
            instance = self.instances[0]

            # Getting custom tags for service checks when docker is down
            self.custom_tags = instance.get("tags", [])

            self.docker_util = DockerUtil()
            if not self.docker_util.client:
                raise Exception("Failed to initialize Docker client.")

            self.docker_gateway = DockerUtil.get_gateway()
            self.metadata_collector = MetadataCollector()

            self.kubeutil = None
            if Platform.is_k8s():
                try:
                    self.kubeutil = KubeUtil()
                except Exception as ex:
                    self.log.error("Couldn't instantiate the kubernetes client, "
                                   "subsequent kubernetes calls will fail as well. Error: %s" % str(ex))

            # We configure the check with the right cgroup settings for this host
            # Just needs to be done once
            self._mountpoints = self.docker_util.get_mountpoints(CGROUP_METRICS)
            self._latest_size_query = 0
            self._filtered_containers = set()
            self._disable_net_metrics = False

            # Set tagging options
            # The collect_labels_as_tags is legacy, only tagging docker metrics.
            # It is replaced by docker_labels_as_tags in datadog.conf.
            # We keep this line for backward compatibility.
            if "collect_labels_as_tags" in instance:
                self.collect_labels_as_tags = instance.get("collect_labels_as_tags")

            self.kube_pod_tags = {}

            self.use_histogram = _is_affirmative(instance.get('use_histogram', False))
            performance_tags = instance.get("performance_tags", DEFAULT_PERFORMANCE_TAGS)

            self.tag_names = {
                CONTAINER: instance.get("container_tags", DEFAULT_CONTAINER_TAGS),
                PERFORMANCE: performance_tags,
                IMAGE: instance.get('image_tags', DEFAULT_IMAGE_TAGS)
            }

            # Set filtering settings
            if self.docker_util.filtering_enabled:
                self.tag_names[FILTERED] = self.docker_util.filtered_tag_names

            # Container network mapping cache
            self.network_mappings = {}

            # get the health check whitelist
            self.whitelist_patterns = None
            health_scs_whitelist = instance.get('health_service_check_whitelist', [])
            if health_scs_whitelist:
                patterns, whitelist_tags = compile_filter_rules(health_scs_whitelist)
                self.whitelist_patterns = set(patterns)
                self.tag_names[HEALTHCHECK] = set(whitelist_tags)

            # Other options
            self.collect_image_stats = _is_affirmative(instance.get('collect_images_stats', False))
            self.collect_container_size = _is_affirmative(instance.get('collect_container_size', False))
            self.collect_container_count = _is_affirmative(instance.get('collect_container_count', False))
            self.collect_volume_count = _is_affirmative(instance.get('collect_volume_count', False))
            self.collect_events = _is_affirmative(instance.get('collect_events', True))
            self.event_attributes_as_tags = instance.get('event_attributes_as_tags', [])
            self.collect_image_size = _is_affirmative(instance.get('collect_image_size', False))
            self.collect_disk_stats = _is_affirmative(instance.get('collect_disk_stats', False))
            self.collect_exit_codes = _is_affirmative(instance.get('collect_exit_codes', False))
            self.collect_ecs_tags = _is_affirmative(instance.get('ecs_tags', True)) and Platform.is_ecs_instance()

            self.filtered_event_types = tuple(instance.get("filtered_event_types", DEFAULT_FILTERED_EVENT_TYPES))

            self.capped_metrics = instance.get('capped_metrics')

        except Exception as e:
            self.log.critical(e)
            self.warning("Initialization failed. Will retry at next iteration")
        else:
            self.init_success = True

    def check(self, instance):
        """Run the Docker check for one instance."""
        if not self.init_success:
            # Initialization can fail if cgroups are not ready or docker daemon is down. So we retry if needed
            # https://github.com/DataDog/dd-agent/issues/1896
            self.init()

            try:
                if self.docker_util.client is None:
                    message = "Unable to connect to Docker daemon"
                    self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                                       message=message, tags=self.custom_tags)
                    return
            except Exception as ex:
                self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                                   message=str(ex), tags=self.custom_tags)
                return

            if not self.init_success:
                # Initialization failed, will try later
                return

        try:
            # Report image metrics
            if self.collect_image_stats:
                self._count_and_weigh_images()

            if Platform.is_k8s():
                self.kube_pod_tags = {}
                if self.kubeutil:
                    try:
                        self.kube_pod_tags = self.kubeutil.get_kube_pod_tags()
                    except Exception as e:
                        self.log.warning('Could not retrieve kubernetes labels: %s' % str(e))

            # containers running with custom cgroups?
            custom_cgroups = _is_affirmative(instance.get('custom_cgroups', False))

            # Get the list of containers and the index of their names
            health_service_checks = True if self.whitelist_patterns else False
            containers_by_id = self._get_and_count_containers(custom_cgroups, health_service_checks)
            containers_by_id = self._crawl_container_pids(containers_by_id, custom_cgroups)

            # Send events from Docker API
            if self.collect_events or self._service_discovery or not self._disable_net_metrics or self.collect_exit_codes:
                self._process_events(containers_by_id)

            # Report performance container metrics (cpu, mem, net, io)
            self._report_performance_metrics(containers_by_id)

            if self.collect_container_size:
                self._report_container_size(containers_by_id)

            if self.collect_container_count:
                self._report_container_count(containers_by_id)

            if self.collect_volume_count:
                self._report_volume_count()

            # Collect disk stats from Docker info command
            if self.collect_disk_stats:
                self._report_disk_stats()

            if health_service_checks:
                self._send_container_healthcheck_sc(containers_by_id)
        except:
            self.log.exception("Docker_daemon check failed")
            self.warning("Check failed. Will retry at next iteration")

        if self.capped_metrics:
            self.filter_capped_metrics()

    def _count_and_weigh_images(self):
        try:
            tags = self._get_tags()
            active_images = self.docker_util.client.images(all=False)
            active_images_len = len(active_images)
            all_images_len = len(self.docker_util.client.images(quiet=True, all=True))
            self.gauge("docker.images.available", active_images_len, tags=tags)
            self.gauge("docker.images.intermediate", (all_images_len - active_images_len), tags=tags)

            if self.collect_image_size:
                self._report_image_size(active_images)

        except Exception as e:
            # It's not an important metric, keep going if it fails
            self.warning("Failed to count Docker images. Exception: {0}".format(e))

    def _get_and_count_containers(self, custom_cgroups=False, healthchecks=False):
        """List all the containers from the API, filter and count them."""

        # Querying the size of containers is slow, we don't do it at each run
        must_query_size = self.collect_container_size and self._latest_size_query == 0
        self._latest_size_query = (self._latest_size_query + 1) % SIZE_REFRESH_RATE

        running_containers_count = Counter()
        all_containers_count = Counter()

        try:
            containers = self.docker_util.client.containers(all=True, size=must_query_size)
        except Exception as e:
            message = "Unable to list Docker containers: {0}".format(e)
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                               message=message, tags=self.custom_tags)
            raise Exception(message)

        else:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.OK, tags=self.custom_tags)

        # Create a set of filtered containers based on the exclude/include rules
        # and cache these rules in docker_util
        self._filter_containers(containers)

        containers_by_id = {}

        for container in containers:
            container_name = DockerUtil.container_name_extractor(container)[0]

            container_status_tags = self._get_tags(container, CONTAINER)

            all_containers_count[tuple(sorted(container_status_tags))] += 1
            if self._is_container_running(container):
                running_containers_count[tuple(sorted(container_status_tags))] += 1

            # Check if the container is included/excluded via its tags
            if self._is_container_excluded(container):
                self.log.debug("Container {0} is excluded".format(container_name))
                continue

            containers_by_id[container['Id']] = container

            # grab pid via API if custom cgroups - otherwise we won't find process when
            # crawling for pids.
            if custom_cgroups or healthchecks:
                try:
                    inspect_dict = self.docker_util.client.inspect_container(container_name)
                    container['_pid'] = inspect_dict['State']['Pid']
                    container['health'] = inspect_dict['State'].get('Health', {})
                except Exception as e:
                    self.log.debug("Unable to inspect Docker container: %s", e)

        total_count = 0
        # TODO: deprecate these 2, they should be replaced by _report_container_count
        for tags, count in running_containers_count.iteritems():
            total_count += count
            self.gauge("docker.containers.running", count, tags=list(tags))
        self.gauge("docker.containers.running.total", total_count, tags=self.custom_tags)

        total_count = 0
        for tags, count in all_containers_count.iteritems():
            stopped_count = count - running_containers_count[tags]
            total_count += stopped_count
            self.gauge("docker.containers.stopped", stopped_count, tags=list(tags))
        self.gauge("docker.containers.stopped.total", total_count, tags=self.custom_tags)

        return containers_by_id

    def _is_container_running(self, container):
        """Tell if a container is running, according to its status.

        There is no "nice" API field to figure it out. We just look at the "Status" field, knowing how it is generated.
        See: https://github.com/docker/docker/blob/v1.6.2/daemon/state.go#L35
        """
        return container["Status"].startswith("Up") or container["Status"].startswith("Restarting")

    def _get_tags(self, entity=None, tag_type=None):
        """Generate the tags for a given entity (container or image) according to a list of tag names."""
        # Start with custom tags
        tags = list(self.custom_tags)

        # Collect pod names as tags on kubernetes
        if Platform.is_k8s() and KubeUtil.POD_NAME_LABEL not in self.collect_labels_as_tags:
            self.collect_labels_as_tags.append(KubeUtil.POD_NAME_LABEL)
            self.collect_labels_as_tags.append(KubeUtil.CONTAINER_NAME_LABEL)

        # Collect container names as tags on rancher
        if Platform.is_rancher():
            if RANCHER_CONTAINER_NAME not in self.collect_labels_as_tags:
                self.collect_labels_as_tags.append(RANCHER_CONTAINER_NAME)
            if RANCHER_SVC_NAME not in self.collect_labels_as_tags:
                self.collect_labels_as_tags.append(RANCHER_SVC_NAME)
            if RANCHER_STACK_NAME not in self.collect_labels_as_tags:
                self.collect_labels_as_tags.append(RANCHER_STACK_NAME)

        if entity is not None:
            pod_name = None
            namespace = None
            # Get labels as tags
            labels = entity.get("Labels")
            if labels is not None:
                for k in self.collect_labels_as_tags:
                    if k in labels:
                        v = labels[k]
                        if k == KubeUtil.POD_NAME_LABEL and Platform.is_k8s():
                            pod_name = v
                            k = "pod_name"
                            if "-" in pod_name:
                                replication_controller = "-".join(pod_name.split("-")[:-1])
                                if "/" in replication_controller:  # k8s <= 1.1
                                    namespace, replication_controller = replication_controller.split("/", 1)

                                elif KubeUtil.NAMESPACE_LABEL in labels:  # k8s >= 1.2
                                    namespace = labels[KubeUtil.NAMESPACE_LABEL]

                                tags.append("kube_namespace:%s" % namespace)
                                tags.append("kube_replication_controller:%s" % replication_controller)
                                tags.append("pod_name:%s" % pod_name)

                        elif k == KubeUtil.CONTAINER_NAME_LABEL and Platform.is_k8s():
                            if v:
                                tags.append("kube_container_name:%s" % v)
                        elif k == SWARM_SVC_LABEL and Platform.is_swarm():
                            if v:
                                tags.append("swarm_service:%s" % v)
                        elif k == RANCHER_CONTAINER_NAME and Platform.is_rancher():
                            if v:
                                tags.append('rancher_container:%s' % v)
                        elif k == RANCHER_SVC_NAME and Platform.is_rancher():
                            if v:
                                tags.append('rancher_service:%s' % v)
                        elif k == RANCHER_STACK_NAME and Platform.is_rancher():
                            if v:
                                tags.append('rancher_stack:%s' % v)

                        elif not v:
                            tags.append(k)

                        else:
                            tags.append("%s:%s" % (k, v))

                    if k == KubeUtil.POD_NAME_LABEL and Platform.is_k8s() and k not in labels:
                        tags.append("pod_name:no_pod")

            # Get entity specific tags
            if tag_type is not None:
                tag_names = self.tag_names[tag_type]
                for tag_name in tag_names:
                    tag_value = self._extract_tag_value(entity, tag_name)
                    if tag_value is not None:
                        for t in tag_value:
                            tags.append('%s:%s' % (tag_name, str(t).strip()))

            # Add kube labels and creator/service tags
            if Platform.is_k8s() and namespace and pod_name:
                kube_tags = self.kube_pod_tags.get("{0}/{1}".format(namespace, pod_name))
                if kube_tags:
                    tags.extend(list(kube_tags))

            if self.metadata_collector.has_detected():
                orch_tags = self.metadata_collector.get_container_tags(co=entity)
                tags.extend(orch_tags)

        return tags

    def _extract_tag_value(self, entity, tag_name):
        """Extra tag information from the API result (containers or images).
        Cache extracted tags inside the entity object.
        """
        if tag_name not in TAG_EXTRACTORS:
            self.warning("{0} isn't a supported tag".format(tag_name))
            return

        # Check for already extracted tags
        if "_tag_values" not in entity:
            entity["_tag_values"] = {}

        if tag_name not in entity["_tag_values"]:
            entity["_tag_values"][tag_name] = TAG_EXTRACTORS[tag_name](entity)

        return entity["_tag_values"][tag_name]

    def _filter_containers(self, containers):
        if not self.docker_util.filtering_enabled:
            return

        self._filtered_containers = set()
        for container in containers:
            container_tags = self._get_tags(container, FILTERED)
            # exclude/include patterns are stored in docker_util to share them with other container-related checks
            if self.docker_util.are_tags_filtered(container_tags):
                container_name = DockerUtil.container_name_extractor(container)[0]
                self._filtered_containers.add(container_name)
                self.log.debug("Container {0} is filtered".format(container_name))

    def _is_container_excluded(self, container):
        """Check if a container is excluded according to the filter rules.

        Requires _filter_containers to run first.
        """
        container_name = DockerUtil.container_name_extractor(container)[0]
        return container_name in self._filtered_containers

    def _report_container_size(self, containers_by_id):
        for container in containers_by_id.itervalues():
            if self._is_container_excluded(container):
                continue

            tags = self._get_tags(container, PERFORMANCE)
            m_func = FUNC_MAP[GAUGE][self.use_histogram]
            if "SizeRw" in container:
                m_func(self, 'docker.container.size_rw', container['SizeRw'],
                       tags=tags)
            if "SizeRootFs" in container:
                m_func(
                    self, 'docker.container.size_rootfs', container['SizeRootFs'],
                    tags=tags)

    def _send_container_healthcheck_sc(self, containers_by_id):
        """Send health service checks for containers."""
        for container in containers_by_id.itervalues():
            healthcheck_tags = self._get_tags(container, HEALTHCHECK)
            match = False
            for tag in healthcheck_tags:
                for rule in self.whitelist_patterns:
                    if re.match(rule, tag):
                        match = True

                        self._submit_healthcheck_sc(container)
                        break

                if match:
                    break

    def _submit_healthcheck_sc(self, container):
        health = container.get('health', {})
        status = AgentCheck.UNKNOWN
        if health:
            _health = health.get('Status', '')
            if _health == 'unhealthy':
                status = AgentCheck.CRITICAL
            elif _health == 'healthy':
                status = AgentCheck.OK

        tags = self._get_tags(container, CONTAINER)
        self.service_check(HEALTHCHECK_SERVICE_CHECK_NAME, status, tags=tags)

    def _report_container_count(self, containers_by_id):
        """Report container count per state"""
        m_func = FUNC_MAP[GAUGE][self.use_histogram]

        per_state_count = defaultdict(int)

        filterlambda = lambda ctr: not self._is_container_excluded(ctr)
        containers = list(filter(filterlambda, containers_by_id.values()))

        for ctr in containers:
            per_state_count[ctr.get('State', '')] += 1

        for state in per_state_count:
            if state:
                m_func(self, 'docker.container.count', per_state_count[state], tags=['container_state:%s' % state.lower()])

    def _report_volume_count(self):
        """Report volume count per state (dangling or not)"""
        m_func = FUNC_MAP[GAUGE][self.use_histogram]

        attached_volumes = self.docker_util.client.volumes(filters={'dangling': False})
        dangling_volumes = self.docker_util.client.volumes(filters={'dangling': True})
        attached_count = len(attached_volumes.get('Volumes', []) or [])
        dangling_count = len(dangling_volumes.get('Volumes', []) or [])
        m_func(self, 'docker.volume.count', attached_count, tags=['volume_state:attached'])
        m_func(self, 'docker.volume.count', dangling_count, tags=['volume_state:dangling'])

    def _report_image_size(self, images):
        for image in images:
            tags = self._get_tags(image, IMAGE)
            if 'VirtualSize' in image:
                self.gauge('docker.image.virtual_size', image['VirtualSize'], tags=tags)
            if 'Size' in image:
                self.gauge('docker.image.size', image['Size'], tags=tags)

    # Performance metrics

    def _report_performance_metrics(self, containers_by_id):

        containers_without_proc_root = []
        for container_id, container in containers_by_id.iteritems():
            if self._is_container_excluded(container) or not self._is_container_running(container):
                continue

            tags = self._get_tags(container, PERFORMANCE)

            try:
                self._report_cgroup_metrics(container, tags)
                if "_proc_root" not in container:
                    containers_without_proc_root.append(DockerUtil.container_name_extractor(container)[0])
                    continue
                self._report_net_metrics(container, tags)
            except BogusPIDException as e:
                self.log.warning('Unable to report cgroup metrics for container %s: %s', container_id[:12], e)

        if containers_without_proc_root:
            message = "Couldn't find pid directory for containers: {0}. They'll be missing network metrics".format(
                ", ".join(containers_without_proc_root))
            if not Platform.is_k8s():
                self.warning(message)
            else:
                # On kubernetes, this is kind of expected. Network metrics will be collected by the kubernetes integration anyway
                self.log.debug(message)

    def _report_cgroup_metrics(self, container, tags):
        cgroup_stat_file_failures = 0
        if not container.get('_pid'):
            raise BogusPIDException('Cannot report on bogus pid(0)')

        for cgroup in CGROUP_METRICS:
            try:
                stat_file = self._get_cgroup_from_proc(cgroup["cgroup"], container['_pid'], cgroup['file'])
            except MountException as e:
                # We can't find a stat file
                self.warning(str(e))
                cgroup_stat_file_failures += 1
                if cgroup_stat_file_failures >= len(CGROUP_METRICS):
                    self.warning("Couldn't find the cgroup files. Skipping the CGROUP_METRICS for now.")
            except IOError as e:
                self.log.debug("Cannot read cgroup file, container likely raced to finish : %s", e)
            else:
                stats = self._parse_cgroup_file(stat_file)
                if stats:
                    for key, (dd_key, metric_func) in cgroup['metrics'].iteritems():
                        metric_func = FUNC_MAP[metric_func][self.use_histogram]
                        if key in stats:
                            metric_func(self, dd_key, int(stats[key]), tags=tags)

                    # Computed metrics
                    for mname, (key_list, fct, metric_func) in cgroup.get('to_compute', {}).iteritems():
                        values = [stats[key] for key in key_list if key in stats]
                        if len(values) != len(key_list):
                            self.log.debug("Couldn't compute {0}, some keys were missing.".format(mname))
                            continue
                        value = fct(*values)
                        metric_func = FUNC_MAP[metric_func][self.use_histogram]
                        if value is not None:
                            metric_func(self, mname, value, tags=tags)

    def _report_net_metrics(self, container, tags):
        """Find container network metrics by looking at /proc/$PID/net/dev of the container process."""
        if self._disable_net_metrics:
            self.log.debug("Network metrics are disabled. Skipping")
            return

        proc_net_file = os.path.join(container['_proc_root'], 'net/dev')

        try:
            if container['Id'] in self.network_mappings:
                networks = self.network_mappings[container['Id']]
            else:
                networks = self.docker_util.get_container_network_mapping(container)
                if not networks:
                    networks = {'eth0': 'bridge'}
                self.network_mappings[container['Id']] = networks
        except Exception as e:
            # Revert to previous behaviour if the method is missing or failing
            # Debug message will only appear once per container, then the cache is used
            self.log.debug("Failed to build docker network mapping, using failsafe. Exception: {0}".format(e))
            networks = {'eth0': 'bridge'}
            self.network_mappings[container['Id']] = networks

        try:
            with open(proc_net_file, 'r') as fp:
                lines = fp.readlines()
                """Two first lines are headers:
                Inter-|   Receive                                                |  Transmit
                 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
                """
                for l in lines[2:]:
                    cols = l.split(':', 1)
                    interface_name = str(cols[0]).strip()
                    if interface_name in networks:
                        net_tags = tags + ['docker_network:'+networks[interface_name]]
                        x = cols[1].split()
                        m_func = FUNC_MAP[RATE][self.use_histogram]
                        m_func(self, "docker.net.bytes_rcvd", long(x[0]), net_tags)
                        m_func(self, "docker.net.bytes_sent", long(x[8]), net_tags)

        except Exception as e:
            # It is possible that the container got stopped between the API call and now
            self.warning("Failed to report IO metrics from file {0}. Exception: {1}".format(proc_net_file, e))

    def _invalidate_network_mapping_cache(self, api_events):
        for ev in api_events:
            try:
                if ev.get('Type') == 'network' and ev.get('Action').endswith('connect'):
                    container_id = ev.get('Actor').get('Attributes').get('container')
                    if container_id in self.network_mappings:
                        self.log.debug("Removing network mapping cache for container %s" % container_id)
                        del self.network_mappings[container_id]
            except Exception:
                self.log.warning('Malformed network event: %s' % str(ev))

    def _process_events(self, containers_by_id):
        api_events = self._get_events()

        if self.collect_exit_codes:
            self._report_exit_codes(api_events, containers_by_id)

        if self.collect_events:
            try:
                aggregated_events = self._pre_aggregate_events(api_events, containers_by_id)
                events = self._format_events(aggregated_events, containers_by_id)
            except (socket.timeout, urllib2.URLError):
                self.warning('Timeout when collecting events. Events will be missing.')
                return
            except Exception as e:
                self.warning("Unexpected exception when collecting events: {0}. "
                             "Events will be missing".format(e))
                return

            for ev in events:
                self.log.debug("Creating event: %s" % ev['msg_title'])
                self.event(ev)

    def _get_events(self):
        """Get the list of events."""
        events, changed_container_ids = self.docker_util.get_events()
        if not self._disable_net_metrics:
            self._invalidate_network_mapping_cache(events)
        if changed_container_ids and self._service_discovery:
            get_sd_backend(self.agentConfig).update_checks(changed_container_ids)
        if changed_container_ids:
            self.metadata_collector.invalidate_cache(events)
        return events

    def _pre_aggregate_events(self, api_events, containers_by_id):
        # Aggregate events, one per image. Put newer events first.
        events = defaultdict(deque)
        for event in api_events:
            # Skip events related to filtered containers
            container = containers_by_id.get(event.get('id'))
            if container is not None and self._is_container_excluded(container):
                self.log.debug("Excluded event: container {0} status changed to {1}".format(
                    event['id'], event['status']))
                continue
            # from may be missing (for network events for example)
            if 'from' in event:
                image_name = event['from']
                if image_name.startswith('sha256:'):
                    image_name = self.docker_util.image_name_extractor({'Image': image_name})
                events[image_name].appendleft(event)
        return events

    def _format_events(self, aggregated_events, containers_by_id):
        events = []
        for image_name, event_group in aggregated_events.iteritems():
            container_tags = set()
            filtered_events_count = 0
            normal_prio_events = []

            for event in event_group:
                # Only keep events that are not configured to be filtered out
                if event['status'].startswith(self.filtered_event_types):
                    filtered_events_count += 1
                    continue
                container_name = event['id'][:11]

                if event['id'] in containers_by_id:
                    cont = containers_by_id[event['id']]
                    container_name = DockerUtil.container_name_extractor(cont)[0]
                    container_tags.update(self._get_tags(cont, PERFORMANCE))
                    container_tags.add('container_name:%s' % container_name)
                    # Add additionnal docker event attributes as tag
                    for attr in self.event_attributes_as_tags:
                        if attr in event['Actor']['Attributes'] and attr not in EXCLUDED_ATTRIBUTES:
                            container_tags.add('%s:%s' % (attr, event['Actor']['Attributes'][attr]))

                normal_prio_events.append((event, container_name))
            if filtered_events_count:
                self.log.debug('%d events were filtered out because of ignored event type' % filtered_events_count)

            normal_event = self._create_dd_event(normal_prio_events, image_name, container_tags, priority='Normal')
            if normal_event:
                events.append(normal_event)

        return events

    def _report_exit_codes(self, events, containers_by_id):
        for event in events:
            container_tags = set()
            container = containers_by_id.get(event.get('id'))
            # Skip events related to filtered containers
            if container is not None and self._is_container_excluded(container):
                continue

            # Report the exit code in case of a DIE event
            if container is not None and event['status'] == 'die':
                container_name = DockerUtil.container_name_extractor(container)[0]
                container_tags.update(self._get_tags(container, CONTAINER))
                container_tags.add('container_name:%s' % container_name)
                try:
                    exit_code = int(event['Actor']['Attributes']['exitCode'])
                    message = 'Container %s exited with %s' % (container_name, exit_code)
                    status = AgentCheck.OK if exit_code == 0 else AgentCheck.CRITICAL
                    self.service_check(EXIT_SERVICE_CHECK_NAME, status, tags=list(container_tags), message=message)
                except KeyError:
                    self.log.warning('Unable to collect the exit code for container %s' % container_name)

    def _create_dd_event(self, events, image, c_tags, priority='Normal'):
        """Create the actual event to submit from a list of similar docker events"""
        if not events:
            return

        max_timestamp = 0
        status = defaultdict(int)
        status_change = []

        for ev, c_name in events:
            max_timestamp = max(max_timestamp, int(ev['time']))
            status[ev['status']] += 1
            status_change.append([c_name, ev['status']])

        status_text = ", ".join(["%d %s" % (count, st) for st, count in status.iteritems()])
        msg_title = "%s %s on %s" % (image, status_text, self.hostname)
        msg_body = (
            "%%%\n"
            "{image_name} {status} on {hostname}\n"
            "```\n{status_changes}\n```\n"
            "%%%"
        ).format(
            image_name=image,
            status=status_text,
            hostname=self.hostname,
            status_changes="\n".join(
                ["%s \t%s" % (change[1].upper(), change[0]) for change in status_change])
        )

        if any(error in status_text for error in ERROR_ALERT_TYPE):
            alert_type = "error"
        else:
            alert_type = None

        return {
            'timestamp': max_timestamp,
            'host': self.hostname,
            'event_type': EVENT_TYPE,
            'msg_title': msg_title,
            'msg_text': msg_body,
            'source_type_name': EVENT_TYPE,
            'event_object': 'docker:%s' % image,
            'tags': list(c_tags),
            'alert_type': alert_type,
            'priority': priority
        }

    def _report_disk_stats(self):
        """Report metrics about the volume space usage"""
        stats = {
            'docker.data.used': None,
            'docker.data.total': None,
            'docker.data.free': None,
            'docker.metadata.used': None,
            'docker.metadata.total': None,
            'docker.metadata.free': None
            # these two are calculated by _calc_percent_disk_stats
            # 'docker.data.percent': None,
            # 'docker.metadata.percent': None
        }
        info = self.docker_util.client.info()
        driver_status = info.get('DriverStatus', [])
        if not driver_status:
            self.log.warning('Disk metrics collection is enabled but docker info did not'
                             ' report any. Your storage driver might not support them, skipping.')
            return
        for metric in driver_status:
            # only consider metrics about disk space
            if len(metric) == 2 and 'Space' in metric[0]:
                # identify Data and Metadata metrics
                mtype = 'data'
                if 'Metadata' in metric[0]:
                    mtype = 'metadata'

                if 'Used' in metric[0]:
                    stats['docker.{0}.used'.format(mtype)] = metric[1]
                elif 'Space Total' in metric[0]:
                    stats['docker.{0}.total'.format(mtype)] = metric[1]
                elif 'Space Available' in metric[0]:
                    stats['docker.{0}.free'.format(mtype)] = metric[1]
        stats = self._format_disk_metrics(stats)
        stats.update(self._calc_percent_disk_stats(stats))
        tags = self._get_tags()
        for name, val in stats.iteritems():
            if val is not None:
                self.gauge(name, val, tags)

    def _format_disk_metrics(self, metrics):
        """Cast the disk stats to float and convert them to bytes"""
        for name, raw_val in metrics.iteritems():
            if raw_val:
                match = DISK_STATS_RE.search(raw_val)
                if match is None or len(match.groups()) != 2:
                    self.log.warning('Can\'t parse value %s for disk metric %s. Dropping it.' % (raw_val, name))
                    metrics[name] = None
                val, unit = match.groups()
                # by default some are uppercased others lowercased. That's error prone.
                unit = unit.lower()
                try:
                    val = int(float(val) * UNIT_MAP[unit])
                    metrics[name] = val
                except KeyError:
                    self.log.error('Unrecognized unit %s for disk metric %s. Dropping it.' % (unit, name))
                    metrics[name] = None
        return metrics

    def _calc_percent_disk_stats(self, stats):
        """Calculate a percentage of used disk space for data and metadata"""
        mtypes = ['data', 'metadata']
        percs = {}
        for mtype in mtypes:
            used = stats.get('docker.{0}.used'.format(mtype))
            total = stats.get('docker.{0}.total'.format(mtype))
            free = stats.get('docker.{0}.free'.format(mtype))
            if used and total and free and ceil(total) < free + used:
                self.log.debug('used, free, and total disk metrics may be wrong, '
                               'used: %s, free: %s, total: %s',
                               used, free, total)
                total = used + free
            try:
                if isinstance(used, int):
                    percs['docker.{0}.percent'.format(mtype)] = round(100 * float(used) / float(total), 2)
                elif isinstance(free, int):
                    percs['docker.{0}.percent'.format(mtype)] = round(100 * (1.0 - (float(free) / float(total))), 2)
            except ZeroDivisionError:
                self.log.error('docker.{0}.total is 0, calculating docker.{1}.percent'
                               ' is not possible.'.format(mtype, mtype))
        return percs

    # Cgroups
    def _get_cgroup_from_proc(self, cgroup, pid, filename):
        """Find a specific cgroup file, containing metrics to extract."""
        params = {
            "file": filename,
        }
        return DockerUtil.find_cgroup_from_proc(self._mountpoints, pid, cgroup, self.docker_util._docker_root) % (params)

    def _parse_cgroup_file(self, stat_file):
        """Parse a cgroup pseudo file for key/values."""
        self.log.debug("Opening cgroup file: %s" % stat_file)
        try:
            with open(stat_file, 'r') as fp:
                if 'blkio' in stat_file:
                    return self._parse_blkio_metrics(fp.read().splitlines())
                elif 'cpuacct.usage' in stat_file:
                    return dict({'usage': str(int(fp.read())/10000000)})
                elif 'memory.soft_limit_in_bytes' in stat_file:
                    value = int(fp.read())
                    # do not report kernel max default value (uint64 * 4096)
                    # see https://github.com/torvalds/linux/blob/5b36577109be007a6ecf4b65b54cbc9118463c2b/mm/memcontrol.c#L2844-L2845
                    # 2 ** 60 is kept for consistency of other cgroups metrics
                    if value < 2 ** 60:
                        return dict({'softlimit': value})
                else:
                    return dict(map(lambda x: x.split(' ', 1), fp.read().splitlines()))
        except IOError:
            # It is possible that the container got stopped between the API call and now.
            # Some files can also be missing (like cpu.stat) and that's fine.
            self.log.debug("Can't open %s. Its metrics will be missing." % stat_file)

    def _parse_blkio_metrics(self, stats):
        """Parse the blkio metrics."""
        metrics = {
            'io_read': 0,
            'io_write': 0,
        }
        for line in stats:
            if 'Read' in line:
                metrics['io_read'] += int(line.split()[2])
            if 'Write' in line:
                metrics['io_write'] += int(line.split()[2])
        return metrics

    def _is_container_cgroup(self, line, selinux_policy):
        if line[1] not in ('cpu,cpuacct', 'cpuacct,cpu', 'cpuacct') or line[2] == '/docker-daemon':
            return False
        if 'docker' in line[2]:  # general case
            return True
        if 'docker' in selinux_policy:  # selinux
            return True
        if line[2].startswith('/') and re.match(CONTAINER_ID_RE, line[2][1:]):  # kubernetes
            return True
        if line[2].startswith('/') and re.match(CONTAINER_ID_RE, line[2].split('/')[-1]): # kube 1.6+ qos hierarchy
            return True
        return False

    # proc files
    def _crawl_container_pids(self, container_dict, custom_cgroups=False):
        """Crawl `/proc` to find container PIDs and add them to `containers_by_id`."""
        proc_path = os.path.join(self.docker_util._docker_root, 'proc')
        pid_dirs = [_dir for _dir in os.listdir(proc_path) if _dir.isdigit()]

        if len(pid_dirs) == 0:
            self.warning("Unable to find any pid directory in {0}. "
                         "If you are running the agent in a container, make sure to "
                         'share the volume properly: "/proc:/host/proc:ro". '
                         "See https://github.com/DataDog/docker-dd-agent/blob/master/README.md for more information. "
                         "Network metrics will be missing".format(proc_path))
            self._disable_net_metrics = True
            return container_dict

        self._disable_net_metrics = False

        for folder in pid_dirs:
            try:
                path = os.path.join(proc_path, folder, 'cgroup')
                with open(path, 'r') as f:
                    content = [line.strip().split(':') for line in f.readlines()]

                selinux_policy = ''
                path = os.path.join(proc_path, folder, 'attr', 'current')
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        selinux_policy = f.readlines()[0]
            except IOError, e:
                #  Issue #2074
                self.log.debug("Cannot read %s, process likely raced to finish : %s", path, e)
            except Exception as e:
                self.warning("Cannot read %s : %s" % (path, str(e)))
                continue

            try:
                for line in content:
                    if self._is_container_cgroup(line, selinux_policy):
                        cpuacct = line[2]
                        break
                else:
                    continue

                matches = re.findall(CONTAINER_ID_RE, cpuacct)
                if matches:
                    container_id = matches[-1]
                    if container_id not in container_dict:
                        self.log.debug(
                            "Container %s not in container_dict, it's likely excluded", container_id
                        )
                        continue
                    container_dict[container_id]['_pid'] = folder
                    container_dict[container_id]['_proc_root'] = os.path.join(proc_path, folder)
                elif custom_cgroups:  # if we match by pid that should be enough (?) - O(n) ugh!
                    for _, container in container_dict.iteritems():
                        if container.get('_pid') == int(folder):
                            container['_proc_root'] = os.path.join(proc_path, folder)
                            break

            except Exception, e:
                self.warning("Cannot parse %s content: %s" % (path, str(e)))
                continue
        return container_dict

    def filter_capped_metrics(self):
        metrics = self.aggregator.metrics.values()
        for metric in metrics:
            if metric.name in self.capped_metrics and len(metric.samples) >= 2:
                cap = self.capped_metrics[metric.name]
                val = metric._rate(metric.samples[-2], metric.samples[-1])
                if val > cap:
                    sample = metric.samples.pop()
                    self.log.debug("Dropped latest value %s (raw sample: %s) of "
                                   "metric %s as it was above the cap for this metric." % (val, sample, metric.name))
