# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""
YARN Cluster Metrics
--------------------
yarn.metrics.appsSubmitted          The number of submitted apps
yarn.metrics.appsCompleted          The number of completed apps
yarn.metrics.appsPending            The number of pending apps
yarn.metrics.appsRunning            The number of running apps
yarn.metrics.appsFailed             The number of failed apps
yarn.metrics.appsKilled             The number of killed apps
yarn.metrics.reservedMB             The size of reserved memory
yarn.metrics.availableMB            The amount of available memory
yarn.metrics.allocatedMB            The amount of allocated memory
yarn.metrics.totalMB                The amount of total memory
yarn.metrics.reservedVirtualCores   The number of reserved virtual cores
yarn.metrics.availableVirtualCores  The number of available virtual cores
yarn.metrics.allocatedVirtualCores  The number of allocated virtual cores
yarn.metrics.totalVirtualCores      The total number of virtual cores
yarn.metrics.containersAllocated    The number of containers allocated
yarn.metrics.containersReserved     The number of containers reserved
yarn.metrics.containersPending      The number of containers pending
yarn.metrics.totalNodes             The total number of nodes
yarn.metrics.activeNodes            The number of active nodes
yarn.metrics.lostNodes              The number of lost nodes
yarn.metrics.unhealthyNodes         The number of unhealthy nodes
yarn.metrics.decommissionedNodes    The number of decommissioned nodes
yarn.metrics.rebootedNodes          The number of rebooted nodes

YARN App Metrics
----------------
yarn.app.progress             The progress of the application as a percent
yarn.app.startedTime          The time in which application started (in ms since epoch)
yarn.app.finishedTime         The time in which the application finished (in ms since epoch)
yarn.app.elapsedTime          The elapsed time since the application started (in ms)
yarn.app.allocatedMB          The sum of memory in MB allocated to the applications running containers
yarn.app.allocatedVCores      The sum of virtual cores allocated to the applications running containers
yarn.app.runningContainers    The number of containers currently running for the application
yarn.app.memorySeconds        The amount of memory the application has allocated (megabyte-seconds)
yarn.app.vcoreSeconds         The amount of CPU resources the application has allocated (virtual core-seconds)

YARN Node Metrics
-----------------
yarn.node.lastHealthUpdate       The last time the node reported its health (in ms since epoch)
yarn.node.usedMemoryMB           The total amount of memory currently used on the node (in MB)
yarn.node.availMemoryMB          The total amount of memory currently available on the node (in MB)
yarn.node.usedVirtualCores       The total number of vCores currently used on the node
yarn.node.availableVirtualCores  The total number of vCores available on the node
yarn.node.numContainers          The total number of containers currently running on the node

YARN Capacity Scheduler Metrics
-----------------
yarn.queue.root.maxCapacity            The configured maximum queue capacity in percentage for root queue
yarn.queue.root.usedCapacity           The used queue capacity in percentage for root queue
yarn.queue.root.capacity               The configured queue capacity in percentage for root queue
yarn.queue.numPendingApplications      The number of pending applications in this queue
yarn.queue.userAMResourceLimit.memory  The maximum memory resources a user can use for Application Masters (in MB)
yarn.queue.userAMResourceLimit.vCores  The maximum vCpus a user can use for Application Masters
yarn.queue.absoluteCapacity            The absolute capacity percentage this queue can use of entire cluster
yarn.queue.userLimitFactor             The minimum user limit percent set in the configuration
yarn.queue.userLimit                   The user limit factor set in the configuration
yarn.queue.numApplications             The number of applications currently in the queue
yarn.queue.usedAMResource.memory       The memory resources used for Application Masters (in MB)
yarn.queue.usedAMResource.vCores       The vCpus used for Application Masters
yarn.queue.absoluteUsedCapacity        The absolute used capacity percentage this queue is using of the entire cluster
yarn.queue.resourcesUsed.memory        The total memory resources this queue is using (in MB)
yarn.queue.resourcesUsed.vCores        The total vCpus this queue is using
yarn.queue.AMResourceLimit.vCores      The maximum vCpus this queue can use for Application Masters
yarn.queue.AMResourceLimit.memory      The maximum memory resources this queue can use for Application Masters (in MB)
yarn.queue.capacity                    The configured queue capacity in percentage relative to its parent queue
yarn.queue.numActiveApplications       The number of active applications in this queue
yarn.queue.absoluteMaxCapacity         The absolute maximum capacity percentage this queue can use of the entire cluster
yarn.queue.usedCapacity                The used queue capacity in percentage
yarn.queue.numContainers               The number of containers being used
yarn.queue.maxCapacity                 The configured maximum queue capacity in percentage relative to its parent queue
yarn.queue.maxApplications             The maximum number of applications this queue can have
yarn.queue.maxApplicationsPerUser      The maximum number of active applications per user this queue can have
"""

# stdlib
from urlparse import urljoin, urlsplit, urlunsplit

# 3rd party
from requests.exceptions import Timeout, HTTPError, InvalidURL, ConnectionError, SSLError
import requests

# Project
from datadog_checks.base.checks import AgentCheck
from datadog_checks.base.config import _is_affirmative


# Default settings
DEFAULT_RM_URI = 'http://localhost:8088'
DEFAULT_TIMEOUT = 5
DEFAULT_CLUSTER_NAME = 'default_cluster'
DEFAULT_COLLECT_APP_METRICS = True
MAX_DETAILED_QUEUES = 100

# Path to retrieve cluster metrics
YARN_CLUSTER_METRICS_PATH = '/ws/v1/cluster/metrics'

# Path to retrieve YARN APPS
YARN_APPS_PATH = '/ws/v1/cluster/apps'

# Path to retrieve node statistics
YARN_NODES_PATH = '/ws/v1/cluster/nodes'

# Path to retrieve queue statistics
YARN_SCHEDULER_PATH = '/ws/v1/cluster/scheduler'

# Metric types
GAUGE = 'gauge'
INCREMENT = 'increment'

# Name of the service check
SERVICE_CHECK_NAME = 'yarn.can_connect'

# Application states to collect
YARN_APPLICATION_STATES = 'RUNNING'

# Cluster metrics identifier
YARN_CLUSTER_METRICS_ELEMENT = 'clusterMetrics'

# Cluster metrics for YARN
YARN_CLUSTER_METRICS = {
    'appsSubmitted': ('yarn.metrics.apps_submitted', GAUGE),
    'appsCompleted': ('yarn.metrics.apps_completed', GAUGE),
    'appsPending': ('yarn.metrics.apps_pending', GAUGE),
    'appsRunning': ('yarn.metrics.apps_running', GAUGE),
    'appsFailed': ('yarn.metrics.apps_failed', GAUGE),
    'appsKilled': ('yarn.metrics.apps_killed', GAUGE),
    'reservedMB': ('yarn.metrics.reserved_mb', GAUGE),
    'availableMB': ('yarn.metrics.available_mb', GAUGE),
    'allocatedMB': ('yarn.metrics.allocated_mb', GAUGE),
    'totalMB': ('yarn.metrics.total_mb', GAUGE),
    'reservedVirtualCores': ('yarn.metrics.reserved_virtual_cores', GAUGE),
    'availableVirtualCores': ('yarn.metrics.available_virtual_cores', GAUGE),
    'allocatedVirtualCores': ('yarn.metrics.allocated_virtual_cores', GAUGE),
    'totalVirtualCores': ('yarn.metrics.total_virtual_cores', GAUGE),
    'containersAllocated': ('yarn.metrics.containers_allocated', GAUGE),
    'containersReserved': ('yarn.metrics.containers_reserved', GAUGE),
    'containersPending': ('yarn.metrics.containers_pending', GAUGE),
    'totalNodes': ('yarn.metrics.total_nodes', GAUGE),
    'activeNodes': ('yarn.metrics.active_nodes', GAUGE),
    'lostNodes': ('yarn.metrics.lost_nodes', GAUGE),
    'unhealthyNodes': ('yarn.metrics.unhealthy_nodes', GAUGE),
    'decommissionedNodes': ('yarn.metrics.decommissioned_nodes', GAUGE),
    'rebootedNodes': ('yarn.metrics.rebooted_nodes', GAUGE),
}

# Application metrics for YARN
YARN_APP_METRICS = {
    'progress': ('yarn.apps.progress', INCREMENT),
    'startedTime': ('yarn.apps.started_time', INCREMENT),
    'finishedTime': ('yarn.apps.finished_time', INCREMENT),
    'elapsedTime': ('yarn.apps.elapsed_time', INCREMENT),
    'allocatedMB': ('yarn.apps.allocated_mb', INCREMENT),
    'allocatedVCores': ('yarn.apps.allocated_vcores', INCREMENT),
    'runningContainers': ('yarn.apps.running_containers', INCREMENT),
    'memorySeconds': ('yarn.apps.memory_seconds', INCREMENT),
    'vcoreSeconds': ('yarn.apps.vcore_seconds', INCREMENT),
}

# Node metrics for YARN
YARN_NODE_METRICS = {
    'lastHealthUpdate': ('yarn.node.last_health_update', GAUGE),
    'usedMemoryMB': ('yarn.node.used_memory_mb', GAUGE),
    'availMemoryMB': ('yarn.node.avail_memory_mb', GAUGE),
    'usedVirtualCores': ('yarn.node.used_virtual_cores', GAUGE),
    'availableVirtualCores': ('yarn.node.available_virtual_cores', GAUGE),
    'numContainers': ('yarn.node.num_containers', GAUGE),
}

# Root queue metrics for YARN
YARN_ROOT_QUEUE_METRICS = {
    'maxCapacity': ('yarn.queue.root.max_capacity', GAUGE),
    'usedCapacity': ('yarn.queue.root.used_capacity', GAUGE),
    'capacity': ('yarn.queue.root.capacity', GAUGE),
}

# Queue metrics for YARN
YARN_QUEUE_METRICS = {
    'numPendingApplications': ('yarn.queue.num_pending_applications', GAUGE),
    'userAMResourceLimit.memory': ('yarn.queue.user_am_resource_limit.memory', GAUGE),
    'userAMResourceLimit.vCores': ('yarn.queue.user_am_resource_limit.vcores', GAUGE),
    'absoluteCapacity': ('yarn.queue.absolute_capacity', GAUGE),
    'userLimitFactor': ('yarn.queue.user_limit_factor', GAUGE),
    'userLimit': ('yarn.queue.user_limit', GAUGE),
    'numApplications': ('yarn.queue.num_applications', GAUGE),
    'usedAMResource.memory': ('yarn.queue.used_am_resource.memory', GAUGE),
    'usedAMResource.vCores': ('yarn.queue.used_am_resource.vcores', GAUGE),
    'absoluteUsedCapacity': ('yarn.queue.absolute_used_capacity', GAUGE),
    'resourcesUsed.memory': ('yarn.queue.resources_used.memory', GAUGE),
    'resourcesUsed.vCores': ('yarn.queue.resources_used.vcores', GAUGE),
    'AMResourceLimit.vCores': ('yarn.queue.am_resource_limit.vcores', GAUGE),
    'AMResourceLimit.memory': ('yarn.queue.am_resource_limit.memory', GAUGE),
    'capacity': ('yarn.queue.capacity', GAUGE),
    'numActiveApplications': ('yarn.queue.num_active_applications', GAUGE),
    'absoluteMaxCapacity': ('yarn.queue.absolute_max_capacity', GAUGE),
    'usedCapacity': ('yarn.queue.used_capacity', GAUGE),
    'numContainers': ('yarn.queue.num_containers', GAUGE),
    'maxCapacity': ('yarn.queue.max_capacity', GAUGE),
    'maxApplications': ('yarn.queue.max_applications', GAUGE),
    'maxApplicationsPerUser': ('yarn.queue.max_applications_per_user', GAUGE),
}


class YarnCheck(AgentCheck):
    """
    Extract statistics from YARN's ResourceManger REST API
    """

    _ALLOWED_APPLICATION_TAGS = ['applicationTags', 'applicationType', 'name', 'queue', 'user']

    def check(self, instance):

        # Get properties from conf file
        rm_address = instance.get('resourcemanager_uri', DEFAULT_RM_URI)
        app_tags = instance.get('application_tags', {})
        queue_blacklist = instance.get('queue_blacklist', [])

        if type(app_tags) is not dict:
            self.log.error("application_tags is incorrect: {} is not a dictionary".format(app_tags))
            app_tags = {}

        filtered_app_tags = {}
        for dd_prefix, yarn_key in app_tags.iteritems():
            if yarn_key in self._ALLOWED_APPLICATION_TAGS:
                filtered_app_tags[dd_prefix] = yarn_key
        app_tags = filtered_app_tags

        # Collected by default
        app_tags['app_name'] = 'name'

        # Authenticate our connection to endpoint if required
        username = instance.get('username')
        password = instance.get('password')
        auth = None
        if username is not None and password is not None:
            auth = (username, password)

        # Option to disable verifying ssl certificate
        ssl_verify = _is_affirmative(instance.get('ssl_verify', True))

        # Get additional tags from the conf file
        custom_tags = instance.get('tags', [])
        tags = list(set(custom_tags))

        # Get the cluster name from the conf file
        cluster_name = instance.get('cluster_name')
        if cluster_name is None:
            self.warning(
                "The cluster_name must be specified in the instance configuration, "
                "defaulting to '{}'".format(DEFAULT_CLUSTER_NAME)
            )
            cluster_name = DEFAULT_CLUSTER_NAME

        tags.append('cluster_name:{}'.format(cluster_name))

        # Get metrics from the Resource Manager
        self._yarn_cluster_metrics(rm_address, auth, ssl_verify, tags)
        if _is_affirmative(instance.get('collect_app_metrics', DEFAULT_COLLECT_APP_METRICS)):
            self._yarn_app_metrics(rm_address, auth, ssl_verify, app_tags, tags)
        self._yarn_node_metrics(rm_address, auth, ssl_verify, tags)
        self._yarn_scheduler_metrics(rm_address, auth, ssl_verify, tags, queue_blacklist)

    def _yarn_cluster_metrics(self, rm_address, auth, ssl_verify, addl_tags):
        """
        Get metrics related to YARN cluster
        """
        metrics_json = self._rest_request_to_json(rm_address, auth, ssl_verify, YARN_CLUSTER_METRICS_PATH, addl_tags)

        if metrics_json:

            yarn_metrics = metrics_json[YARN_CLUSTER_METRICS_ELEMENT]

            if yarn_metrics is not None:
                self._set_yarn_metrics_from_json(addl_tags, yarn_metrics, YARN_CLUSTER_METRICS)

    def _yarn_app_metrics(self, rm_address, auth, ssl_verify, app_tags, addl_tags):
        """
        Get metrics for running applications
        """
        metrics_json = self._rest_request_to_json(
            rm_address, auth, ssl_verify, YARN_APPS_PATH, addl_tags, states=YARN_APPLICATION_STATES
        )

        if metrics_json and metrics_json['apps'] is not None and metrics_json['apps']['app'] is not None:

            for app_json in metrics_json['apps']['app']:

                tags = []
                for dd_tag, yarn_key in app_tags.iteritems():
                    try:
                        val = app_json[yarn_key]
                        if val:
                            tags.append('{tag}:{value}'.format(tag=dd_tag, value=val))
                    except KeyError:
                        self.log.error("Invalid value {} for application_tag".format(yarn_key))

                tags.extend(addl_tags)

                self._set_yarn_metrics_from_json(tags, app_json, YARN_APP_METRICS)

    def _yarn_node_metrics(self, rm_address, auth, ssl_verify, addl_tags):
        """
        Get metrics related to YARN nodes
        """
        metrics_json = self._rest_request_to_json(rm_address, auth, ssl_verify, YARN_NODES_PATH, addl_tags)

        if metrics_json and metrics_json['nodes'] is not None and metrics_json['nodes']['node'] is not None:

            for node_json in metrics_json['nodes']['node']:
                node_id = node_json['id']

                tags = ['node_id:{}'.format(str(node_id))]
                tags.extend(addl_tags)

                self._set_yarn_metrics_from_json(tags, node_json, YARN_NODE_METRICS)

    def _yarn_scheduler_metrics(self, rm_address, auth, ssl_verify, addl_tags, queue_blacklist):
        """
        Get metrics from YARN scheduler
        """
        metrics_json = self._rest_request_to_json(rm_address, auth, ssl_verify, YARN_SCHEDULER_PATH, addl_tags)

        try:
            metrics_json = metrics_json['scheduler']['schedulerInfo']

            if metrics_json['type'] == 'capacityScheduler':
                self._yarn_capacity_scheduler_metrics(metrics_json, addl_tags, queue_blacklist)

        except KeyError:
            pass

    def _yarn_capacity_scheduler_metrics(self, metrics_json, addl_tags, queue_blacklist):
        """
        Get metrics from YARN scheduler if it's type is capacityScheduler
        """
        tags = ['queue_name:{}'.format(metrics_json['queueName'])]
        tags.extend(addl_tags)

        self._set_yarn_metrics_from_json(tags, metrics_json, YARN_ROOT_QUEUE_METRICS)

        if metrics_json['queues'] is not None and metrics_json['queues']['queue'] is not None:

            queues_count = 0
            for queue_json in metrics_json['queues']['queue']:
                queue_name = queue_json['queueName']

                if queue_name in queue_blacklist:
                    self.log.debug('Queue "{}" is blacklisted. Ignoring it'.format(queue_name))
                    continue

                queues_count += 1
                if queues_count > MAX_DETAILED_QUEUES:
                    self.warning(
                        "Found more than 100 queues, will only send metrics on first 100 queues. "
                        "Please filter the queues with the check's `queue_blacklist` parameter"
                    )
                    break

                tags = ['queue_name:{}'.format(str(queue_name))]
                tags.extend(addl_tags)

                self._set_yarn_metrics_from_json(tags, queue_json, YARN_QUEUE_METRICS)

    def _set_yarn_metrics_from_json(self, tags, metrics_json, yarn_metrics):
        """
        Parse the JSON response and set the metrics
        """
        for dict_path, metric in yarn_metrics.iteritems():
            metric_name, metric_type = metric

            metric_value = self._get_value_from_json(dict_path, metrics_json)

            if metric_value is not None:
                self._set_metric(metric_name, metric_type, metric_value, tags)

    def _get_value_from_json(self, dict_path, metrics_json):
        """
        Get a value from a dictionary under N keys, represented as str("key1.key2...key{n}")
        """
        for key in dict_path.split('.'):
            if key in metrics_json:
                metrics_json = metrics_json.get(key)
            else:
                return None
        return metrics_json

    def _set_metric(self, metric_name, metric_type, value, tags=None, device_name=None):
        """
        Set a metric
        """
        if metric_type == GAUGE:
            self.gauge(metric_name, value, tags=tags, device_name=device_name)
        elif metric_type == INCREMENT:
            self.increment(metric_name, value, tags=tags, device_name=device_name)
        else:
            self.log.error('Metric type "{}" unknown'.format(metric_type))

    def _rest_request_to_json(self, address, auth, ssl_verify, object_path, tags, *args, **kwargs):
        """
        Query the given URL and return the JSON response
        """
        response_json = None

        service_check_tags = ['url:{}'.format(self._get_url_base(address))] + tags
        service_check_tags = list(set(service_check_tags))

        url = address

        if object_path:
            url = self._join_url_dir(url, object_path)

        # Add args to the url
        if args:
            for directory in args:
                url = self._join_url_dir(url, directory)

        self.log.debug('Attempting to connect to "{}"'.format(url))

        # Add kwargs as arguments
        if kwargs:
            query = '&'.join(['{}={}'.format(key, value) for key, value in kwargs.iteritems()])
            url = urljoin(url, '?' + query)

        try:
            response = requests.get(url, auth=auth, verify=ssl_verify, timeout=self.default_integration_http_timeout)
            response.raise_for_status()
            response_json = response.json()

        except Timeout as e:
            self.service_check(
                SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                tags=service_check_tags,
                message="Request timeout: {}, {}".format(url, e),
            )
            raise

        except (HTTPError, InvalidURL, ConnectionError, SSLError) as e:
            self.service_check(
                SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                tags=service_check_tags,
                message="Request failed: {}, {}".format(url, e),
            )
            raise

        except ValueError as e:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=service_check_tags, message=str(e))
            raise

        else:
            self.service_check(
                SERVICE_CHECK_NAME,
                AgentCheck.OK,
                tags=service_check_tags,
                message="Connection to {} was successful".format(url),
            )

        return response_json

    def _join_url_dir(self, url, *args):
        """
        Join a URL with multiple directories
        """
        for path in args:
            url = url.rstrip('/') + '/'
            url = urljoin(url, path.lstrip('/'))

        return url

    def _get_url_base(self, url):
        """
        Return the base of a URL
        """
        s = urlsplit(url)
        return urlunsplit([s.scheme, s.netloc, '', '', ''])
