# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six.moves.urllib.parse import urljoin
import math

from six import iteritems


class CouchDB2:

    MAX_NODES_PER_CHECK = 20

    def __init__(self, agent_check):
        self.agent_check = agent_check
        self.gauge = agent_check.gauge

    def _build_metrics(self, data, tags, prefix='couchdb'):
        for key, value in iteritems(data):
            if "type" in value:
                if value["type"] == "histogram":
                    for metric, value in iteritems(value["value"]):
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
        for key, value in iteritems(data['sizes']):
            self.gauge("couchdb.by_db.{0}_size".format(key), value, tags)

        for key in ['doc_del_count', 'doc_count']:
            self.gauge("couchdb.by_db.{0}".format(key), data[key], tags)

    def _build_dd_metrics(self, info, tags):
        data = info['view_index']
        ddtags = list(tags)
        ddtags.append("design_document:{0}".format(info['name']))
        ddtags.append("language:{0}".format(data['language']))

        for key, value in iteritems(data['sizes']):
            self.gauge("couchdb.by_ddoc.{0}_size".format(key), value, ddtags)

        for key, value in iteritems(data['updates_pending']):
            self.gauge("couchdb.by_ddoc.{0}_updates_pending".format(key), value, ddtags)

        self.gauge("couchdb.by_ddoc.waiting_clients", data['waiting_clients'], ddtags)

    def _build_system_metrics(self, data, tags, prefix='couchdb.erlang'):
        for key, value in iteritems(data):
            if key == "message_queues":
                for queue, val in iteritems(value):
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
                for node, metrics in iteritems(value):
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

        for metric, count in iteritems(counts):
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
