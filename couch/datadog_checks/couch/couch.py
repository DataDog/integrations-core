# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from urlparse import urljoin
from urllib import quote
import math

import requests
from datadog_checks.checks import AgentCheck
from datadog_checks.utils.headers import headers

from . import errors


class CouchDb(AgentCheck):

    TIMEOUT = 5
    SERVICE_CHECK_NAME = 'couchdb.can_connect'
    SOURCE_TYPE_NAME = 'couchdb'
    MAX_DB = 50

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.checker = None

    def get(self, url, instance, service_check_tags, run_check=False):
        "Hit a given URL and return the parsed json"
        self.log.debug('Fetching CouchDB stats at url: %s' % url)

        auth = None
        if 'user' in instance and 'password' in instance:
            auth = (instance['user'], instance['password'])

        # Override Accept request header so that failures are not redirected to the Futon web-ui
        request_headers = headers(self.agentConfig)
        request_headers['Accept'] = 'text/json'

        try:
            r = requests.get(url, auth=auth, headers=request_headers,
                             timeout=int(instance.get('timeout', self.TIMEOUT)))
            r.raise_for_status()
            if run_check:
                self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK,
                                   tags=service_check_tags,
                                   message='Connection to %s was successful' % url)
        except requests.exceptions.Timeout as e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                               tags=service_check_tags, message="Request timeout: {0}, {1}".format(url, e))
            raise
        except requests.exceptions.HTTPError as e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                               tags=service_check_tags, message=str(e.message))
            raise
        except Exception as e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                               tags=service_check_tags, message=str(e))
            raise
        return r.json()

    def check(self, instance):
        server = self.get_server(instance)
        if self.checker is None:
            name = instance.get('name', server)
            tags = ["instance:{0}".format(name)] + self.get_config_tags(instance)

            try:
                version = self.get(self.get_server(instance), instance, tags, True)['version']
            except Exception:
                raise errors.ConnectionError("Unable to talk to the server")

            if version.startswith('1.'):
                self.checker = CouchDB1(self)
            elif version.startswith('2.'):
                self.checker = CouchDB2(self)
            else:
                raise errors.BadVersionError("Unkown version {0}".format(version))

        self.checker.check(instance)

    def get_server(self, instance):
        server = instance.get('server', None)
        if server is None:
            raise errors.BadConfigError("A server must be specified")
        return server

    def get_config_tags(self, instance):
        tags = instance.get('tags', [])

        # Clean up tags in case there was a None entry in the instance
        # e.g. if the yaml contains tags: but no actual tags
        return list(set(tags)) if tags else []


class CouchDB1:
    """Extracts stats from CouchDB via its REST API
    http://wiki.apache.org/couchdb/Runtime_Statistics
    """

    def __init__(self, agent_check):
        self.db_blacklist = {}
        self.agent_check = agent_check
        self.gauge = agent_check.gauge

    def _create_metric(self, data, tags=None):
        overall_stats = data.get('stats', {})
        for key, stats in overall_stats.items():
            for metric, val in stats.items():
                if val['current'] is not None:
                    metric_name = '.'.join(['couchdb', key, metric])
                    self.gauge(metric_name, val['current'], tags=tags)

        for db_name, db_stats in data.get('databases', {}).items():
            for name, val in db_stats.items():
                if name in ['doc_count', 'disk_size'] and val is not None:
                    metric_name = '.'.join(['couchdb', 'by_db', name])
                    metric_tags = list(tags)
                    metric_tags.append('db:%s' % db_name)
                    self.gauge(metric_name, val, tags=metric_tags, device_name=db_name)

    def check(self, instance):
        server = self.agent_check.get_server(instance)
        tags = ['instance:%s' % server] + self.agent_check.get_config_tags(instance)
        data = self.get_data(server, instance, tags)
        self._create_metric(data, tags=tags)

    def get_data(self, server, instance, tags):
        # The dictionary to be returned.
        couchdb = {'stats': None, 'databases': {}}

        # First, get overall statistics.
        endpoint = '/_stats/'

        url = urljoin(server, endpoint)

        overall_stats = self.agent_check.get(url, instance, tags, True)

        # No overall stats? bail out now
        if overall_stats is None:
            raise Exception("No stats could be retrieved from %s" % url)

        couchdb['stats'] = overall_stats

        # Next, get all database names.
        endpoint = '/_all_dbs/'

        url = urljoin(server, endpoint)

        # Get the list of whitelisted databases.
        db_whitelist = instance.get('db_whitelist')
        self.db_blacklist.setdefault(server, [])
        self.db_blacklist[server].extend(instance.get('db_blacklist', []))
        whitelist = set(db_whitelist) if db_whitelist else None
        databases = set(self.agent_check.get(url, instance, tags)) - set(self.db_blacklist[server])
        databases = databases.intersection(whitelist) if whitelist else databases

        max_dbs_per_check = instance.get('max_dbs_per_check', self.agent_check.MAX_DB)
        if len(databases) > max_dbs_per_check:
            self.agent_check.warning('Too many databases, only the first %s will be checked.' % max_dbs_per_check)
            databases = list(databases)[:max_dbs_per_check]

        for dbName in databases:
            url = urljoin(server, quote(dbName, safe=''))
            try:
                db_stats = self.agent_check.get(url, instance, tags)
            except requests.exceptions.HTTPError as e:
                couchdb['databases'][dbName] = None
                if (e.response.status_code == 403) or (e.response.status_code == 401):
                    self.db_blacklist[server].append(dbName)
                    self.warning('Database %s is not readable by the configured user. '
                                 'It will be added to the blacklist. Please restart the agent to clear.' % dbName)
                    del couchdb['databases'][dbName]
                    continue
            if db_stats is not None:
                couchdb['databases'][dbName] = db_stats
        return couchdb


class CouchDB2:

    MAX_NODES_PER_CHECK = 20

    def __init__(self, agent_check):
        self.agent_check = agent_check
        self.gauge = agent_check.gauge

    def _build_metrics(self, data, tags, prefix='couchdb'):
        for key, value in data.items():
            if "type" in value:
                if value["type"] == "histogram":
                    for metric, value in value["value"].items():
                        if metric == "histogram":
                            continue
                        elif metric == "percentile":
                            for pair in value:
                                self.gauge("{0}.{1}.percentile.{2}".format(prefix, key, pair[0]), pair[1], tags=tags)
                        else:
                            self.gauge("{0}.{1}.{2}".format(prefix, key, metric), value, tags=tags)
                else:
                    self.gauge("{0}.{1}".format(prefix, key), value["value"], tags=tags)
            elif type(value) is dict:
                self._build_metrics(value, tags, "{0}.{1}".format(prefix, key))

    def _build_db_metrics(self, data, tags):
        for key, value in data['sizes'].items():
            self.gauge("couchdb.by_db.{0}_size".format(key), value, tags)

        for key in ['purge_seq', 'doc_del_count', 'doc_count']:
            self.gauge("couchdb.by_db.{0}".format(key), data[key], tags)

    def _build_dd_metrics(self, info, tags):
        data = info['view_index']
        ddtags = list(tags)
        ddtags.append("design_document:{0}".format(info['name']))
        ddtags.append("language:{0}".format(data['language']))

        for key, value in data['sizes'].items():
            self.gauge("couchdb.by_ddoc.{0}_size".format(key), value, ddtags)

        for key, value in data['updates_pending'].items():
            self.gauge("couchdb.by_ddoc.{0}_updates_pending".format(key), value, ddtags)

        self.gauge("couchdb.by_ddoc.waiting_clients", data['waiting_clients'], ddtags)

    def _build_system_metrics(self, data, tags, prefix='couchdb.erlang'):
        for key, value in data.items():
            if key == "message_queues":
                for queue, val in value.items():
                    queue_tags = list(tags)
                    queue_tags.append("queue:{0}".format(queue))
                    if type(val) is dict:
                        if 'count' in val:
                            self.gauge("{0}.{1}.size".format(prefix, key), val['count'], queue_tags)
                        else:
                            self.agent_check.log.debug("Queue %s does not have a key 'count'. "
                                                       "It will be ignored." % queue)
                    else:
                        self.gauge("{0}.{1}.size".format(prefix, key), val, queue_tags)
            elif key == "distribution":
                for node, metrics in value.items():
                    dist_tags = list(tags)
                    dist_tags.append("node:{0}".format(node))
                    self._build_system_metrics(metrics, dist_tags, "{0}.{1}".format(prefix, key))
            elif type(value) is dict:
                self._build_system_metrics(value, tags, "{0}.{1}".format(prefix, key))
            else:
                self.gauge("{0}.{1}".format(prefix, key), value, tags)

    def _build_active_tasks_metrics(self, data, tags, prefix='couchdb.active_tasks'):
        counts = {
            'replication': 0,
            'database_compaction': 0,
            'indexer': 0,
            'view_compaction': 0
        }
        for task in data:
            counts[task['type']] += 1
            rtags = list(tags)
            if task['type'] == 'replication':
                for tag in ['doc_id', 'source', 'target', 'user']:
                    rtags.append("{0}:{1}".format(tag, task[tag]))
                rtags.append("type:{0}".format('continuous' if task['continuous'] else 'one-time'))
                metrics = [
                    'doc_write_failures',
                    'docs_read',
                    'docs_written',
                    'missing_revisions_found',
                    'revisions_checked',
                    'changes_pending'
                ]
                for metric in metrics:
                    if task[metric] is None:
                        task[metric] = 0
                    self.gauge("{0}.replication.{1}".format(prefix, metric), task[metric], rtags)
            elif task['type'] == 'database_compaction':
                rtags.append("database:{0}".format(task['database'].split('/')[-1].split('.')[0]))
                for metric in ['changes_done', 'progress', 'total_changes']:
                    self.gauge("{0}.db_compaction.{1}".format(prefix, metric), task[metric], rtags)
            elif task['type'] == 'indexer':
                rtags.append("database:{0}".format(task['database'].split('/')[-1].split('.')[0]))
                rtags.append("design_document:{0}".format(task['design_document'].split('/')[-1]))
                for metric in ['changes_done', 'progress', 'total_changes']:
                    self.gauge("{0}.indexer.{1}".format(prefix, metric), task[metric], rtags)
            elif task['type'] == 'view_compaction':
                rtags.append("database:{0}".format(task['database'].split('/')[-1].split('.')[0]))
                rtags.append("design_document:{0}".format(task['design_document'].split('/')[-1]))
                if task.get('phase', None) is not None:
                    rtags.append("phase:{0}".format(task['phase']))
                for metric in ['changes_done', 'progress', 'total_changes']:
                    if task.get(metric, None) is not None:
                        self.gauge("{0}.view_compaction.{1}".format(prefix, metric), task[metric], rtags)

        for metric, count in counts.items():
            if metric == "database_compaction":
                metric = "db_compaction"
            self.gauge("{0}.{1}.count".format(prefix, metric), count, tags)

    def _get_instance_names(self, server, instance):
        name = instance.get('name', None)
        if name is None:
            url = urljoin(server, "/_membership")
            names = self.agent_check.get(url, instance, [])['cluster_nodes']
            return names[:instance.get('max_nodes_per_check', self.MAX_NODES_PER_CHECK)]
        else:
            return [name]

    def _get_dbs_to_scan(self, server, instance, name, tags):
        dbs = self.agent_check.get(urljoin(server, "_all_dbs"), instance, tags)
        try:
            nodes = self.agent_check.get(urljoin(server, "_membership"), instance, tags)['cluster_nodes']
        except KeyError:
            return []

        idx = nodes.index(name)
        size = int(math.ceil(len(dbs) / float(len(nodes))))
        return dbs[(idx * size):((idx + 1) * size)]

    def check(self, instance):
        server = self.agent_check.get_server(instance)

        config_tags = self.agent_check.get_config_tags(instance)
        max_dbs_per_check = instance.get('max_dbs_per_check', self.agent_check.MAX_DB)
        for name in self._get_instance_names(server, instance):
            tags = config_tags + ["instance:{0}".format(name)]
            self._build_metrics(self._get_node_stats(server, name, instance, tags), tags)
            self._build_system_metrics(self._get_system_stats(server, name, instance, tags), tags)
            self._build_active_tasks_metrics(self._get_active_tasks(server, name, instance, tags), tags)

            db_whitelist = instance.get('db_whitelist', None)
            db_blacklist = instance.get('db_blacklist', [])
            scanned_dbs = 0
            for db in self._get_dbs_to_scan(server, instance, name, tags):
                if (db_whitelist is None or db in db_whitelist) and (db not in db_blacklist):
                    db_tags = config_tags + ["db:{0}".format(db)]
                    db_url = urljoin(server, db)
                    self._build_db_metrics(self.agent_check.get(db_url, instance, db_tags), db_tags)
                    for dd in self.agent_check.get(
                        "{0}/_all_docs?startkey=\"_design/\"&endkey=\"_design0\"".format(db_url),
                        instance,
                        db_tags
                    )['rows']:
                        self._build_dd_metrics(
                            self.agent_check.get("{0}/{1}/_info".format(db_url, dd['id']), instance, db_tags),
                            db_tags
                        )
                    scanned_dbs += 1
                    if scanned_dbs >= max_dbs_per_check:
                        break

    def _get_node_stats(self, server, name, instance, tags):
        url = urljoin(server, "/_node/{0}/_stats".format(name))

        # Fetch initial stats and capture a service check based on response.
        stats = self.agent_check.get(url, instance, tags, True)

        # No overall stats? bail out now
        if stats is None:
            raise Exception("No stats could be retrieved from %s" % url)

        return stats

    def _get_system_stats(self, server, name, instance, tags):
        url = urljoin(server, "/_node/{0}/_system".format(name))

        # Fetch _system (Erlang) stats.
        return self.agent_check.get(url, instance, tags)

    def _get_active_tasks(self, server, name, instance, tags):
        url = urljoin(server, "/_active_tasks")

        tasks = self.agent_check.get(url, instance, tags)

        #  print tasks

        return [task for task in tasks if task['node'] == name]
