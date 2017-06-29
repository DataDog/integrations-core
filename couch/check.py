# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from urlparse import urljoin
from urllib import quote

# 3rd party
import requests

# project
from checks import AgentCheck
from util import headers


# In couch 2.0 these metrics moved from the top level to under couchdb
COUCHDB2_MOVED_METRICS = ('httpd', 'httpd_request_methods', 'httpd_status_codes')


class CouchDb(AgentCheck):
    """Extracts stats from CouchDB via its REST API
    http://wiki.apache.org/couchdb/Runtime_Statistics
    """

    MAX_DB = 50
    SERVICE_CHECK_NAME = 'couchdb.can_connect'
    SOURCE_TYPE_NAME = 'couchdb'
    TIMEOUT = 5

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.db_blacklist = {}

    def _create_metric_helper(self, overall_stats, tags):
        for key, stats in overall_stats.items():
            for metric, val in stats.items():
                if 'current' in val:
                    if val['current'] is None:
                        continue
                    metric_name = '.'.join(['couchdb', key, metric])
                    self.gauge(metric_name, val['current'], tags=tags)
                elif 'value' in val:
                    if val['value'] is None:
                        continue
                    metric_name = '.'.join(['couchdb', key, metric])
                    self.gauge(metric_name, val['value'], tags=tags)
                elif isinstance(val, dict):
                    for sub_metric, sub_val in val.items():
                        if sub_val.get('value') is not None:
                            if metric in COUCHDB2_MOVED_METRICS:
                                metric_name = '.'.join(['couchdb', metric, sub_metric])
                            else:
                                metric_name = '.'.join(['couchdb', key, metric, sub_metric])
                            self.gauge(metric_name, sub_val['value'], tags=tags)

    def _create_metric(self, data, tags=None):
        if data.get('stats'):
            self._create_metric_helper(data['stats'], tags)
        elif data.get('cluster_stats'):
            for member, member_stats in data['cluster_stats'].items():
                member_tags = (tags or []) + ['node:%s' % member]
                self._create_metric_helper(data['cluster_stats'], member_tags)

        for db_name, db_stats in data.get('databases', {}).items():
            for name, val in db_stats.items():
                if name in ['doc_count', 'disk_size'] and val is not None:
                    metric_name = '.'.join(['couchdb', 'by_db', name])
                    metric_tags = list(tags)
                    metric_tags.append('db:%s' % db_name)
                    self.gauge(metric_name, val, tags=metric_tags, device_name=db_name)

    def _get_stats(self, url, instance):
        "Hit a given URL and return the parsed json"
        self.log.debug('Fetching Couchdb stats at url: %s' % url)

        auth = None
        if 'user' in instance and 'password' in instance:
            auth = (instance['user'], instance['password'])
        # Override Accept request header so that failures are not redirected to the Futon web-ui
        request_headers = headers(self.agentConfig)
        request_headers['Accept'] = 'text/json'
        r = requests.get(url, auth=auth, headers=request_headers,
                         timeout=int(instance.get('timeout', self.TIMEOUT)))
        r.raise_for_status()
        return r.json()

    def check(self, instance):
        server = instance.get('server', None)
        if server is None:
            raise Exception("A server must be specified")
        data = self.get_data(server, instance)
        self._create_metric(data, tags=['instance:%s' % server])

    def _get_node_stats(self, server, instance):
        # First, get overall statistics.
        endpoint = '_stats/'

        url = urljoin(server, endpoint)

        # Fetch initial stats and capture a service check based on response.
        service_check_tags = ['instance:%s' % server]
        try:
            overall_stats = self._get_stats(url, instance)
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
        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK,
                tags=service_check_tags,
                message='Connection to %s was successful' % url)

        # No overall stats? bail out now
        if overall_stats is None:
            raise Exception("No stats could be retrieved from %s" % url)

        return overall_stats

    def _get_couch_version(self, server):
        try:
            couch_version = requests.get(server).json().get('version', '1.6')
        except Exception as e:
            service_check_tags = ['instance:%s' % server]
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                tags=service_check_tags, message=str(e))
            raise
        else:
            return couch_version

    def get_data(self, server, instance):
        # The dictionary to be returned.
        couchdb = {'stats': None, 'cluster_stats': {}, 'databases': {}}

        couch_version = self._get_couch_version(server)
        if couch_version.startswith('2.'):
            endpoint = '_membership'
            url = urljoin(server, endpoint)
            members = self._get_stats(url, instance)["cluster_nodes"]
            member_endpoints = [urljoin(server, '_node/%s/') % member for member in members]
            couchdb['cluster_stats'] = {
                endpoint: self._get_node_stats(endpoint, instance)
                for endpoint in member_endpoints
            }
        else:
            couchdb['stats'] = self._get_node_stats(server, instance)

        # Next, get all database names.
        endpoint = '/_all_dbs/'

        url = urljoin(server, endpoint)

        # Get the list of whitelisted databases.
        db_whitelist = instance.get('db_whitelist')
        self.db_blacklist.setdefault(server, [])
        self.db_blacklist[server].extend(instance.get('db_blacklist', []))
        whitelist = set(db_whitelist) if db_whitelist else None
        databases = set(self._get_stats(url, instance)) - set(self.db_blacklist[server])
        databases = databases.intersection(whitelist) if whitelist else databases

        if len(databases) > self.MAX_DB:
            self.warning('Too many databases, only the first %s will be checked.' % self.MAX_DB)
            databases = list(databases)[:self.MAX_DB]

        for dbName in databases:
            url = urljoin(server, quote(dbName, safe=''))
            try:
                db_stats = self._get_stats(url, instance)
            except requests.exceptions.HTTPError as e:
                couchdb['databases'][dbName] = None
                if (e.response.status_code == 403) or (e.response.status_code == 401):
                    self.db_blacklist[server].append(dbName)
                    self.warning('Database %s is not readable by the configured user. It will be added to the blacklist. Please restart the agent to clear.' % dbName)
                    del couchdb['databases'][dbName]
                    continue
            if db_stats is not None:
                couchdb['databases'][dbName] = db_stats
        return couchdb
