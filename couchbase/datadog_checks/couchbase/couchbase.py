# (C) Datadog, Inc. 2018-present
# (C) Justin Slattery <Justin.Slattery@fzysqr.com> 2013
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import division

import re
import time

import requests
from six import string_types
from six.moves.urllib.parse import urljoin

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.couchbase.couchbase_consts import (
    BUCKET_STATS,
    COUCHBASE_STATS_PATH,
    COUCHBASE_VITALS_PATH,
    INDEX_STATS_COUNT_METRICS,
    INDEX_STATS_METRICS_PATH,
    INDEX_STATS_SERVICE_CHECK_NAME,
    INDEXER_STATE_MAP,
    NODE_CLUSTER_SERVICE_CHECK_NAME,
    NODE_HEALTH_SERVICE_CHECK_NAME,
    NODE_HEALTH_TRANSLATION,
    NODE_MEMBERSHIP_TRANSLATION,
    QUERY_STATS,
    SECONDS_VALUE_PATTERN,
    SERVICE_CHECK_NAME,
    SG_METRICS_PATH,
    SG_SERVICE_CHECK_NAME,
    SOURCE_TYPE_NAME,
    SYNC_GATEWAY_COUNT_METRICS,
    TO_SECONDS,
)


class Couchbase(AgentCheck):
    """
    Extracts stats from Couchbase via its REST API
    http://docs.couchbase.com/couchbase-manual-2.0/#using-the-rest-api
    """

    HTTP_CONFIG_REMAPPER = {'user': {'name': 'username'}, 'ssl_verify': {'name': 'tls_verify'}}

    def __init__(self, name, init_config, instances):
        super(Couchbase, self).__init__(name, init_config, instances)

        self._sync_gateway_url = self.instance.get('sync_gateway_url', None)
        self._index_stats_url = self.instance.get('index_stats_url')
        self._server = self.instance.get('server', None)
        if self._server is None:
            raise ConfigurationError("The server must be specified")
        self._tags = list(set(self.instance.get('tags', [])))
        self._tags.append('instance:{}'.format(self._server))

        self._previous_status = None
        self._version = None

    def _create_metrics(self, data):
        # Get storage metrics
        storage_totals = data['stats']['storageTotals']
        for key, storage_type in storage_totals.items():
            for metric_name, val in storage_type.items():
                if val is not None:
                    metric_name = 'couchbase.{}.{}'.format(key, self.camel_case_to_joined_lower(metric_name))
                    self.gauge(metric_name, val, tags=self._tags)

        # Get bucket metrics
        for bucket_name, bucket_stats in data['buckets'].items():
            metric_tags = ['bucket:{}'.format(bucket_name), 'device:{}'.format(bucket_name)]
            metric_tags.extend(self._tags)
            for metric_name, val in bucket_stats.items():
                if val is not None:
                    norm_metric_name = self.camel_case_to_joined_lower(metric_name)
                    if norm_metric_name in BUCKET_STATS:
                        full_metric_name = 'couchbase.by_bucket.{}'.format(norm_metric_name)
                        self.gauge(full_metric_name, val[0], tags=metric_tags)

        # Get node metrics
        for node_name, node_stats in data['nodes'].items():
            metric_tags = ['node:{}'.format(node_name), 'device:{}'.format(node_name)]
            metric_tags.extend(self._tags)
            for metric_name, val in node_stats['interestingStats'].items():
                if val is not None:
                    metric_name = 'couchbase.by_node.{}'.format(self.camel_case_to_joined_lower(metric_name))
                    self.gauge(metric_name, val, tags=metric_tags)

            # Get cluster health data
            self._process_cluster_health_data(node_name, node_stats)

        # Get query metrics
        for metric_name, val in data['query'].items():
            if val is not None:
                norm_metric_name = self.camel_case_to_joined_lower(metric_name)
                if norm_metric_name in QUERY_STATS:
                    # for query times, the unit is part of the value, we need to extract it
                    if isinstance(val, string_types):
                        val = self.extract_seconds_value(val)

                    full_metric_name = 'couchbase.query.{}'.format(self.camel_case_to_joined_lower(norm_metric_name))
                    self.gauge(full_metric_name, val, tags=self._tags)

        # Get tasks, we currently only care about 'rebalance' tasks
        rebalance_status, rebalance_msg = data['tasks'].get('rebalance', (None, None))

        # Only fire an event when the state has changed
        if rebalance_status is not None and self._previous_status != rebalance_status:
            rebalance_event = None

            # If we get an error, we create an error event with the msg we receive
            if rebalance_status == 'error':
                msg_title = 'Encountered an error while rebalancing'
                msg = rebalance_msg

                rebalance_event = self._create_event('error', msg_title, msg)

            # We only want to fire a 'completion' of a rebalance so make sure we're not firing an event on first run
            elif rebalance_status == 'notRunning' and self._previous_status is not None:
                msg_title = 'Stopped rebalancing'
                msg = 'stopped rebalancing.'
                rebalance_event = self._create_event('info', msg_title, msg)

            # If a rebalance task is running, fire an event. This will also fire an event if a rebalance task was
            #   already running when the check first runs.
            elif rebalance_status == 'gracefulFailover':
                msg_title = 'Failing over gracefully'
                msg = 'is failing over gracefully.'
                rebalance_event = self._create_event('info', msg_title, msg)
            elif rebalance_status == 'rebalance':
                msg_title = 'Rebalancing'
                msg = 'is rebalancing.'
                rebalance_event = self._create_event('info', msg_title, msg)

            # Send the event
            if rebalance_event is not None:
                self.event(rebalance_event)

            # Update the status of this instance
            self._previous_status = rebalance_status

    def _process_cluster_health_data(self, node_name, node_stats):
        """
        Process and send cluster health data (i.e. cluster membership status and node health
        """

        # Tags for service check
        cluster_health_tags = list(self._tags) + ['node:{}'.format(node_name)]

        # Get the membership status of the node
        cluster_membership = node_stats.get('clusterMembership', None)
        membership_status = NODE_MEMBERSHIP_TRANSLATION.get(cluster_membership, AgentCheck.UNKNOWN)
        self.service_check(NODE_CLUSTER_SERVICE_CHECK_NAME, membership_status, tags=cluster_health_tags)

        # Get the health status of the node
        health = node_stats.get('status', None)
        health_status = NODE_HEALTH_TRANSLATION.get(health, AgentCheck.UNKNOWN)
        self.service_check(NODE_HEALTH_SERVICE_CHECK_NAME, health_status, tags=cluster_health_tags)

    def _create_event(self, alert_type, msg_title, msg):
        """
        Create an event object
        """
        msg_title = 'Couchbase {}: {}'.format(self._server, msg_title)
        msg = 'Couchbase instance {} {}'.format(self._server, msg)

        return {
            'timestamp': int(time.time()),
            'event_type': 'couchbase_rebalance',
            'msg_text': msg,
            'msg_title': msg_title,
            'alert_type': alert_type,
            'source_type_name': SOURCE_TYPE_NAME,
            'aggregation_key': self._server,
            'tags': self._tags,
        }

    def _get_stats(self, url):
        """
        Hit a given URL and return the parsed json.
        """
        r = self.http.get(url)
        r.raise_for_status()
        return r.json()

    def check(self, _):
        data = self.get_data()
        self._collect_version(data)
        self._create_metrics(data)
        if self._sync_gateway_url:
            self._collect_sync_gateway_metrics()
        try:
            # Error handling in case Couchbase changes their versioning format
            if self._index_stats_url and self._version and int(self._version.split(".")[0]) >= 7:
                self._collect_index_stats_metrics()
        except Exception as e:
            self.log.debug(str(e))

    def _collect_version(self, data):
        nodes = data['stats']['nodes']

        if nodes:
            # Mixed version clusters are discouraged and are therefore rare, see:
            # https://forums.couchbase.com/t/combining-multiple-versions-in-one-cluster/8782/5
            version = nodes[0]['version']

            # Convert e.g. 5.5.3-4039-enterprise to semver
            num_separators = version.count('-')
            if num_separators == 2:
                build_separator = version.rindex('-')
                version = list(version)
                version[build_separator] = '+'
                self._version = ''.join(version)

            self.set_metadata('version', self._version)

    def get_data(self):
        # The dictionary to be returned.
        couchbase = {'stats': None, 'buckets': {}, 'nodes': {}, 'query': {}, 'tasks': {}}

        # build couchbase stats entry point
        url = '{}{}'.format(self._server, COUCHBASE_STATS_PATH)

        # Fetch initial stats and capture a service check based on response.
        service_check_tags = self._tags
        if service_check_tags is None:
            service_check_tags = []
        else:
            service_check_tags = list(set(service_check_tags))
        try:
            overall_stats = self._get_stats(url)
            # No overall stats? bail out now
            if overall_stats is None:
                raise Exception("No data returned from couchbase endpoint: {}".format(url))
        except requests.exceptions.HTTPError as e:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=service_check_tags, message=str(e))
            raise
        except Exception as e:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=service_check_tags, message=str(e))
            raise
        else:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.OK, tags=service_check_tags)

        couchbase['stats'] = overall_stats

        nodes = overall_stats['nodes']

        # Next, get all the nodes
        if nodes is not None:
            for node in nodes:
                couchbase['nodes'][node['hostname']] = node

        # Next, get all buckets .
        endpoint = overall_stats['buckets']['uri']

        url = '{}{}'.format(self._server, endpoint)
        buckets = self._get_stats(url)

        if buckets is not None:
            for bucket in buckets:
                bucket_name = bucket['name']

                # Fetch URI for the stats bucket
                endpoint = bucket['stats']['uri']
                url = '{}{}'.format(self._server, endpoint)

                try:
                    bucket_stats = self._get_stats(url)
                except requests.exceptions.HTTPError:
                    url_backup = '{}/pools/nodes/buckets/{}/stats'.format(self._server, bucket_name)
                    bucket_stats = self._get_stats(url_backup)

                bucket_samples = bucket_stats['op']['samples']
                if bucket_samples is not None:
                    couchbase['buckets'][bucket['name']] = bucket_samples

        # Next, get the query monitoring data
        query_data = self._get_query_monitoring_data()
        if query_data is not None:
            couchbase['query'] = query_data

        # Next, get all the tasks
        tasks_url = '{}{}/tasks'.format(self._server, COUCHBASE_STATS_PATH)
        try:
            tasks = self._get_stats(tasks_url)
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
            self.log.error("Error accessing the endpoint %s", tasks_url)

        return couchbase

    def _get_query_monitoring_data(self):
        query_data = None
        query_monitoring_url = self.instance.get('query_monitoring_url')
        if query_monitoring_url:
            url = '{}{}'.format(query_monitoring_url, COUCHBASE_VITALS_PATH)
            try:
                query_data = self._get_stats(url)
            except requests.exceptions.RequestException:
                self.log.error(
                    "Error accessing the endpoint %s, make sure you're running at least "
                    "couchbase 4.5 to collect the query monitoring metrics",
                    url,
                )

        return query_data

    def _collect_sync_gateway_metrics(self):
        url = '{}{}'.format(self._sync_gateway_url, SG_METRICS_PATH)
        try:
            data = self._get_stats(url).get('syncgateway', {})
        except requests.exceptions.RequestException as e:
            msg = "Error accessing the Sync Gateway monitoring endpoint %s: %s," % (url, str(e))
            self.log.debug(msg)
            self.service_check(SG_SERVICE_CHECK_NAME, AgentCheck.CRITICAL, msg, self._tags)
            return

        self.service_check(SG_SERVICE_CHECK_NAME, AgentCheck.OK, self._tags)

        global_resource_stats = data.get('global', {}).get('resource_utilization', {})
        for mname, mval in global_resource_stats.items():
            try:
                self._submit_gateway_metrics(mname, mval, self._tags)
            except Exception as e:
                self.log.debug("Unable to parse metric %s with value `%s: %s`", mname, mval, str(e))

        per_db_stats = data.get('per_db', {})
        for db, db_groups in per_db_stats.items():
            db_tags = ['db:{}'.format(db)] + self._tags
            for subgroup, db_metrics in db_groups.items():
                self.log.debug("Submitting metrics for group `%s`: `%s`", subgroup, db_metrics)
                for mname, mval in db_metrics.items():
                    try:
                        self._submit_gateway_metrics(mname, mval, db_tags, subgroup)
                    except Exception as e:
                        self.log.debug("Unable to parse metric %s with value `%s`: %s", mname, mval, str(e))
                        continue

    def _submit_gateway_metrics(self, mname, mval, tags, prefix=None):
        namespace = '.'.join(['couchbase', 'sync_gateway'])
        if prefix:
            namespace = '.'.join([namespace, prefix])

        if prefix == 'database' and mname in ['cache_feed', 'import_feed']:
            # Handle cache_feed and import_feed sub stats
            for cfname, cfval in mval.items():
                self.monotonic_count('.'.join([namespace, mname, cfname]), cfval, tags)
        elif prefix == 'gsi_views':
            # gsi view metrics are formatted with design doc and views `sync_gateway_2.1.access_query_count`
            # parse design doc as tag and submit rest as a metric
            match = re.match(r'\{([^}:;]+)\}-(\w+):', mname)
            if match:
                design_doc_tag = match.groups()[0]
                gsi_tags = ['design_doc_name:{}'.format(design_doc_tag)] + tags
                ddname = match.groups()[0]
                self.monotonic_count('.'.join([namespace, ddname]), tags=gsi_tags)

        elif mname in SYNC_GATEWAY_COUNT_METRICS:
            self.monotonic_count('.'.join([namespace, mname]), mval, tags)
        else:
            self.gauge('.'.join([namespace, mname]), mval, tags)

    # Takes a camelCased variable and returns a joined_lower equivalent.
    # Returns input if non-camelCase variable is detected.
    def camel_case_to_joined_lower(self, variable):
        # replace non-word with _
        converted_variable = re.sub(r'\W+', '_', variable)

        # insert _ in front of capital letters and lowercase the string
        converted_variable = re.sub('([A-Z])', r'_\g<1>', converted_variable).lower()

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

        match = SECONDS_VALUE_PATTERN.search(value)

        val, unit = match.group(1, 3)
        # They use the 'micro' symbol for microseconds so there is an encoding problem
        # so let's assume it's microseconds if we don't find the key in unit
        if unit not in TO_SECONDS:
            unit = 'us'

        return float(val) / TO_SECONDS[unit]

    def _collect_index_stats_metrics(self):
        url = urljoin(self._index_stats_url, INDEX_STATS_METRICS_PATH)
        try:
            data = self._get_stats(url)
        except requests.exceptions.RequestException as e:
            msg = "Error accessing the Index Statistics endpoint: %s: %s" % (url, str(e))
            self.log.warning(msg)
            self.service_check(INDEX_STATS_SERVICE_CHECK_NAME, AgentCheck.CRITICAL, self._tags, msg)
            return

        self.service_check(INDEX_STATS_SERVICE_CHECK_NAME, AgentCheck.OK, self._tags)

        for keyspace in data:
            if keyspace == "indexer":
                # The indexer object provides metric about the index node
                for mname, mval in data.get(keyspace).items():
                    self._submit_index_node_metrics(mname, mval)
            else:
                index_tags = self._extract_index_tags(keyspace) + self._tags
                for mname, mval in data.get(keyspace).items():
                    self._submit_per_index_metrics(mname, mval, index_tags)

    def _extract_index_tags(self, keyspace):
        # Index Keyspaces can come in different formats:
        # partition, bucket:index_name, bucket:collection:index_name, bucket:scope:collection:index_name
        # For variations missing the scope and collection, they refer to the default scope and collection respectively
        # https://docs.couchbase.com/server/current/n1ql/n1ql-language-reference/createprimaryindex.html#keyspace-ref
        tag_arr = keyspace.split(":")
        if len(tag_arr) == 2:
            bucket, index_name = tag_arr
            scope, collection = ["default", "default"]
        elif len(tag_arr) == 3:
            bucket, collection, index_name = tag_arr
            scope = 'default'
        elif len(tag_arr) == 4:
            bucket, scope, collection, index_name = tag_arr
        else:
            # Catch all incase the keyspace has either none or 3 or more separators(':')
            # There is a documented example of partition-num being a possible keyspace:
            # https://docs.couchbase.com/server/current/rest-api/rest-index-stats.html#_get_index_stats
            # But we shouldn't encounter this since we don't query the index api with the needed params
            # (Version 1.19.0+ of the Couchbase check)
            formatted_tags = []
            self.log.debug("Unable to extract tags from keyspace: %s", keyspace)
            return formatted_tags

        formatted_tags = [
            'bucket:{}'.format(bucket),
            'scope:{}'.format(scope),
            'collection:{}'.format(collection),
            'index_name:{}'.format(index_name),
        ]
        return formatted_tags

    def _submit_index_node_metrics(self, mname, mval):
        namespace = 'couchbase.indexer'
        f_mname = '.'.join([namespace, mname])
        if mname == "indexer_state":
            self.gauge(f_mname, INDEXER_STATE_MAP[mval], self._tags)
        else:
            self.gauge(f_mname, mval, self._tags)

    def _submit_per_index_metrics(self, mname, mval, tags):
        namespace = 'couchbase.index'
        f_mname = '.'.join([namespace, mname])
        if mname in INDEX_STATS_COUNT_METRICS:
            self.monotonic_count(f_mname, mval, tags)
        else:
            self.gauge(f_mname, mval, tags)
