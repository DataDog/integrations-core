# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import time
from collections import defaultdict

import requests
from six import iteritems, itervalues
from six.moves.urllib.parse import urljoin, urlparse

from datadog_checks.base import AgentCheck, to_string

from .config import from_instance
from .metrics import (
    CLUSTER_PENDING_TASKS,
    health_stats_for_version,
    index_stats_for_version,
    node_system_stats_for_version,
    pshard_stats_for_version,
    stats_for_version,
)


class AuthenticationError(requests.exceptions.HTTPError):
    """Authentication Error, unable to reach server"""


class ESCheck(AgentCheck):
    HTTP_CONFIG_REMAPPER = {
        'aws_service': {'name': 'aws_service', 'default': 'es'},
        'ssl_verify': {'name': 'tls_verify'},
        'ssl_cert': {'name': 'tls_cert'},
        'ssl_key': {'name': 'tls_private_key'},
    }

    SERVICE_CHECK_CONNECT_NAME = 'elasticsearch.can_connect'
    SERVICE_CHECK_CLUSTER_STATUS = 'elasticsearch.cluster_health'
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

    def check(self, instance):
        config = from_instance(instance)
        admin_forwarder = config.admin_forwarder

        # Check ES version for this instance and define parameters
        # (URLs and metrics) accordingly
        try:
            version = self._get_es_version(config)
        except AuthenticationError:
            self.log.exception("The ElasticSearch credentials are incorrect")
            raise

        health_url, stats_url, pshard_stats_url, pending_tasks_url = self._get_urls(version, config.cluster_stats)
        stats_metrics = stats_for_version(version)
        if config.cluster_stats:
            # Include Node System metrics
            stats_metrics.update(node_system_stats_for_version(version))
        pshard_stats_metrics = pshard_stats_for_version(version)

        # Load stats data.
        # This must happen before other URL processing as the cluster name
        # is retrieved here, and added to the tag list.
        stats_url = self._join_url(config.url, stats_url, admin_forwarder)
        stats_data = self._get_data(stats_url, config)
        if stats_data.get('cluster_name'):
            # retrieve the cluster name from the data, and append it to the
            # master tag list.
            cluster_name_tag = "cluster_name:{}".format(stats_data['cluster_name'])
            config.tags.append(cluster_name_tag)
            config.health_tags.append(cluster_name_tag)
        self._process_stats_data(stats_data, stats_metrics, config)

        # Load cluster-wise data
        # Note: this is a cluster-wide query, might TO.
        if config.pshard_stats:
            send_sc = bubble_ex = not config.pshard_graceful_to
            pshard_stats_url = self._join_url(config.url, pshard_stats_url, admin_forwarder)
            try:
                pshard_stats_data = self._get_data(pshard_stats_url, config, send_sc=send_sc)
                self._process_pshard_stats_data(pshard_stats_data, config, pshard_stats_metrics)
            except requests.ReadTimeout as e:
                if bubble_ex:
                    raise
                self.log.warning("Timed out reading pshard-stats from servers (%s) - stats will be missing", e)

        # Load the health data.
        health_url = self._join_url(config.url, health_url, admin_forwarder)
        health_data = self._get_data(health_url, config)
        self._process_health_data(health_data, config, version)

        if config.pending_task_stats:
            # Load the pending_tasks data.
            pending_tasks_url = self._join_url(config.url, pending_tasks_url, admin_forwarder)
            pending_tasks_data = self._get_data(pending_tasks_url, config)
            self._process_pending_tasks_data(pending_tasks_data, config)

        if config.index_stats and version >= [1, 0, 0]:
            try:
                self._get_index_metrics(config, admin_forwarder, version)
            except requests.ReadTimeout as e:
                self.log.warning("Timed out reading index stats from servers (%s) - stats will be missing", e)

        # If we're here we did not have any ES conn issues
        self.service_check(self.SERVICE_CHECK_CONNECT_NAME, AgentCheck.OK, tags=config.service_check_tags)

    def _get_es_version(self, config):
        """
        Get the running version of elasticsearch.
        """
        try:
            data = self._get_data(config.url, config, send_sc=False)
            raw_version = data['version']['number']
            self.set_metadata('version', raw_version)
            # pre-release versions of elasticearch are suffixed with -rcX etc..
            # peel that off so that the map below doesn't error out
            raw_version = raw_version.split('-')[0]
            version = [int(p) for p in raw_version.split('.')[0:3]]
        except AuthenticationError:
            raise
        except Exception as e:
            self.warning("Error while trying to get Elasticsearch version from %s %s", config.url, e)
            version = [1, 0, 0]

        self.log.debug("Elasticsearch version is %s", version)
        return version

    def _join_url(self, base, url, admin_forwarder=False):
        """
        overrides `urlparse.urljoin` since it removes base url path
        https://docs.python.org/2/library/urlparse.html#urlparse.urljoin
        """
        if admin_forwarder:
            return base + url
        else:
            return urljoin(base, url)

    def _get_index_metrics(self, config, admin_forwarder, version):
        cat_url = '/_cat/indices?format=json&bytes=b'
        index_url = self._join_url(config.url, cat_url, admin_forwarder)
        index_resp = self._get_data(index_url, config)
        index_stats_metrics = index_stats_for_version(version)
        health_stat = {'green': 0, 'yellow': 1, 'red': 2}
        for idx in index_resp:
            tags = config.tags + ['index_name:' + idx['index']]
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

            # Convert the health status value
            if index_data['health'] is not None:
                index_data['health'] = health_stat[index_data['health'].lower()]

            # Ensure that index_data does not contain None values
            for key, value in list(iteritems(index_data)):
                if value is None:
                    del index_data[key]
                    self.log.warning("The index %s has no metric data for %s", idx['index'], key)

            for metric in index_stats_metrics:
                # metric description
                desc = index_stats_metrics[metric]
                self._process_metric(index_data, metric, *desc, tags=tags)

    def _get_urls(self, version, cluster_stats):
        """
        Compute the URLs we need to hit depending on the running ES version
        """
        pshard_stats_url = "/_stats"
        health_url = "/_cluster/health"

        if version >= [0, 90, 10]:
            pending_tasks_url = "/_cluster/pending_tasks"
            stats_url = "/_nodes/stats" if cluster_stats else "/_nodes/_local/stats"
            if version < [5, 0, 0]:
                # version 5 errors out if the `all` parameter is set
                stats_url += "?all=true"
        else:
            # legacy
            pending_tasks_url = None
            stats_url = "/_cluster/nodes/stats?all=true" if cluster_stats else "/_cluster/nodes/_local/stats?all=true"

        return health_url, stats_url, pshard_stats_url, pending_tasks_url

    def _get_data(self, url, config, send_sc=True):
        """
        Hit a given URL and return the parsed json
        """
        resp = None
        try:
            resp = self.http.get(url)
            resp.raise_for_status()
        except Exception as e:
            # this means we've hit a particular kind of auth error that means the config is broken
            if resp and resp.status_code == 400:
                raise AuthenticationError("The ElasticSearch credentials are incorrect")

            if send_sc:
                self.service_check(
                    self.SERVICE_CHECK_CONNECT_NAME,
                    AgentCheck.CRITICAL,
                    message="Error {} when hitting {}".format(e, url),
                    tags=config.service_check_tags,
                )
            raise

        self.log.debug("request to url %s returned: %s", url, resp)

        return resp.json()

    def _process_pending_tasks_data(self, data, config):
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
            self._process_metric(node_data, metric, *desc, tags=config.tags)

    def _process_stats_data(self, data, stats_metrics, config):
        for node_data in itervalues(data.get('nodes', {})):
            metric_hostname = None
            metrics_tags = list(config.tags)

            # Resolve the node's name
            node_name = node_data.get('name')
            if node_name:
                metrics_tags.append('node_name:{}'.format(node_name))

            # Resolve the node's hostname
            if config.node_name_as_host:
                if node_name:
                    metric_hostname = node_name
            elif config.cluster_stats:
                for k in ['hostname', 'host']:
                    if k in node_data:
                        metric_hostname = node_data[k]
                        break

            for metric, desc in iteritems(stats_metrics):
                self._process_metric(node_data, metric, *desc, tags=metrics_tags, hostname=metric_hostname)

    def _process_pshard_stats_data(self, data, config, pshard_stats_metrics):
        for metric, desc in iteritems(pshard_stats_metrics):
            self._process_metric(data, metric, *desc, tags=config.tags)

    def _process_metric(self, data, metric, xtype, path, xform=None, tags=None, hostname=None):
        """
        data: dictionary containing all the stats
        metric: datadog metric
        path: corresponding path in data, flattened, e.g. thread_pool.bulk.queue
        xform: a lambda to apply to the numerical value
        """
        value = data

        # Traverse the nested dictionaries
        for key in path.split('.'):
            if value is not None:
                value = value.get(key)
            else:
                break

        if value is not None:
            if xform:
                value = xform(value)
            if xtype == "gauge":
                self.gauge(metric, value, tags=tags, hostname=hostname)
            else:
                self.rate(metric, value, tags=tags, hostname=hostname)
        else:
            self.log.debug("Metric not found: %s -> %s", path, metric)

    def _process_health_data(self, data, config, version):
        cluster_status = data.get('status')
        if not self.cluster_status.get(config.url):
            self.cluster_status[config.url] = cluster_status
            if cluster_status in ["yellow", "red"]:
                event = self._create_event(cluster_status, tags=config.tags)
                self.event(event)

        if cluster_status != self.cluster_status.get(config.url):
            self.cluster_status[config.url] = cluster_status
            event = self._create_event(cluster_status, tags=config.tags)
            self.event(event)

        cluster_health_metrics = health_stats_for_version(version)

        for metric, desc in iteritems(cluster_health_metrics):
            self._process_metric(data, metric, *desc, tags=config.tags)

        # Process the service check
        if cluster_status == 'green':
            status = AgentCheck.OK
            data['tag'] = "OK"
        elif cluster_status == 'yellow':
            status = AgentCheck.WARNING
            data['tag'] = "WARN"
        else:
            status = AgentCheck.CRITICAL
            data['tag'] = "ALERT"

        msg = (
            "{tag} on cluster \"{cluster_name}\" "
            "| active_shards={active_shards} "
            "| initializing_shards={initializing_shards} "
            "| relocating_shards={relocating_shards} "
            "| unassigned_shards={unassigned_shards} "
            "| timed_out={timed_out}".format(
                tag=data.get('tag'),
                cluster_name=data.get('cluster_name'),
                active_shards=data.get('active_shards'),
                initializing_shards=data.get('initializing_shards'),
                relocating_shards=data.get('relocating_shards'),
                unassigned_shards=data.get('unassigned_shards'),
                timed_out=data.get('timed_out'),
            )
        )

        self.service_check(
            self.SERVICE_CHECK_CLUSTER_STATUS, status, message=msg, tags=config.service_check_tags + config.health_tags
        )

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
