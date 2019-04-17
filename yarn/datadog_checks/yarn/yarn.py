# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import requests
import requests_kerberos
from requests.exceptions import ConnectionError, HTTPError, InvalidURL, SSLError, Timeout
from six import iteritems
from six.moves.urllib.parse import urljoin, urlsplit, urlunsplit

from datadog_checks.base import AgentCheck, is_affirmative

KERBEROS_STRATEGIES = {
    'required': requests_kerberos.REQUIRED,
    'optional': requests_kerberos.OPTIONAL,
    'disabled': requests_kerberos.DISABLED,
}


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
        for dd_prefix, yarn_key in iteritems(app_tags):
            if yarn_key in self._ALLOWED_APPLICATION_TAGS:
                filtered_app_tags[dd_prefix] = yarn_key
        app_tags = filtered_app_tags

        # Collected by default
        app_tags['app_name'] = 'name'

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
        self._yarn_cluster_metrics(rm_address, instance, tags)
        if is_affirmative(instance.get('collect_app_metrics', DEFAULT_COLLECT_APP_METRICS)):
            self._yarn_app_metrics(rm_address, instance, app_tags, tags)
        self._yarn_node_metrics(rm_address, instance, tags)
        self._yarn_scheduler_metrics(rm_address, instance, tags, queue_blacklist)

    def _yarn_cluster_metrics(self, rm_address, instance, addl_tags):
        """
        Get metrics related to YARN cluster
        """
        metrics_json = self._rest_request_to_json(rm_address, instance, YARN_CLUSTER_METRICS_PATH, addl_tags)

        if metrics_json:

            yarn_metrics = metrics_json[YARN_CLUSTER_METRICS_ELEMENT]

            if yarn_metrics is not None:
                self._set_yarn_metrics_from_json(addl_tags, yarn_metrics, YARN_CLUSTER_METRICS)

    def _yarn_app_metrics(self, rm_address, instance, app_tags, addl_tags):
        """
        Get metrics for running applications
        """
        metrics_json = self._rest_request_to_json(
            rm_address, instance, YARN_APPS_PATH, addl_tags, states=YARN_APPLICATION_STATES
        )

        if metrics_json and metrics_json['apps'] is not None and metrics_json['apps']['app'] is not None:

            for app_json in metrics_json['apps']['app']:

                tags = []
                for dd_tag, yarn_key in iteritems(app_tags):
                    try:
                        val = app_json[yarn_key]
                        if val:
                            tags.append('{tag}:{value}'.format(tag=dd_tag, value=val))
                    except KeyError:
                        self.log.error("Invalid value {} for application_tag".format(yarn_key))

                tags.extend(addl_tags)

                self._set_yarn_metrics_from_json(tags, app_json, YARN_APP_METRICS)

    def _yarn_node_metrics(self, rm_address, instance, addl_tags):
        """
        Get metrics related to YARN nodes
        """
        metrics_json = self._rest_request_to_json(rm_address, instance, YARN_NODES_PATH, addl_tags)

        if metrics_json and metrics_json['nodes'] is not None and metrics_json['nodes']['node'] is not None:

            for node_json in metrics_json['nodes']['node']:
                node_id = node_json['id']

                tags = ['node_id:{}'.format(str(node_id))]
                tags.extend(addl_tags)

                self._set_yarn_metrics_from_json(tags, node_json, YARN_NODE_METRICS)

    def _yarn_scheduler_metrics(self, rm_address, instance, addl_tags, queue_blacklist):
        """
        Get metrics from YARN scheduler
        """
        metrics_json = self._rest_request_to_json(rm_address, instance, YARN_SCHEDULER_PATH, addl_tags)

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
        for dict_path, metric in iteritems(yarn_metrics):
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

    def _rest_request_to_json(self, url, instance, object_path, tags, *args, **kwargs):
        """
        Query the given URL and return the JSON response
        """
        service_check_tags = ['url:{}'.format(self._get_url_base(url))] + tags
        service_check_tags = list(set(service_check_tags))

        if object_path:
            url = self._join_url_dir(url, object_path)

        # Add args to the url
        if args:
            for directory in args:
                url = self._join_url_dir(url, directory)

        auth = None

        # Authenticate our connection to JMX endpoint if required
        kerberos = instance.get('kerberos')
        username = instance.get('username')
        password = instance.get('password')
        if username is not None and password is not None:
            auth = (username, password)
        elif kerberos is not None:
            if kerberos not in KERBEROS_STRATEGIES:
                raise Exception('Invalid Kerberos strategy `{}`'.format(kerberos))

            auth = requests_kerberos.HTTPKerberosAuth(
                mutual_authentication=KERBEROS_STRATEGIES[kerberos],
                delegate=is_affirmative(instance.get('kerberos_delegate', False)),
                force_preemptive=is_affirmative(instance.get('kerberos_force_initiate', False)),
                hostname_override=instance.get('kerberos_hostname'),
                principal=instance.get('kerberos_principal'),
            )

        ssl_verify = is_affirmative(instance.get('ssl_verify', True))

        old_keytab_path = None
        if 'kerberos_keytab' in instance:
            old_keytab_path = os.getenv('KRB5_CLIENT_KTNAME')
            os.environ['KRB5_CLIENT_KTNAME'] = instance['kerberos_keytab']

        self.log.debug('Attempting to connect to "{}"'.format(url))

        # Add kwargs as arguments
        if kwargs:
            query = '&'.join(['{}={}'.format(key, value) for key, value in iteritems(kwargs)])
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

        finally:
            if old_keytab_path is not None:
                os.environ['KRB5_CLIENT_KTNAME'] = old_keytab_path

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
