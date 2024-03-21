# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re
import time
from collections import defaultdict, namedtuple
from copy import deepcopy
from itertools import product

import requests
from six import iteritems, itervalues
from six.moves.urllib.parse import urljoin, urlparse

from datadog_checks.base import AgentCheck, is_affirmative, to_string

from .config import from_instance
from .metrics import (
    CAT_ALLOCATION_METRICS,
    CLUSTER_PENDING_TASKS,
    INDEX_SEARCH_STATS,
    TEMPLATE_METRICS,
    health_stats_for_version,
    index_stats_for_version,
    node_system_stats_for_version,
    pshard_stats_for_version,
    slm_stats_for_version,
    stats_for_version,
)

REGEX = r'(?<!\\)\.'  # This regex string is used to traverse through nested dictionaries for JSON responses

DatadogESHealth = namedtuple('DatadogESHealth', ['status', 'reverse_status', 'tag'])
ES_HEALTH_TO_DD_STATUS = {
    'green': DatadogESHealth(AgentCheck.OK, AgentCheck.CRITICAL, 'OK'),
    'yellow': DatadogESHealth(AgentCheck.WARNING, AgentCheck.WARNING, 'WARN'),
    'red': DatadogESHealth(AgentCheck.CRITICAL, AgentCheck.OK, 'ALERT'),
}

# Skipping the following templates:
#
#   logs|metrics|synthetic: created by default by Elasticsearch, they can be disabled
#   by setting stack.templates.enabled to false
#
#   .monitoring: shard monitoring templates.
#
#   .slm: snapshot lifecyle management
#
#   .deprecation: deprecation reports
#
TEMPLATE_EXCLUSION_LIST = (
    'logs',
    'metrics',
    'synthetics',
    '.monitoring',
    '.slm-',
    '.deprecation',
)


class AuthenticationError(requests.exceptions.HTTPError):
    """Authentication Error, unable to reach server"""


def get_dynamic_tags(columns):
    dynamic_tags = []  # This is a list of (path to tag, name of tag)
    for column in columns:
        if column.get('type') == 'tag':
            value_path = column.get('value_path')
            name = column.get('name')
            dynamic_tags.append((value_path, name))
    return dynamic_tags


def get_value_from_path(value, path):
    result = value

    # Traverse the nested dictionaries
    for key in re.split(REGEX, path):
        if result is not None:
            key = key.replace('\\', '')
            if key.isdigit() and isinstance(result, list):
                result = result[int(key)]
            else:
                result = result.get(key)
        else:
            break

    return result


class ESCheck(AgentCheck):
    HTTP_CONFIG_REMAPPER = {
        'aws_service': {'name': 'aws_service', 'default': 'es'},
        'ssl_verify': {'name': 'tls_verify'},
        'ssl_cert': {'name': 'tls_cert'},
        'ssl_key': {'name': 'tls_private_key'},
    }

    SERVICE_CHECK_CONNECT_NAME = 'elasticsearch.can_connect'
    SERVICE_CHECK_CLUSTER_STATUS = 'elasticsearch.cluster_health'
    CAT_ALLOC_PATH = '/_cat/allocation?v=true&format=json&bytes=b'
    SOURCE_TYPE_NAME = 'elasticsearch'

    def __init__(self, name, init_config, instances):
        super(ESCheck, self).__init__(name, init_config, instances)
        # Host status needs to persist across all checks
        self.cluster_status = {}

        if self.instance.get('auth_type') == 'aws' and self.instance.get('url'):
            self.HTTP_CONFIG_REMAPPER = self.HTTP_CONFIG_REMAPPER.copy()
            self.HTTP_CONFIG_REMAPPER['aws_host'] = {
                'name': 'aws_host',
                'default': urlparse(self.instance['url']).hostname,
            }
        self._config = from_instance(self.instance)

    def check(self, _):
        admin_forwarder = self._config.admin_forwarder
        jvm_rate = self.instance.get('gc_collectors_as_rate', False)
        base_tags = list(self._config.tags)
        service_check_tags = list(self._config.service_check_tags)

        # Check ES version for this instance and define parameters
        # (URLs and metrics) accordingly
        try:
            version = self._get_es_version()
        except AuthenticationError:
            self.log.exception("The ElasticSearch credentials are incorrect")
            raise

        health_url, stats_url, pshard_stats_url, pending_tasks_url, slm_url = self._get_urls(version)
        stats_metrics = stats_for_version(version, jvm_rate)
        if self._config.cluster_stats:
            # Include Node System metrics
            stats_metrics.update(node_system_stats_for_version(version))
        pshard_stats_metrics = pshard_stats_for_version(version)

        # Load stats data.
        # This must happen before other URL processing as the cluster name
        # is retrieved here, and added to the tag list.
        stats_url = self._join_url(stats_url, admin_forwarder)
        stats_data = self._get_data(stats_url)

        if stats_data.get('cluster_name'):
            # retrieve the cluster name from the data, and append it to the
            # master tag list.
            cluster_tags = ["elastic_cluster:{}".format(stats_data['cluster_name'])]
            if not is_affirmative(self.instance.get('disable_legacy_cluster_tag', False)):
                cluster_tags.append("cluster_name:{}".format(stats_data['cluster_name']))
            base_tags.extend(cluster_tags)
            service_check_tags.extend(cluster_tags)
        self._process_stats_data(stats_data, stats_metrics, base_tags)

        if self._collect_template_metrics(es_version=version):
            self._get_template_metrics(admin_forwarder, base_tags)
        else:
            self.log.debug("ES version %s does not support template metrics", version)

        # Load cluster-wise data
        # Note: this is a cluster-wide query, might TO.
        if self._config.pshard_stats:
            send_sc = bubble_ex = not self._config.pshard_graceful_to
            pshard_stats_url = self._join_url(pshard_stats_url, admin_forwarder)
            try:
                pshard_stats_data = self._get_data(pshard_stats_url, send_sc=send_sc)
                self._process_pshard_stats_data(pshard_stats_data, pshard_stats_metrics, base_tags)
            except requests.ReadTimeout as e:
                if bubble_ex:
                    raise
                self.log.warning("Timed out reading pshard-stats from servers (%s) - stats will be missing", e)

        # Get Snapshot Lifecycle Management (SLM) policies
        if slm_url is not None:
            slm_url = self._join_url(slm_url, admin_forwarder)
            policy_data = self._get_data(slm_url)
            self._process_policy_data(policy_data, version, base_tags)

        # Load the health data.
        health_url = self._join_url(health_url, admin_forwarder)
        health_data = self._get_data(health_url)
        self._process_health_data(health_data, version, base_tags, service_check_tags)

        if self._config.pending_task_stats:
            # Load the pending_tasks data.
            pending_tasks_url = self._join_url(pending_tasks_url, admin_forwarder)
            pending_tasks_data = self._get_data(pending_tasks_url)
            self._process_pending_tasks_data(pending_tasks_data, base_tags)

        if self._config.index_stats and version >= [1, 0, 0]:
            try:
                self._get_index_metrics(admin_forwarder, version, base_tags)
            except requests.ReadTimeout as e:
                self.log.warning("Timed out reading index stats from servers (%s) - stats will be missing", e)

        # Load the cat allocation data.
        if self._config.cat_allocation_stats:
            self._process_cat_allocation_data(admin_forwarder, version, base_tags)

        # Load custom queries
        if self._config.custom_queries:
            self._run_custom_queries(admin_forwarder, base_tags)

        # If we're here we did not have any ES conn issues
        self.service_check(self.SERVICE_CHECK_CONNECT_NAME, AgentCheck.OK, tags=self._config.service_check_tags)

    def _get_es_version(self):
        """
        Get the running version of elasticsearch.
        """
        try:
            data = self._get_data(self._config.url, send_sc=False)
            raw_version = data['version']['number']

            self.set_metadata('version', raw_version)
            # pre-release versions of elasticearch are suffixed with -rcX etc..
            # peel that off so that the map below doesn't error out
            raw_version = raw_version.split('-')[0]
            version = [int(p) for p in raw_version.split('.')[0:3]]
            if data['version'].get('distribution', '') == 'opensearch':
                # Opensearch API is backwards compatible with ES 7.10.0
                # https://opensearch.org/faq
                self.log.debug('OpenSearch version %s detected', version)
                version = [7, 10, 0]
        except AuthenticationError:
            raise
        except Exception as e:
            self.warning("Error while trying to get Elasticsearch version from %s %s", self._config.url, e)
            version = [1, 0, 0]

        self.log.debug("Elasticsearch version is %s", version)
        return version

    def _join_url(self, url, admin_forwarder=False):
        """
        overrides `urlparse.urljoin` since it removes base url path
        https://docs.python.org/2/library/urlparse.html#urlparse.urljoin
        """
        if admin_forwarder:
            return self._config.url + url
        else:
            return urljoin(self._config.url, url)

    def _get_index_metrics(self, admin_forwarder, version, base_tags):
        index_resp = self._get_data(self._join_url('/_cat/indices?format=json&bytes=b', admin_forwarder))
        for idx in index_resp:
            # we need to remap metric names because the ones from elastic
            # contain dots and that would confuse `_process_metric()` (sic)
            index_data = {
                'docs_count': idx.get('docs.count'),
                'docs_deleted': idx.get('docs.deleted'),
                'primary_shards': idx.get('pri'),
                'replica_shards': idx.get('rep'),
                'primary_store_size': idx.get('pri.store.size'),
                'store_size': idx.get('store.size'),
                'health': idx.get('health'),
            }

            # Convert Elastic health to Datadog status.
            if index_data['health'] is not None:
                dd_health = ES_HEALTH_TO_DD_STATUS[index_data['health'].lower()]
                index_data['health'] = dd_health.status
                index_data['health_reverse'] = dd_health.reverse_status

            # Ensure that index_data does not contain None values
            for key, value in list(iteritems(index_data)):
                if value is None:
                    del index_data[key]
                    self.log.debug("The index %s has no metric data for %s", idx['index'], key)

            tags = base_tags + ['index_name:' + idx['index']]
            for metric, desc in iteritems(index_stats_for_version(version)):
                self._process_metric(index_data, metric, *desc, tags=tags)
        self._get_index_search_stats(admin_forwarder, base_tags)

    def _get_template_metrics(self, admin_forwarder, base_tags):

        try:
            template_resp = self._get_data(self._join_url('/_cat/templates?format=json', admin_forwarder))
        except requests.exceptions.RequestException as e:
            self.log.debug("Error reading templates info from servers (%s) - template metrics will be missing", e)
            return

        filtered_templates = [t for t in template_resp if not t['name'].startswith(TEMPLATE_EXCLUSION_LIST)]

        for metric, desc in iteritems(TEMPLATE_METRICS):
            self._process_metric({'templates': filtered_templates}, metric, *desc, tags=base_tags)

    def _get_index_search_stats(self, admin_forwarder, base_tags):
        """
        Stats for searches in every index.
        """
        # NOTE: Refactor this if we discover we are making too many requests.
        # This endpoint can return more data, all of what the /_cat/indices endpoint returns except index health.
        # The health we can get from /_cluster/health if we pass level=indices query param. Reference:
        # https://www.elastic.co/guide/en/elasticsearch/reference/current/cluster-health.html#cluster-health-api-query-params # noqa: E501
        indices = self._get_data(self._join_url('/_stats/search', admin_forwarder))['indices']
        for (idx_name, data), (m_name, path) in product(iteritems(indices), INDEX_SEARCH_STATS):
            tags = base_tags + ['index_name:' + idx_name]
            self._process_metric(data, m_name, 'gauge', path, tags=tags)

    def _get_urls(self, version):
        """
        Compute the URLs we need to hit depending on the running ES version
        """
        pshard_stats_url = "/_stats"
        health_url = "/_cluster/health"
        slm_url = None

        if version >= [0, 90, 10]:
            pending_tasks_url = "/_cluster/pending_tasks"
            stats_url = "/_nodes/stats" if self._config.cluster_stats else "/_nodes/_local/stats"
            if version < [5, 0, 0]:
                # version 5 errors out if the `all` parameter is set
                stats_url += "?all=true"
            if version >= [7, 4, 0] and self._config.slm_stats:
                slm_url = "/_slm/policy"
        else:
            # legacy
            pending_tasks_url = None
            stats_url = (
                "/_cluster/nodes/stats?all=true"
                if self._config.cluster_stats
                else "/_cluster/nodes/_local/stats?all=true"
            )

        return health_url, stats_url, pshard_stats_url, pending_tasks_url, slm_url

    def _get_data(self, url, send_sc=True, data=None):
        """
        Hit a given URL and return the parsed json
        """
        resp = None
        try:
            if data:
                resp = self.http.post(url, json=data)
            else:
                resp = self.http.get(url)
            resp.raise_for_status()
        except Exception as e:
            # this means we've hit a particular kind of auth error that means the config is broken
            if isinstance(resp, requests.Response) and resp.status_code == 400:
                raise AuthenticationError("The ElasticSearch credentials are incorrect")

            if send_sc:
                self.service_check(
                    self.SERVICE_CHECK_CONNECT_NAME,
                    AgentCheck.CRITICAL,
                    message="Error {} when hitting {}".format(e, url),
                    tags=self._config.service_check_tags,
                )
            raise

        self.log.debug("request to url %s returned: %s", url, resp)

        return resp.json()

    def _process_pending_tasks_data(self, data, base_tags):
        p_tasks = defaultdict(int)
        average_time_in_queue = 0

        for task in data.get('tasks', []):
            p_tasks[task.get('priority')] += 1
            average_time_in_queue += task.get('time_in_queue_millis', 0)

        total = sum(itervalues(p_tasks))
        node_data = {
            'pending_task_total': total,
            'pending_tasks_priority_high': p_tasks['high'],
            'pending_tasks_priority_urgent': p_tasks['urgent'],
            # if total is 0 default to 1
            'pending_tasks_time_in_queue': average_time_in_queue // (total or 1),
        }

        for metric in CLUSTER_PENDING_TASKS:
            # metric description
            desc = CLUSTER_PENDING_TASKS[metric]
            self._process_metric(node_data, metric, *desc, tags=base_tags)

    def _process_stats_data(self, data, stats_metrics, base_tags):
        for node_data in itervalues(data.get('nodes', {})):
            metric_hostname = None
            metrics_tags = list(base_tags)

            # Resolve the node's name
            node_name = node_data.get('name')
            if node_name:
                metrics_tags.append('node_name:{}'.format(node_name))

            # Resolve the node's hostname
            if self._config.node_name_as_host:
                if node_name:
                    metric_hostname = node_name
            elif self._config.cluster_stats:
                for k in ['hostname', 'host']:
                    if k in node_data:
                        metric_hostname = node_data[k]
                        break

            for metric, desc in iteritems(stats_metrics):
                self._process_metric(node_data, metric, *desc, tags=metrics_tags, hostname=metric_hostname)

    def _process_pshard_stats_data(self, data, pshard_stats_metrics, base_tags):
        for metric, desc in iteritems(pshard_stats_metrics):
            pshard_tags = base_tags
            if desc[1].startswith('_all.'):
                pshard_tags = pshard_tags + ['index_name:_all']
            self._process_metric(data, metric, *desc, tags=pshard_tags)
        # process index-level metrics
        if self._config.cluster_stats and self._config.detailed_index_stats:
            for metric, desc in iteritems(pshard_stats_metrics):
                if desc[1].startswith('_all.'):
                    for index in data['indices']:
                        self.log.debug("Processing index %s", index)
                        escaped_index = index.replace('.', '\.')  # noqa: W605
                        index_desc = (
                            desc[0],
                            'indices.' + escaped_index + '.' + desc[1].replace('_all.', ''),
                            desc[2] if 2 < len(desc) else None,
                        )
                        self._process_metric(data, metric, *index_desc, tags=base_tags + ['index_name:' + index])

    def _process_metric(self, data, metric, xtype, path, xform=None, tags=None, hostname=None):
        """
        data: dictionary containing all the stats
        metric: datadog metric
        path: corresponding path in data, flattened, e.g. thread_pool.bulk.queue
        xform: a lambda to apply to the numerical value
        """
        value = get_value_from_path(data, path)

        if value is not None:
            if xform:
                value = xform(value)
            if xtype == "gauge":
                self.gauge(metric, value, tags=tags, hostname=hostname)
            elif xtype == "monotonic_count":
                self.monotonic_count(metric, value, tags=tags, hostname=hostname)
            else:
                self.rate(metric, value, tags=tags, hostname=hostname)
        else:
            self.log.debug("Metric not found: %s -> %s", path, metric)

    def _process_health_data(self, data, version, base_tags, service_check_tags):
        prev_status = self.cluster_status.get(self._config.url)
        self.cluster_status[self._config.url] = current_status = data.get('status')
        if self._config.submit_events and (
            (prev_status is None and current_status in ["yellow", "red"])  # Cluster starts in bad status.
            or current_status != prev_status
        ):
            self.event(self._create_event(current_status, tags=base_tags))

        for metric, desc in iteritems(health_stats_for_version(version)):
            self._process_metric(data, metric, *desc, tags=base_tags)

        # Process the service check
        dd_health = ES_HEALTH_TO_DD_STATUS.get(current_status, ES_HEALTH_TO_DD_STATUS['red'])
        msg = (
            "{tag} on cluster \"{cluster_name}\" "
            "| active_shards={active_shards} "
            "| initializing_shards={initializing_shards} "
            "| relocating_shards={relocating_shards} "
            "| unassigned_shards={unassigned_shards} "
            "| timed_out={timed_out}".format(
                tag=dd_health.tag,
                cluster_name=data.get('cluster_name'),
                active_shards=data.get('active_shards'),
                initializing_shards=data.get('initializing_shards'),
                relocating_shards=data.get('relocating_shards'),
                unassigned_shards=data.get('unassigned_shards'),
                timed_out=data.get('timed_out'),
            )
        )
        self.service_check(self.SERVICE_CHECK_CLUSTER_STATUS, dd_health.status, message=msg, tags=service_check_tags)

    def _process_policy_data(self, data, version, base_tags):
        for policy, policy_data in iteritems(data):
            repo = policy_data.get('policy', {}).get('repository', 'unknown')
            tags = base_tags + ['policy:{}'.format(policy), 'repository:{}'.format(repo)]

            slm_stats = slm_stats_for_version(version)
            for metric, desc in iteritems(slm_stats):
                self._process_metric(policy_data, metric, *desc, tags=tags)

    def _process_cat_allocation_data(self, admin_forwarder, version, base_tags):
        if version < [5, 0, 0]:
            self.log.debug(
                "Collecting cat allocation metrics is not supported in version %s. Skipping",
                '.'.join(str(int) for int in version),
            )
            return

        self.log.debug("Collecting cat allocation metrics")
        cat_allocation_url = self._join_url(self.CAT_ALLOC_PATH, admin_forwarder)
        try:
            cat_allocation_data = self._get_data(cat_allocation_url)
        except requests.ReadTimeout as e:
            self.log.error("Timed out reading cat allocation stats from servers (%s) - stats will be missing", e)
            return

        # we need to remap metric names because the ones from elastic
        # contain dots and that would confuse `_process_metric()` (sic)
        data_to_collect = {'disk.indices', 'disk.used', 'disk.avail', 'disk.total', 'disk.percent', 'shards'}
        for dic in cat_allocation_data:
            cat_allocation_dic = {
                k.replace('.', '_'): v for k, v in dic.items() if k in data_to_collect and v is not None
            }
            tags = base_tags + ['node_name:' + dic.get('node').lower()]
            for metric in CAT_ALLOCATION_METRICS:
                desc = CAT_ALLOCATION_METRICS[metric]
                self._process_metric(cat_allocation_dic, metric, *desc, tags=tags)

    def _process_custom_metric(
        self,
        value,
        data_path,
        value_path,
        dynamic_tags,
        xtype,
        metric_name,
        tags=None,
    ):
        """
        value: JSON payload to traverse
        data_path: path to data right before metric value or right before list of metric values
        value_path: path to data after data_path to metric value
        dynamic_tags: list of dynamic tags and their value_paths
        xtype: datadog metric type, default to gauge
        metric_name: datadog metric name
        tags: list of tags that should be included with each metric submitted
        """

        tags_to_submit = deepcopy(tags)
        path = '{}.{}'.format(data_path, value_path)

        # Collect the value of tags first, and then append to tags_to_submit
        for dynamic_tag_path, dynamic_tag_name in dynamic_tags:
            # Traverse down the tree to find the tag value
            dynamic_tag_value = get_value_from_path(value, dynamic_tag_path)

            # If tag is there, then add it to list of tags to submit
            if dynamic_tag_value is not None:
                dynamic_tag = '{}:{}'.format(dynamic_tag_name, dynamic_tag_value)
                tags_to_submit.append(dynamic_tag)
            else:
                self.log.debug("Dynamic tag is null: %s -> %s", path, dynamic_tag_name)

        # Now do the same for the actual metric
        branch_value = get_value_from_path(value, value_path)

        if branch_value is not None:
            if xtype == "gauge":
                self.gauge(metric_name, branch_value, tags=tags_to_submit)
            elif xtype == "monotonic_count":
                self.monotonic_count(metric_name, branch_value, tags=tags_to_submit)
            elif xtype == "rate":
                self.rate(metric_name, branch_value, tags=tags_to_submit)
            else:
                self.log.warning(
                    "Metric type of %s is not gauge, monotonic_count, or rate; skipping this metric", metric_name
                )
        else:
            self.log.debug("Metric not found: %s -> %s", path, metric_name)

    def _run_custom_queries(self, admin_forwarder, base_tags):
        self.log.debug("Running custom queries")
        custom_queries = self._config.custom_queries

        for query_endpoint in custom_queries:
            try:
                columns = query_endpoint.get('columns', [])
                data_path = query_endpoint.get('data_path')
                raw_endpoint = query_endpoint.get('endpoint')
                static_tags = query_endpoint.get('tags', [])
                payload = query_endpoint.get('payload', {})

                endpoint = self._join_url(raw_endpoint, admin_forwarder)
                data = self._get_data(endpoint, data=payload)

                # If there are tags, add the tag path to list of paths to evaluate while processing metric
                dynamic_tags = get_dynamic_tags(columns)
                tags = base_tags + static_tags

                # Traverse the nested dictionaries to the data_path and get the remainder JSON response
                value = get_value_from_path(data, data_path)

                for column in columns:
                    metric_type = column.get('type', 'gauge')

                    # Skip tags since already processed
                    if metric_type == 'tag':
                        continue
                    name = column.get('name')
                    value_path = column.get('value_path')
                    if name and value_path:
                        # At this point, there may be multiple branches of value_paths.
                        # If value is a list, go through each entry
                        if isinstance(value, list):
                            value = value
                        else:
                            value = [value]

                        for branch in value:
                            self._process_custom_metric(
                                value=branch,
                                data_path=data_path,
                                value_path=value_path,
                                dynamic_tags=dynamic_tags,
                                xtype=metric_type,
                                metric_name=name,
                                tags=tags,
                            )
            except Exception as e:
                self.log.error("Custom query %s failed: %s", query_endpoint, e)
                continue

    def _create_event(self, status, tags=None):
        hostname = to_string(self.hostname)
        if status == "red":
            alert_type = "error"
            msg_title = "{} is {}".format(hostname, status)

        elif status == "yellow":
            alert_type = "warning"
            msg_title = "{} is {}".format(hostname, status)

        else:
            # then it should be green
            alert_type = "success"
            msg_title = "{} recovered as {}".format(hostname, status)

        msg = "ElasticSearch: {} just reported as {}".format(hostname, status)

        return {
            'timestamp': int(time.time()),
            'event_type': 'elasticsearch',
            'host': hostname,
            'msg_text': msg,
            'msg_title': msg_title,
            'alert_type': alert_type,
            'source_type_name': "elasticsearch",
            'event_object': hostname,
            'tags': tags,
        }

    @staticmethod
    def _collect_template_metrics(es_version):
        # Prerequisite check to determine if template metrics should be collected or not
        # https://www.elastic.co/guide/en/elasticsearch/reference/5.1/release-notes-5.1.1.html#feature-5.1.1
        # Template metric collection by default sends a critical service alert in case of failure
        #   For unsupported ES versions (<5.1.1) failure to collect template metrics is expected
        #   This function will aid for collecting template metrics only on the supported ES versions
        CAT_TEMPLATE_SUPPORTED_ES_VERSION = [5, 1, 1]

        return es_version >= CAT_TEMPLATE_SUPPORTED_ES_VERSION
