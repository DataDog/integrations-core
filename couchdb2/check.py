# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from urlparse import urljoin

# 3rd party
import requests

# project
from checks import AgentCheck
from util import headers

EVENT_TYPE = SOURCE_TYPE_NAME = 'couchdb2'


class Couchdb2Check(AgentCheck):

    SERVICE_CHECK_NAME = 'couchdb2.can_connect'
    TIMEOUT = 5

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

    def _build_metrics(self, data, tags, prefix = 'couchdb'):
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

    def check(self, instance):
        server = instance.get('host', None)
        if server is None:
            raise Exception("A host must be given")

        tags=['instance:%s' % server]
        self._build_metrics(self._get_node_stats(server, instance), tags)


    def _get_node_stats(self, server, instance):
        server = "{0}:{1}".format(server, instance.get('backdoor', 5986))
        url = urljoin(server, '/_stats')

        # Fetch initial stats and capture a service check based on response.
        service_check_tags = ['instance:%s' % server]
        stats = None
        try:
            stats = self._get(url, instance)
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
        if stats is None:
            raise Exception("No stats could be retrieved from %s" % url)

        return stats

    def _get(self, url, instance):
        "Hit a given URL and return the parsed json"
        self.log.debug('Fetching CouchDB stats at url: %s' % url)

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

