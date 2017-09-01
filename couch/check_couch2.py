# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from urlparse import urljoin

# 3rd party
import requests

# project
from checks import AgentCheck

class CouchDB2:

    SERVICE_CHECK_NAME = 'couchdb2.can_connect'

    def __init__(self, agent_check, name, init_config, agentConfig, instances=None):
        self.agent_check = agent_check

    def _build_metrics(self, data, tags, prefix = 'couchdb'):
        for key, value in data.items():
            if "type" in value:
                if value["type"] == "histogram":
                    for metric, value in value["value"].items():
                        if metric == "histogram":
                            continue
                        elif metric == "percentile":
                            for pair in value:
                                self.agent_check.gauge("{0}.{1}.percentile.{2}".format(prefix, key, pair[0]), pair[1], tags=tags)
                        else:
                            self.agent_check.gauge("{0}.{1}.{2}".format(prefix, key, metric), value, tags=tags)
                else:
                    self.agent_check.gauge("{0}.{1}".format(prefix, key), value["value"], tags=tags)
            elif type(value) is dict:
                self._build_metrics(value, tags, "{0}.{1}".format(prefix, key))


    def _build_db_metrics(self, data, tags):
        for key, value in data['sizes'].items():
            self.agent_check.gauge("couchdb.by_db.{0}_size".format(key), value, tags)

        for key in ['purge_seq', 'doc_del_count', 'doc_count']:
            self.agent_check.gauge("couchdb.by_db.{0}".format(key), data[key], tags)

    def check(self, instance):
        server = self.agent_check.get_server(instance)

        name = instance.get('name', None)
        if name is None:
            raise Exception("At least one name is required")

        tags = ["instance:{0}".format(name)]
        self._build_metrics(self._get_node_stats(server, name, instance, tags), tags)

        db_whitelist = instance.get('db_whitelist', None)
        for db in self.agent_check.get(urljoin(server, "/_all_dbs"), instance):
            if db_whitelist is None or db in db_whitelist:
                tags = ["instance:{0}".format(name), "db:{0}".format(db)]
                self._build_db_metrics(self.agent_check.get(urljoin(server, db), instance), tags)

    def _get_node_stats(self, server, name, instance, tags):
        url = urljoin(server, "/_node/{}/_stats".format(name))

        # Fetch initial stats and capture a service check based on response.
        stats = None
        try:
            stats = self.agent_check.get(url, instance)
        except requests.exceptions.Timeout as e:
            self.agent_check.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                tags=tags, message="Request timeout: {0}, {1}".format(url, e))
            raise
        except requests.exceptions.HTTPError as e:
            self.agent_check.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                tags=tags, message=str(e.message))
            raise
        except Exception as e:
            self.agent_check.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                tags=tags, message=str(e))
            raise
        else:
            self.agent_check.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK,
                tags=tags, message='Connection to %s was successful' % url)

        # No overall stats? bail out now
        if stats is None:
            raise Exception("No stats could be retrieved from %s" % url)

        return stats
