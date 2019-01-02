# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import requests
import simplejson as json

from six.moves.urllib.parse import urljoin
from datadog_checks.config import is_affirmative

from .settings import (DEFAULT_API_REQUEST_TIMEOUT, DEFAULT_KEYSTONE_API_VERSION, DEFAULT_NEUTRON_API_VERSION,
                       DEFAULT_PAGINATED_LIMIT, DEFAULT_MAX_RETRY)
from .exceptions import (InstancePowerOffFailure, AuthenticationNeeded, KeystoneUnreachable, MissingNovaEndpoint,
                         MissingNeutronEndpoint, IncompleteIdentity)

UNSCOPED_AUTH = 'unscoped'


class ApiFactory(object):

    @staticmethod
    def create(logger, proxies, instance_config):
        keystone_server_url = instance_config.get("keystone_server_url")
        ssl_verify = is_affirmative(instance_config.get("ssl_verify", True))
        paginated_limit = instance_config.get('paginated_limit')
        request_timeout = instance_config.get('request_timeout')
        user = instance_config.get("user")

        api = SimpleApi(logger, keystone_server_url, timeout=request_timeout, ssl_verify=ssl_verify, proxies=proxies,
                        limit=paginated_limit)
        api.connect(user)
        return api


class AbstractApi(object):
    def __init__(self, logger):
        self.logger = logger

    def get_keystone_endpoint(self):
        raise NotImplementedError()

    def get_nova_endpoint(self):
        raise NotImplementedError()

    def get_neutron_endpoint(self):
        raise NotImplementedError()

    def get_projects(self):
        raise NotImplementedError()

    def get_os_hypervisor_uptime(self, hypervisor_id):
        raise NotImplementedError()

    def get_os_aggregates(self):
        raise NotImplementedError()

    def get_os_hypervisors_detail(self):
        raise NotImplementedError()

    def get_servers_detail(self, query_params):
        raise NotImplementedError()

    def get_flavors_detail(self, query_params):
        raise NotImplementedError()

    def get_server_diagnostics(self, server_id):
        raise NotImplementedError()

    def get_project_limits(self, project_id):
        raise NotImplementedError()

    def get_networks(self):
        raise NotImplementedError()


class SimpleApi(AbstractApi):
    def __init__(self, logger, keystone_endpoint, ssl_verify=False, proxies=None,
                 timeout=DEFAULT_API_REQUEST_TIMEOUT, limit=DEFAULT_PAGINATED_LIMIT):
        super(SimpleApi, self).__init__(logger)

        self.keystone_endpoint = keystone_endpoint
        self.ssl_verify = ssl_verify
        self.proxies = proxies
        self.timeout = timeout
        self.paginated_limit = limit
        self.nova_endpoint = None
        self.neutron_endpoint = None
        self.auth_token = None
        self.headers = None
        # Cache for the `_make_request` method
        self.cache = {}

    def connect(self, user):
        credentials = Authenticator.from_config(self.logger, self.keystone_endpoint, user, self.ssl_verify,
                                                self.proxies, self.timeout)
        self.logger.debug("Nova Url: %s", credentials.nova_endpoint)
        self.nova_endpoint = credentials.nova_endpoint
        self.logger.debug("Neutron Url: %s", credentials.neutron_endpoint)
        self.neutron_endpoint = credentials.neutron_endpoint
        self.auth_token = credentials.auth_token
        self.headers = {'X-Auth-Token': credentials.auth_token}

    def _make_request(self, url, headers, params=None):
        """
        Generic request handler for OpenStack API requests
        Raises specialized Exceptions for commonly encountered error codes
        """
        self.logger.debug("Request URL, Headers and Params: %s, %s, %s", url, headers, params)

        # Checking if request is in cache
        cache_key = "|".join([url, json.dumps(headers), json.dumps(params), str(self.timeout)])
        if cache_key in self.cache:
            self.logger.debug("Request found in cache. cache key %s", cache_key)
            return self.cache.get(cache_key)

        try:
            resp = requests.get(
                url,
                headers=headers,
                verify=self.ssl_verify,
                params=params,
                timeout=self.timeout,
                proxies=self.proxies,
            )
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            self.logger.debug("Error contacting openstack endpoint: %s", e)
            if resp.status_code == 401:
                self.logger.info('Need to reauthenticate before next check')
                raise AuthenticationNeeded()
            elif resp.status_code == 409:
                raise InstancePowerOffFailure()
            else:
                raise e
        jresp = resp.json()
        self.logger.debug("url: %s || response: %s", url, jresp)

        # Adding response to the cache
        self.cache[cache_key] = jresp
        return jresp

    def get_keystone_endpoint(self):
        self._make_request(self.keystone_endpoint, self.headers)

    def get_nova_endpoint(self):
        self._make_request(self.nova_endpoint, self.headers)

    def get_neutron_endpoint(self):
        self._make_request(self.neutron_endpoint, self.headers)

    def get_os_hypervisor_uptime(self, hyp_id):
        url = '{}/os-hypervisors/{}/uptime'.format(self.nova_endpoint, hyp_id)
        resp = self._make_request(url, self.headers)
        return resp.get('hypervisor', {}).get('uptime')

    def get_os_aggregates(self):
        url = '{}/os-aggregates'.format(self.nova_endpoint)
        aggregate_list = self._make_request(url, self.headers)
        return aggregate_list.get('aggregates', [])

    def get_os_hypervisors_detail(self):
        url = '{}/os-hypervisors/detail'.format(self.nova_endpoint)
        hypervisors = self._make_request(url, self.headers)
        return hypervisors.get('hypervisors', [])

    def get_servers_detail(self, query_params):
        url = '{}/servers/detail'.format(self.nova_endpoint)
        return self._get_paginated_list(url, 'servers', query_params)

    def get_server_diagnostics(self, server_id):
        url = '{}/servers/{}/diagnostics'.format(self.nova_endpoint, server_id)
        return self._make_request(url, self.headers)

    def get_project_limits(self, tenant_id):
        url = '{}/limits'.format(self.nova_endpoint)
        server_stats = self._make_request(url, self.headers, params={"tenant_id": tenant_id})
        limits = server_stats.get('limits', {}).get('absolute', {})
        return limits

    def get_flavors_detail(self, query_params):
        url = '{}/flavors/detail'.format(self.nova_endpoint)
        return self._get_paginated_list(url, 'flavors', query_params)

    def _get_paginated_list(self, url, obj, query_params):
        result = []
        query_params = query_params or {}
        query_params['limit'] = self.paginated_limit
        resp = self._make_request(url, self.headers, params=query_params)
        result.extend(resp.get(obj, []))
        # Avoid the extra request since we know we're done when the response has anywhere between
        # 0 and paginated_server_limit servers
        while len(resp) == self.paginated_limit:
            query_params['marker'] = resp[-1]['id']
            query_params['limit'] = self.paginated_limit
            retry = 0
            while retry < DEFAULT_MAX_RETRY:
                # `details` endpoints are typically expensive calls,
                # If it fails, we retry DEFAULT_RETRY times while reducing the `limit` param
                # otherwise we will backoff
                try:
                    resp = self._make_request(url, self.headers, params=query_params)
                    result.extend(resp.get(obj, []))

                    break
                except Exception as e:
                    query_params['limit'] /= 2
                    retry += 1
                    if retry == DEFAULT_MAX_RETRY:
                        raise e

        return result

    def get_networks(self):
        url = '{}/{}/networks'.format(self.neutron_endpoint, DEFAULT_NEUTRON_API_VERSION)

        try:
            networks = self._make_request(url, self.headers)
            return networks.get('networks')
        except Exception as e:
            self.logger.warning('Unable to get the list of all network ids: {}'.format(e))
            raise e

    def get_projects(self):
        """
        Returns all projects in the domain
        """
        url = urljoin(self.keystone_endpoint, "{}/{}".format(DEFAULT_KEYSTONE_API_VERSION, "projects"))
        try:
            r = self._make_request(url, self.headers)
            return r.get('projects', [])

        except Exception as e:
            self.logger.warning('Unable to get projects: {}'.format(e))
            raise e


class Authenticator(object):
    def __init__(self):
        pass

    @classmethod
    def from_config(cls, logger, keystone_endpoint, user, ssl_verify=False, proxies=None,
                    timeout=DEFAULT_API_REQUEST_TIMEOUT):
        # Make Token authentication with explicit unscoped authorization
        identity = cls._get_user_identity(user)
        post_auth_token_resp = cls._post_auth_token(logger, keystone_endpoint, identity, ssl_verify=ssl_verify,
                                                    proxies=proxies, timeout=timeout, scope=UNSCOPED_AUTH)
        keystone_auth_token = post_auth_token_resp.headers.get('X-Subject-Token')
        # List all projects using retrieved auth token
        headers = {'X-Auth-Token': keystone_auth_token}
        projects = cls._get_auth_projects(logger, keystone_endpoint, headers=headers, ssl_verify=ssl_verify,
                                          proxies=proxies, timeout=timeout)

        # For each project, we create an OpenStackProject object that we add to the `project_scopes` dict
        last_auth_token = None
        last_project_auth_scope = None
        last_nova_endpoint = None
        last_neutron_endpoint = None
        for project in projects:
            identity = {"methods": ['token'], "token": {"id": keystone_auth_token}}
            scope = {'project': {'id': project.get('id')}}
            # Make Token authentication with project id scoped authorization
            token_resp = cls._post_auth_token(logger, keystone_endpoint, identity, ssl_verify=ssl_verify,
                                              proxies=proxies, timeout=timeout, scope=scope)

            # Retrieved token, nova and neutron endpoints
            auth_token = token_resp.headers.get('X-Subject-Token')
            nova_endpoint = cls._get_nova_endpoint(token_resp.json())
            neutron_endpoint = cls._get_neutron_endpoint(token_resp.json())
            project_auth_scope = {
                'project': {
                    'name': project.get('name'),
                    'id': project.get('id'),
                    'domain': {} if project.get('domain_id') is None else {'id': project.get('domain_id')},
                }
            }

            project_name = project.get('name')
            project_id = project.get('id')
            if project_name is not None and project_id is not None:
                last_auth_token = auth_token
                last_project_auth_scope = project_auth_scope
                last_nova_endpoint = nova_endpoint
                last_neutron_endpoint = neutron_endpoint

        if last_auth_token and last_project_auth_scope and last_nova_endpoint and last_neutron_endpoint:
            return Credential(last_auth_token, last_project_auth_scope, last_nova_endpoint, last_neutron_endpoint)

        return None

    @staticmethod
    def _post_auth_token(logger, keystone_endpoint, identity, ssl_verify=False, proxies=None,
                         timeout=DEFAULT_API_REQUEST_TIMEOUT, scope=UNSCOPED_AUTH):
        auth_url = urljoin(keystone_endpoint, "{}/auth/tokens".format(DEFAULT_KEYSTONE_API_VERSION))
        try:
            payload = {'auth': {'identity': identity, 'scope': scope}}
            headers = {'Content-Type': 'application/json'}

            resp = requests.post(
                auth_url,
                headers=headers,
                data=json.dumps(payload),
                verify=ssl_verify,
                timeout=timeout,
                proxies=proxies,
            )
            resp.raise_for_status()
            logger.debug("url: %s || response: %s", auth_url, resp.json())
            return resp

        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            msg = "Failed keystone auth with identity:{identity} scope:{scope} @{url}".format(
                identity=identity,
                scope=scope,
                url=auth_url)
            logger.debug(msg)
            raise KeystoneUnreachable(msg)

    @staticmethod
    def _get_auth_projects(logger, keystone_endpoint, headers=None, ssl_verify=False, proxies=None,
                           timeout=DEFAULT_API_REQUEST_TIMEOUT):
        auth_url = ""
        try:
            auth_url = urljoin(keystone_endpoint, "{}/auth/projects".format(DEFAULT_KEYSTONE_API_VERSION))
            resp = requests.get(
                auth_url,
                headers=headers,
                verify=ssl_verify,
                timeout=timeout,
                proxies=proxies
            )
            resp.raise_for_status()
            jresp = resp.json()
            logger.debug("url: %s || response: %s", auth_url, jresp)
            projects = jresp.get('projects')
            return projects
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            msg = "unable to retrieve project list from keystone auth with identity: @{url}: {ex}".format(
                    url=auth_url,
                    ex=e)
            logger.debug(msg)
            raise KeystoneUnreachable(msg)

    @staticmethod
    def _get_user_identity(user):
        """
        Parse user identity out of init_config

        To guarantee a uniquely identifiable user, expects
        {"user": {"name": "my_username", "password": "my_password",
                  "domain": {"id": "my_domain_id"}
                  }
        }
        """
        if not (user and user.get('name') and user.get('password') and user.get("domain")
                and user.get("domain").get("id")):
            raise IncompleteIdentity()

        identity = {"methods": ['password'], "password": {"user": user}}
        return identity

    @classmethod
    def _get_neutron_endpoint(cls, json_resp):
        """
        Parse the service catalog returned by the Identity API for an endpoint matching the Neutron service
        Sends a CRITICAL service check when none are found registered in the Catalog
        """
        valid_endpoint = cls._get_valid_endpoint(json_resp, 'neutron', 'network')
        if valid_endpoint:
            return valid_endpoint
        raise MissingNeutronEndpoint()

    @classmethod
    def _get_nova_endpoint(cls, json_resp):
        """
        Parse the service catalog returned by the Identity API for an endpoint matching
        the Nova service with the requested version
        Sends a CRITICAL service check when no viable candidates are found in the Catalog
        """
        valid_endpoint = cls._get_valid_endpoint(json_resp, 'nova', 'compute')
        if valid_endpoint:
            return valid_endpoint
        raise MissingNovaEndpoint()

    @staticmethod
    def _get_valid_endpoint(resp, name, entry_type):
        """
        Parse the service catalog returned by the Identity API for an endpoint matching
        the Nova service with the requested version
        Sends a CRITICAL service check when no viable candidates are found in the Catalog
        """
        catalog = resp.get('token', {}).get('catalog', [])
        for entry in catalog:
            if entry.get('name') and entry.get('type') and entry.get('name') == name and \
                            entry.get('type') == entry_type:
                # Collect any endpoints on the public or internal interface
                valid_endpoints = {}
                for ep in entry.get('endpoints'):
                    interface = ep.get('interface', '')
                    if interface in ['public', 'internal']:
                        valid_endpoints[interface] = ep.get('url')

                if valid_endpoints:
                    # Favor public endpoints over internal
                    return valid_endpoints.get('public', valid_endpoints.get('internal'))

        return None


class Credential(object):
    def __init__(self, auth_token, auth_scope, nova_endpoint, neutron_endpoint):
        self.auth_token = auth_token
        self.name = auth_scope.get("project", {}).get("name")
        self.domain_id = auth_scope.get("project", {}).get("domain", {}).get("id")
        self.tenant_id = auth_scope.get("project", {}).get("id")
        self.nova_endpoint = nova_endpoint
        self.neutron_endpoint = neutron_endpoint
