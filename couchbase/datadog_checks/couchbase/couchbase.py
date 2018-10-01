# (C) Datadog, Inc. 2018
# (C) Justin Slattery <Justin.Slattery@fzysqr.com> 2013
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# stdlib
import time
import re
from collections import defaultdict

# 3rd party
import requests

# project
from datadog_checks.base.checks import AgentCheck
from datadog_checks.base.utils.headers import headers
from datadog_checks.base.utils.containers import hash_mutable

# Constants
COUCHBASE_STATS_PATH = '/pools/default'
COUCHBASE_VITALS_PATH = '/admin/vitals'
DEFAULT_TIMEOUT = 10


class Couchbase(AgentCheck):
    """
    Extracts stats from Couchbase via its REST API
    http://docs.couchbase.com/couchbase-manual-2.0/#using-the-rest-api
    """

    # Service Checks
    SERVICE_CHECK_NAME = 'couchbase.can_connect'
    NODE_CLUSTER_SERVICE_CHECK_NAME = 'couchbase.by_node.cluster_membership'
    NODE_HEALTH_SERVICE_CHECK_NAME = 'couchbase.by_node.health'

    NODE_MEMBERSHIP_TRANSLATION = {
        'active': AgentCheck.OK,
        'inactiveAdded': AgentCheck.WARNING,
        'activeFailed': AgentCheck.CRITICAL,
        None: AgentCheck.UNKNOWN,
    }

    NODE_HEALTH_TRANSLATION = {
        'healthy': AgentCheck.OK,
        'warmup': AgentCheck.OK,
        'unhealthy': AgentCheck.CRITICAL,
        None: AgentCheck.UNKNOWN
    }

    # Events
    SOURCE_TYPE_NAME = 'couchbase'

    # Selected metrics to send amongst all the bucket stats, after name normalization
    BUCKET_STATS = set([
        "avg_bg_wait_time",
        "avg_disk_commit_time",
        "avg_disk_update_time",
        "bg_wait_total",
        "bytes_read",
        "bytes_written",
        "cas_badval",
        "cas_hits",
        "cas_misses",
        "cmd_get",
        "cmd_set",
        "couch_docs_actual_disk_size",
        "couch_docs_data_size",
        "couch_docs_disk_size",
        "couch_docs_fragmentation",
        "couch_spatial_data_size",
        "couch_spatial_disk_size",
        "couch_spatial_ops",
        "couch_total_disk_size",
        "couch_views_data_size",
        "couch_views_disk_size",
        "couch_views_fragmentation",
        "couch_views_ops",
        "cpu_idle_ms",
        "cpu_utilization_rate",
        "curr_connections",
        "curr_items_tot",
        "curr_items",
        "decr_hits",
        "decr_misses",
        "delete_hits",
        "delete_misses",
        "disk_commit_count",
        "disk_update_count",
        "disk_write_queue",
        "ep_bg_fetched",
        "ep_cache_miss_rate",
        "ep_cache_miss_ratio",
        "ep_dcp_fts_backoff",
        "ep_dcp_fts_count",
        "ep_dcp_fts_items_remaining",
        "ep_dcp_fts_items_sent",
        "ep_dcp_fts_producer_count",
        "ep_dcp_fts_total_bytes",
        "ep_dcp_2i_backoff",
        "ep_dcp_2i_count",
        "ep_dcp_2i_items_remaining",
        "ep_dcp_2i_items_sent",
        "ep_dcp_2i_producer_count",
        "ep_dcp_2i_total_bytes",
        "ep_dcp_other_backoff",
        "ep_dcp_other_count",
        "ep_dcp_other_items_remaining",
        "ep_dcp_other_items_sent",
        "ep_dcp_other_producer_count",
        "ep_dcp_other_total_bytes",
        "ep_dcp_replica_backoff",
        "ep_dcp_replica_count",
        "ep_dcp_replica_items_remaining",
        "ep_dcp_replica_items_sent",
        "ep_dcp_replica_producer_count",
        "ep_dcp_replica_total_bytes",
        "ep_dcp_views_backoff",
        "ep_dcp_views_count",
        "ep_dcp_views_items_remaining",
        "ep_dcp_views_items_sent",
        "ep_dcp_views_producer_count",
        "ep_dcp_views_total_bytes",
        "ep_dcp_xdcr_backoff",
        "ep_dcp_xdcr_count",
        "ep_dcp_xdcr_items_remaining",
        "ep_dcp_xdcr_items_sent",
        "ep_dcp_xdcr_producer_count",
        "ep_dcp_xdcr_total_bytes",
        "ep_diskqueue_drain",
        "ep_diskqueue_fill",
        "ep_diskqueue_items",
        "ep_flusher_todo",
        "ep_item_commit_failed",
        "ep_kv_size",
        "ep_max_size",
        "ep_mem_high_wat",
        "ep_mem_low_wat",
        "ep_meta_data_memory",
        "ep_num_non_resident",
        "ep_num_ops_del_meta",
        "ep_num_ops_del_ret_meta",
        "ep_num_ops_get_meta",
        "ep_num_ops_set_meta",
        "ep_num_ops_set_ret_meta",
        "ep_num_value_ejects",
        "ep_oom_errors",
        "ep_ops_create",
        "ep_ops_update",
        "ep_overhead",
        "ep_queue_size",
        "ep_resident_items_rate",
        "ep_tap_replica_queue_drain",
        "ep_tap_total_queue_drain",
        "ep_tap_total_queue_fill",
        "ep_tap_total_total_backlog_size",
        "ep_tmp_oom_errors",
        "ep_vb_total",
        "evictions",
        "get_hits",
        "get_misses",
        "hibernated_requests",
        "hibernated_waked",
        "hit_ratio",
        "incr_hits",
        "incr_misses",
        "mem_actual_free",
        "mem_actual_used",
        "mem_free",
        "mem_total",
        "mem_used",
        "mem_used_sys",
        "misses",
        "ops",
        "page_faults",
        "replication_docs_rep_queue",
        "replication_meta_latency_aggr",
        "rest_requests",
        "swap_total",
        "swap_used",
        "vb_active_eject",
        "vb_active_itm_memory",
        "vb_active_meta_data_memory",
        "vb_active_num_non_resident",
        "vb_active_num",
        "vb_active_ops_create",
        "vb_active_ops_update",
        "vb_active_queue_age",
        "vb_active_queue_drain",
        "vb_active_queue_fill",
        "vb_active_queue_size",
        "vb_active_resident_items_ratio",
        "vb_avg_active_queue_age",
        "vb_avg_pending_queue_age",
        "vb_avg_replica_queue_age",
        "vb_avg_total_queue_age",
        "vb_pending_curr_items",
        "vb_pending_eject",
        "vb_pending_itm_memory",
        "vb_pending_meta_data_memory",
        "vb_pending_num_non_resident",
        "vb_pending_num",
        "vb_pending_ops_create",
        "vb_pending_ops_update",
        "vb_pending_queue_age",
        "vb_pending_queue_drain",
        "vb_pending_queue_fill",
        "vb_pending_queue_size",
        "vb_pending_resident_items_ratio",
        "vb_replica_curr_items",
        "vb_replica_eject",
        "vb_replica_itm_memory",
        "vb_replica_meta_data_memory",
        "vb_replica_num_non_resident",
        "vb_replica_num",
        "vb_replica_ops_create",
        "vb_replica_ops_update",
        "vb_replica_queue_age",
        "vb_replica_queue_drain",
        "vb_replica_queue_fill",
        "vb_replica_queue_size",
        "vb_replica_resident_items_ratio",
        "vb_total_queue_age",
        "xdc_ops",
    ])
    # Selected metrics of the query monitoring API
    # See https://developer.couchbase.com/documentation/server/4.5/tools/query-monitoring.html
    QUERY_STATS = set([
        'cores',
        'cpu_sys_percent',
        'cpu_user_percent',
        'gc_num',
        'gc_pause_percent',
        'gc_pause_time',
        'memory_system',
        'memory_total',
        'memory_usage',
        'request_active_count',
        'request_completed_count',
        'request_per_sec_15min',
        'request_per_sec_1min',
        'request_per_sec_5min',
        'request_prepared_percent',
        'request_time_80percentile',
        'request_time_95percentile',
        'request_time_99percentile',
        'request_time_mean',
        'request_time_median',
        'total_threads',
    ])

    TO_SECONDS = {
        'ns': 1e9,
        'us': 1e6,
        'ms': 1e3,
        's': 1,
    }

    seconds_value_pattern = re.compile('(\d+(\.\d+)?)(\D+)')

    class CouchbaseInstanceState(object):
        def __init__(self):
            self.previous_status = None

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

        # Keep track of all instances
        self._instance_states = defaultdict(lambda: self.CouchbaseInstanceState())

    def _create_metrics(self, data, instance_state, server, tags=None):
        # Get storage metrics
        storage_totals = data['stats']['storageTotals']
        for key, storage_type in storage_totals.items():
            for metric_name, val in storage_type.items():
                if val is not None:
                    metric_name = 'couchbase.{}.{}'.format(key, self.camel_case_to_joined_lower(metric_name))
                    self.gauge(metric_name, val, tags=tags)

        # Get bucket metrics
        for bucket_name, bucket_stats in data['buckets'].items():
            metric_tags = list(tags)
            metric_tags.append('bucket:{}'.format(bucket_name))
            for metric_name, val in bucket_stats.items():
                if val is not None:
                    norm_metric_name = self.camel_case_to_joined_lower(metric_name)
                    if norm_metric_name in self.BUCKET_STATS:
                        full_metric_name = 'couchbase.by_bucket.{}'.format(norm_metric_name)
                        self.gauge(full_metric_name, val[0], tags=metric_tags, device_name=bucket_name)

        # Get node metrics
        for node_name, node_stats in data['nodes'].items():
            metric_tags = list(tags)
            metric_tags.append('node:{}'.format(node_name))
            for metric_name, val in node_stats['interestingStats'].items():
                if val is not None:
                    metric_name = 'couchbase.by_node.{}'.format(self.camel_case_to_joined_lower(metric_name))
                    self.gauge(metric_name, val, tags=metric_tags, device_name=node_name)

            # Get cluster health data
            self._process_cluster_health_data(node_name, node_stats, tags)

        # Get query metrics
        for metric_name, val in data['query'].items():
            if val is not None:
                norm_metric_name = self.camel_case_to_joined_lower(metric_name)
                if norm_metric_name in self.QUERY_STATS:
                    # for query times, the unit is part of the value, we need to extract it
                    if isinstance(val, basestring):
                        val = self.extract_seconds_value(val)

                    full_metric_name = 'couchbase.query.{}'.format(self.camel_case_to_joined_lower(norm_metric_name))
                    self.gauge(full_metric_name, val, tags=tags)

        # Get tasks, we currently only care about 'rebalance' tasks
        rebalance_status, rebalance_msg = data['tasks'].get('rebalance', (None, None))

        # Only fire an event when the state has changed
        if rebalance_status is not None and instance_state.previous_status != rebalance_status:
            rebalance_event = None

            # If we get an error, we create an error event with the msg we receive
            if rebalance_status == 'error':
                msg_title = 'Encountered an error while rebalancing'
                msg = rebalance_msg

                rebalance_event = self._create_event('error', msg_title, msg, server, tags=tags)

            # We only want to fire a 'completion' of a rebalance so make sure we're not firing an event on first run
            elif rebalance_status == 'notRunning' and instance_state.previous_status is not None:
                msg_title = 'Stopped rebalancing'
                msg = 'stopped rebalancing.'
                rebalance_event = self._create_event('info', msg_title, msg, server, tags=tags)

            # If a rebalance task is running, fire an event. This will also fire an event if a rebalance task was
            #   already running when the check first runs.
            elif rebalance_status == 'gracefulFailover':
                msg_title = 'Failing over gracefully'
                msg = 'is failing over gracefully.'
                rebalance_event = self._create_event('info', msg_title, msg, server, tags=tags)
            elif rebalance_status == 'rebalance':
                msg_title = 'Rebalancing'
                msg = 'is rebalancing.'
                rebalance_event = self._create_event('info', msg_title, msg, server, tags=tags)

            # Send the event
            if rebalance_event is not None:
                self.event(rebalance_event)

            # Update the status of this instance
            instance_state.previous_status = rebalance_status

    def _process_cluster_health_data(self, node_name, node_stats, tags):
        """
        Process and send cluster health data (i.e. cluster membership status and node health
        """

        # Tags for service check
        cluster_health_tags = list(tags) + ['node:{}'.format(node_name)]

        # Get the membership status of the node
        cluster_membership = node_stats.get('clusterMembership', None)
        membership_status = self.NODE_MEMBERSHIP_TRANSLATION.get(cluster_membership, AgentCheck.UNKNOWN)
        self.service_check(self.NODE_CLUSTER_SERVICE_CHECK_NAME, membership_status, tags=cluster_health_tags)

        # Get the health status of the node
        health = node_stats.get('status', None)
        health_status = self.NODE_HEALTH_TRANSLATION.get(health, AgentCheck.UNKNOWN)
        self.service_check(self.NODE_HEALTH_SERVICE_CHECK_NAME, health_status, tags=cluster_health_tags)

    def _create_event(self, alert_type, msg_title, msg, server, tags=None):
        """
        Create an event object
        """
        msg_title = 'Couchbase {}: {}'.format(server, msg_title)
        msg = 'Couchbase instance {} {}'.format(server, msg)

        return {
            'timestamp': int(time.time()),
            'event_type': 'couchbase_rebalance',
            'msg_text': msg,
            'msg_title': msg_title,
            'alert_type': alert_type,
            'source_type_name': self.SOURCE_TYPE_NAME,
            'aggregation_key': server,
            'tags': tags
        }

    def _get_stats(self, url, instance):
        """
        Hit a given URL and return the parsed json.
        """

        self.log.debug('Fetching Couchbase stats at url: {}'.format(url))

        timeout = float(instance.get('timeout', DEFAULT_TIMEOUT))

        auth = None
        if 'user' in instance and 'password' in instance:
            auth = (instance['user'], instance['password'])

        r = requests.get(url, auth=auth, headers=headers(self.agentConfig), timeout=timeout)
        r.raise_for_status()
        return r.json()

    def check(self, instance):
        instance_state = self._instance_states[hash_mutable(instance)]

        server = instance.get('server', None)
        if server is None:
            raise Exception("The server must be specified")
        tags = instance.get('tags', [])
        # Clean up tags in case there was a None entry in the instance
        # e.g. if the yaml contains tags: but no actual tags
        if tags is None:
            tags = []
        else:
            tags = list(set(tags))
        tags.append('instance:{}'.format(server))
        data = self.get_data(server, instance)
        self._create_metrics(data, instance_state, server, tags=list(set(tags)))

    def get_data(self, server, instance):
        # The dictionary to be returned.
        couchbase = {
            'stats': None,
            'buckets': {},
            'nodes': {},
            'query': {},
            'tasks': {}
        }

        # build couchbase stats entry point
        url = '{}{}'.format(server, COUCHBASE_STATS_PATH)

        # Fetch initial stats and capture a service check based on response.
        service_check_tags = instance.get('tags', [])
        if service_check_tags is None:
            service_check_tags = []
        else:
            service_check_tags = list(set(service_check_tags))
        service_check_tags.append('instance:{}'.format(server))
        try:
            overall_stats = self._get_stats(url, instance)
            # No overall stats? bail out now
            if overall_stats is None:
                raise Exception("No data returned from couchbase endpoint: {}".format(url))
        except requests.exceptions.HTTPError as e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                               tags=service_check_tags, message=str(e.message))
            raise
        except Exception as e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=service_check_tags, message=str(e))
            raise
        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=service_check_tags)

        couchbase['stats'] = overall_stats

        nodes = overall_stats['nodes']

        # Next, get all the nodes
        if nodes is not None:
            for node in nodes:
                couchbase['nodes'][node['hostname']] = node

        # Next, get all buckets .
        endpoint = overall_stats['buckets']['uri']

        url = '{}{}'.format(server, endpoint)
        buckets = self._get_stats(url, instance)

        if buckets is not None:
            for bucket in buckets:
                bucket_name = bucket['name']

                # Fetch URI for the stats bucket
                endpoint = bucket['stats']['uri']
                url = '{}{}'.format(server, endpoint)

                try:
                    bucket_stats = self._get_stats(url, instance)
                except requests.exceptions.HTTPError:
                    url_backup = '{}/pools/nodes/buckets/{}/stats'.format(server, bucket_name)
                    bucket_stats = self._get_stats(url_backup, instance)

                bucket_samples = bucket_stats['op']['samples']
                if bucket_samples is not None:
                    couchbase['buckets'][bucket['name']] = bucket_samples

        # Next, get the query monitoring data
        query_monitoring_url = instance.get('query_monitoring_url', None)
        if query_monitoring_url is not None:
            try:
                url = '{}{}'.format(query_monitoring_url, COUCHBASE_VITALS_PATH)
                query = self._get_stats(url, instance)
                if query is not None:
                    couchbase['query'] = query
            except requests.exceptions.HTTPError:
                self.log.error("Error accessing the endpoint {}, make sure you're running at least "
                               "couchbase 4.5 to collect the query monitoring metrics".format(url))

        # Next, get all the tasks
        tasks_url = '{}{}/tasks'.format(server, COUCHBASE_STATS_PATH)
        try:
            tasks = self._get_stats(tasks_url, instance)
            for task in tasks:
                task_type = task['type']

                # We only care about rebalance statuses
                if task_type != 'rebalance':
                    continue

                # Format the status so it's easier to understand
                if 'errorMessage' in task:
                    couchbase['tasks'][task_type] = ('error', task['errorMessage'])
                elif task['status'] == 'notRunning':
                    couchbase['tasks'][task_type] = (task['status'], None)

                # If the status is 'running', we want to differentiate between a regular rebalance and a graceful
                #   failover rebalance, so we use the subtype
                elif task['status'] == 'running':
                    couchbase['tasks'][task_type] = (task['subtype'], None)

                # Should only be 1 rebalance
                break

        except requests.exceptions.HTTPError:
            self.log.error("Error accessing the endpoint {}".format(url))

        return couchbase

    # Takes a camelCased variable and returns a joined_lower equivalent.
    # Returns input if non-camelCase variable is detected.
    def camel_case_to_joined_lower(self, variable):
        # replace non-word with _
        converted_variable = re.sub('\W+', '_', variable)

        # insert _ in front of capital letters and lowercase the string
        converted_variable = re.sub('([A-Z])', '_\g<1>', converted_variable).lower()

        # remove duplicate _
        converted_variable = re.sub('_+', '_', converted_variable)

        # handle special case of starting/ending underscores
        converted_variable = re.sub('^_|_$', '', converted_variable)

        return converted_variable

    # Takes a string with a time and a unit (e.g '3.45ms') and returns the value in seconds
    def extract_seconds_value(self, value):

        # When couchbase is set up, most of values are equal to 0 and are exposed as "0" and not "0s"
        # This statement is preventing values to be searched by the pattern (and break things)
        if value == '0':
            return 0

        match = self.seconds_value_pattern.search(value)

        val, unit = match.group(1, 3)
        # They use the 'micro' symbol for microseconds so there is an encoding problem
        # so let's assume it's microseconds if we don't find the key in unit
        if unit not in self.TO_SECONDS:
            unit = 'us'

        return float(val) / self.TO_SECONDS[unit]
