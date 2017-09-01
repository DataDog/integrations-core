# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib

# 3rd party
import requests

# project
from checks import AgentCheck
from util import headers
from check_couch1 import CouchDB1
from check_couch2 import CouchDB2

class CouchDb(AgentCheck):

    TIMEOUT = 5

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        version = init_config.get('version', '1.x')
        self.checker = None
        if version.startswith('1.'):
            self.checker = CouchDB1(self, name, init_config, agentConfig, instances)
        elif version.startswith('2.'):
            self.checker = CouchDB2(self, name, init_config, agentConfig, instances)
        else:
            raise Exception("Unkown version {0}".format(version))

    def get(self, url, instance):
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

    def check(self, instance):
        self.checker.check(instance)

    def get_server(self, instance):
        server = instance.get('server', None)
        if server is None:
            raise Exception("A server must be specified")
        return server
