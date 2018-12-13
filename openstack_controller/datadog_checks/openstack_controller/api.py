# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import requests
import simplejson as json
from datadog_checks.config import is_affirmative
from six.moves.urllib.parse import urljoin

from .settings import (DEFAULT_API_REQUEST_TIMEOUT, DEFAULT_KEYSTONE_API_VERSION, DEFAULT_NEUTRON_API_VERSION,
                       DEFAULT_PAGINATED_SERVER_LIMIT)
from .exceptions import (IncompleteConfig, IncompleteIdentity, MissingNovaEndpoint,
                         MissingNeutronEndpoint, InstancePowerOffFailure, AuthenticationNeeded, KeystoneUnreachable)


UNSCOPED_AUTH = 'unscoped'


class ApiFactory(object):

    @staticmethod
    def create(logger, proxy_config, instance_config):
        return SimpleApi(logger, proxy_config, instance_config)


class AbstractApi(object):
    def __init__(self, logger):
        self.logger = logger

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

    def __init__(self, logger, proxy_config, instance_config):
        super(SimpleApi, self).__init__(logger)

        self.identity_endpoint = instance_config.get("keystone_server_url")
        if not self.identity_endpoint:
            raise IncompleteConfig()

        self.ssl_verify = is_affirmative(instance_config.get("ssl_verify", True))
        self.proxy_config = proxy_config
        self.paginated_server_limit = instance_config.get('paginated_server_limit') or DEFAULT_PAGINATED_SERVER_LIMIT
        self.timeout = instance_config.get('request_timeout') or DEFAULT_API_REQUEST_TIMEOUT

        # Make Password authentication with explicit unscoped authorization
        identity = SimpleApi._get_user_identity(instance_config)
        auth_token, _, _ = SimpleApi._get_auth_token_endpoints(logger, self.identity_endpoint, self.ssl_verify,
                                                               self.proxy_config, identity, self.timeout)
        self.headers = {'X-Auth-Token': auth_token}

        # List all projects using retrieved auth token
        projects = SimpleApi._get_auth_projects(logger, self.identity_endpoint, self.headers,
                                                self.ssl_verify, self.proxy_config, self.timeout)

        # Fetch auth_token and additional endpoints
        for project in projects:
            identity = {"methods": ['token'], "token": {"id": auth_token}}
            scope = {'project': {'id': project.get('id')}}
            # Make Token authentication with project id scoped authorization
            self.auth_token, self.compute_endpoint, self.network_endpoint = SimpleApi._get_auth_token_endpoints(
                logger, self.identity_endpoint, self.ssl_verify, self.proxy_config, identity, self.timeout,
                scope=scope, return_endpoints=True)

            if self.compute_endpoint and self.network_endpoint:
                break

        if not self.compute_endpoint or not self.network_endpoint:
            self.logger.info("Endpoints not found, make sure you admin user has access to your OpenStack projects: \n")
            return
        self.logger.debug("Compute Url: %s", self.compute_endpoint)
        self.logger.debug("Network Url: %s", self.network_endpoint)

    @staticmethod
    def _get_auth_token_endpoints(logger, identity_endpoint, ssl_verify, proxy_config, identity, timeout,
                                  scope=UNSCOPED_AUTH, return_endpoints=False):
        auth_url = urljoin(identity_endpoint, "{}/auth/tokens".format(DEFAULT_KEYSTONE_API_VERSION))
        try:
            payload = {'auth': {'identity': identity, 'scope': scope}}
            headers = {'Content-Type': 'application/json'}

            resp = requests.post(
                auth_url,
                headers=headers,
                data=json.dumps(payload),
                verify=ssl_verify,
                timeout=timeout,
                proxies=proxy_config,
            )
            resp.raise_for_status()
            logger.debug("url: %s || response: %s", auth_url, resp.json())
            # Retrieved token, nova and neutron endpoints
            auth_token = resp.headers.get('X-Subject-Token')
            if return_endpoints:
                compute_endpoint = SimpleApi._get_compute_endpoint(resp.json())
                network_endpoint = SimpleApi._get_network_endpoint(resp.json())
                return auth_token, compute_endpoint, network_endpoint
            else:
                return auth_token, None, None
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            msg = "Failed keystone auth with identity:{identity} scope:{scope} @{url}".format(
                identity=identity,
                scope=scope,
                url=auth_url)
            logger.debug(msg)
            raise KeystoneUnreachable(msg)

    @staticmethod
    def _get_auth_projects(logger, keystone_server_url, headers, ssl_verify, proxy_config, timeout):
        auth_url = ""
        try:
            auth_url = urljoin(keystone_server_url, "{}/auth/projects".format(DEFAULT_KEYSTONE_API_VERSION))
            resp = requests.get(
                auth_url,
                headers=headers,
                verify=ssl_verify,
                timeout=timeout,
                proxies=proxy_config
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
    def _get_user_identity(instance_config):
        """
        Parse user identity out of init_config

        To guarantee a uniquely identifiable user, expects
        {"user": {"name": "my_username", "password": "my_password",
                  "domain": {"id": "my_domain_id"}
                  }
        }
        """
        user = instance_config.get('user')

        if not (user and user.get('name') and user.get('password') and user.get("domain")
                and user.get("domain").get("id")):
            raise IncompleteIdentity()

        identity = {"methods": ['password'], "password": {"user": user}}
        return identity

    @staticmethod
    def _get_network_endpoint(json_resp):
        """
        Parse the service catalog returned by the Identity API for an endpoint matching the Neutron service
        Sends a CRITICAL service check when none are found registered in the Catalog
        """
        valid_endpoint = SimpleApi._get_valid_endpoint(json_resp, 'neutron', 'network')
        if valid_endpoint:
            return valid_endpoint
        raise MissingNeutronEndpoint()

    @staticmethod
    def _get_compute_endpoint(json_resp):
        """
        Parse the service catalog returned by the Identity API for an endpoint matching
        the Nova service with the requested version
        Sends a CRITICAL service check when no viable candidates are found in the Catalog
        """
        valid_endpoint = SimpleApi._get_valid_endpoint(json_resp, 'nova', 'compute')
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

    def _make_request(self, url, headers, params=None):
        """
        Generic request handler for OpenStack API requests
        Raises specialized Exceptions for commonly encountered error codes
        """
        self.logger.debug("Request URL, Headers and Params: %s, %s, %s", url, headers, params)

        try:
            resp = requests.get(
                url,
                headers=headers,
                verify=self.ssl_verify,
                params=params,
                timeout=self.timeout,
                proxies=self.proxy_config,
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

        return jresp

    def get_os_hypervisor_uptime(self, hyp_id):
        url = '{}/os-hypervisors/{}/uptime'.format(self.compute_endpoint, hyp_id)
        resp = self._make_request(url, self.headers)
        return resp.get('hypervisor', {}).get('uptime')

    def get_os_aggregates(self):
        url = '{}/os-aggregates'.format(self.compute_endpoint)
        aggregate_list = self._make_request(url, self.headers)
        return aggregate_list.get('aggregates', [])

    def get_os_hypervisors_detail(self):
        url = '{}/os-hypervisors/detail'.format(self.compute_endpoint)
        return self._make_request(url, self.headers)

    def get_servers_detail(self, query_params):
        servers = []
        query_params = query_params or {}
        query_params['limit'] = self.paginated_server_limit
        resp = self._get_servers_detail(query_params)
        servers.extend(resp)
        # Avoid the extra request since we know we're done when the response has anywhere between
        # 0 and paginated_server_limit servers
        while len(resp) == self.paginated_server_limit:
            query_params['marker'] = resp[-1]['id']
            resp = self._get_servers_detail(query_params)
            servers.extend(resp)
        return servers

    def _get_servers_detail(self, query_params):
        url = '{}/servers/detail'.format(self.compute_endpoint)
        resp = self._make_request(url, self.headers, params=query_params)
        return resp.get('servers', [])

    def get_server_diagnostics(self, server_id):
        url = '{}/servers/{}/diagnostics'.format(self.compute_endpoint, server_id)
        return self._make_request(url, self.headers)

    def get_project_limits(self, tenant_id):
        url = '{}/limits'.format(self.compute_endpoint)
        server_stats = self._make_request(url, self.headers, params={"tenant_id": tenant_id})
        limits = server_stats.get('limits', {}).get('absolute', {})
        return limits

    def get_flavors_detail(self, query_params):
        flavors = []
        query_params = query_params or {}
        query_params['limit'] = self.paginated_server_limit
        resp = self._get_flavors_detail(query_params)
        flavors.extend(resp)
        # Avoid the extra request since we know we're done when the response has anywhere between
        # 0 and paginated_server_limit servers
        while len(resp) == self.paginated_server_limit:
            query_params['marker'] = resp[-1]['id']
            resp = self._get_flavors_detail(query_params)
            flavors.extend(resp)
        return flavors

    def _get_flavors_detail(self, query_params):
        url = '{}/flavors/detail'.format(self.compute_endpoint)
        flavors = self._make_request(url, self.headers, params=query_params)
        return flavors.get('flavors', [])

    def get_networks(self):
        url = '{}/{}/networks'.format(self.network_endpoint, DEFAULT_NEUTRON_API_VERSION)

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
        url = urljoin(self.identity_endpoint, "{}/{}".format(DEFAULT_KEYSTONE_API_VERSION, "projects"))
        try:
            r = self._make_request(url, self.headers)
            return r.get('projects', [])

        except Exception as e:
            self.logger.warning('Unable to get projects: {}'.format(e))
            raise e
