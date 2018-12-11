# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six.moves.urllib.parse import quote
from six.moves.urllib.parse import urljoin

from six import iteritems

import requests


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
        for key, stats in iteritems(overall_stats):
            for metric, val in iteritems(stats):
                if val['current'] is not None:
                    metric_name = '.'.join(['couchdb', key, metric])
                    self.gauge(metric_name, val['current'], tags=tags)

        for db_name, db_stats in iteritems(data.get('databases', {})):
            for name, val in iteritems(db_stats):
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
