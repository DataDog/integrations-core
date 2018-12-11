# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import requests
from datadog_checks.checks import AgentCheck
from datadog_checks.utils.headers import headers

from . import errors

from .one import CouchDB1
from .two import CouchDB2


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
