# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import requests
import simplejson as json
from six.moves.urllib.parse import urljoin
from .settings import DEFAULT_API_REQUEST_TIMEOUT, DEFAULT_KEYSTONE_API_VERSION, DEFAULT_NEUTRON_API_VERSION
from .exceptions import (InstancePowerOffFailure, AuthenticationNeeded, KeystoneUnreachable)


UNSCOPED_AUTH = 'unscoped'


class AbstractApi(object):
    DEFAULT_API_REQUEST_TIMEOUT = 10  # seconds

    def __init__(self, logger, ssl_verify, proxy_config):
        self.logger = logger
        self.ssl_verify = ssl_verify
        self.proxy_config = proxy_config
        # Cache for the `_make_request` method
        self.cache = {}

    def _make_request(self, url, headers, params=None, timeout=DEFAULT_API_REQUEST_TIMEOUT):
        """
        Generic request handler for OpenStack API requests
        Raises specialized Exceptions for commonly encountered error codes
        """
        self.logger.debug("Request URL, Headers and Params: %s, %s, %s", url, headers, params)

        # Checking if request is in cache
        cache_key = "|".join([url, json.dump(headers), json.dump(params), timeout])
        if cache_key in self.cache:
            self.logger.debug("Request found in cache. cache key %s", cache_key)
            return self.cache.get(cache_key)

        resp = {}
        try:
            resp = requests.get(
                url,
                headers=headers,
                verify=self.ssl_verify,
                params=params,
                timeout=timeout,
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
        self.logger.debug("url: %s || response: %s", url, resp.json())
        jresp = resp.json()

        # Adding response to the cache
        self.cache[cache_key] = jresp
        return jresp


class ComputeApi(AbstractApi):
    def __init__(self, logger, ssl_verify, proxy_config, endpoint, auth_token):
        AbstractApi.__init__(self, logger, ssl_verify, proxy_config)
        self.endpoint = endpoint
        self.auth_token = auth_token

    def get_os_hypervisor_uptime(self, hyp_id):
        url = '{}/os-hypervisors/{}/uptime'.format(self.endpoint, hyp_id)
        headers = {'X-Auth-Token': self.auth_token}
        resp = self._make_request(url, headers)
        return resp.get('hypervisor', {}).get('uptime')

    def get_os_aggregates(self):
        url = '{}/os-aggregates'.format(self.endpoint)
        headers = {'X-Auth-Token': self.auth_token}
        aggregate_list = self._make_request(url, headers)
        return aggregate_list.get('aggregates', [])

    def get_os_hypervisors_detail(self):
        url = '{}/os-hypervisors/detail'.format(self.endpoint)
        headers = {'X-Auth-Token': self.auth_token}
        return self._make_request(url, headers)

    def get_servers_detail(self, query_params, timeout=None):
        url = '{}/servers/detail'.format(self.endpoint)
        headers = {'X-Auth-Token': self.auth_token}
        resp = self._make_request(url, headers, params=query_params, timeout=timeout)
        return resp.get('servers', [])

    def get_server_diagnostics(self, server_id):
        url = '{}/servers/{}/diagnostics'.format(self.endpoint, server_id)
        headers = {'X-Auth-Token': self.auth_token}
        return self._make_request(url, headers)

    def get_project_limits(self, tenant_id):
        url = '{}/limits'.format(self.endpoint)
        headers = {'X-Auth-Token': self.auth_token}
        server_stats = self._make_request(url, headers, params={"tenant_id": tenant_id})
        limits = server_stats.get('limits', {}).get('absolute', {})
        return limits


class NeutronApi(AbstractApi):
    def __init__(self, logger, ssl_verify, proxy_config, endpoint, auth_token):
        AbstractApi.__init__(self, logger, ssl_verify, proxy_config)
        self.endpoint = endpoint
        self.auth_token = auth_token

    def get_network_ids(self):
        url = '{}/{}/networks'.format(self.endpoint, DEFAULT_NEUTRON_API_VERSION)
        headers = {'X-Auth-Token': self.auth_token}

        network_ids = []
        try:
            net_details = self._make_request(url, headers)
            for network in net_details['networks']:
                network_ids.append(network['id'])
        except Exception as e:
            self.logger.warning('Unable to get the list of all network ids: {}'.format(e))
            raise e

        return network_ids

    def get_network_details(self, network_id):
        url = '{}/{}/networks/{}'.format(self.endpoint, DEFAULT_NEUTRON_API_VERSION, network_id)
        headers = {'X-Auth-Token': self.auth_token}
        return self._make_request(url, headers)


class KeystoneApi(AbstractApi):
    def __init__(self, logger, ssl_verify, proxy_config, endpoint, auth_token):
        AbstractApi.__init__(self, logger, ssl_verify, proxy_config)
        self.endpoint = endpoint
        self.auth_token = auth_token

    def post_auth_token(self, identity, scope=UNSCOPED_AUTH):
        auth_url = urljoin(self.endpoint, "{}/auth/tokens".format(DEFAULT_KEYSTONE_API_VERSION))
        try:
            payload = {'auth': {'identity': identity, 'scope': scope}}
            headers = {'Content-Type': 'application/json'}

            resp = requests.post(
                auth_url,
                headers=headers,
                data=json.dumps(payload),
                verify=self.ssl_verify,
                timeout=DEFAULT_API_REQUEST_TIMEOUT,
                proxies=self.proxy_config,
            )
            resp.raise_for_status()
            return resp

        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            msg = "Failed keystone auth with identity:{identity} scope:{scope} @{url}".format(
                identity=identity,
                scope=scope,
                url=auth_url)
            self.logger.debug(msg)
            raise KeystoneUnreachable(msg)

    def get_auth_projects(self):
        auth_url = ""
        try:
            auth_url = urljoin(self.endpoint, "{}/auth/projects".format(DEFAULT_KEYSTONE_API_VERSION))
            headers = {'X-Auth-Token': self.auth_token}

            resp = requests.get(
                auth_url,
                headers=headers,
                verify=self.ssl_verify,
                timeout=DEFAULT_API_REQUEST_TIMEOUT,
                proxies=self.proxy_config
            )
            resp.raise_for_status()
            self.logger.debug("url: %s || response: %s", auth_url, resp.json().get('projects'))
            return resp.json().get('projects')
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            msg = "unable to retrieve project list from keystone auth with identity: @{url}: {ex}".format(
                    url=auth_url,
                    ex=e)
            self.logger.debug(msg)
            raise KeystoneUnreachable(msg)

    def get_projects(self, project_token):
        """
        Returns all projects in the domain
        """
        # TODO: Is this call needed, we loop over all project and then call keystone for projects by giving
        # the project token (not keystone)
        url = urljoin(self.endpoint, "{}/{}".format(DEFAULT_KEYSTONE_API_VERSION, "projects"))
        headers = {'X-Auth-Token': project_token}
        try:
            r = self._make_request(url, headers)
            self.logger.debug("url: %s || response: %s", url, json.dumps(r['projects']))
            return r['projects']

        except Exception as e:
            self.logger.warning('Unable to get projects: {}'.format(e))
            raise e

    def get_project_name_from_id(self, project_token, project_id):
        url = urljoin(self.endpoint, "{}/{}/{}".format(DEFAULT_KEYSTONE_API_VERSION, "projects", project_id))
        self.logger.debug("Project URL is %s", url)
        headers = {'X-Auth-Token': project_token}
        try:
            r = self._make_request(url, headers)
            return r.get('project', {})['name']

        except Exception as e:
            self.logger.warning('Unable to get project name: {}'.format(e))
            return None

    def get_project_details(self, tenant_id, project_name, domain_id):
        """
        Returns the project that this instance of the check is scoped to
        """
        filter_params = {}
        url = urljoin(self.endpoint, "{}/{}".format(DEFAULT_KEYSTONE_API_VERSION, "projects"))
        if tenant_id:
            if project_name:
                return {"id": tenant_id, "name": project_name}, None, None

            url = "{}/{}".format(url, tenant_id)
        else:
            filter_params = {"name": project_name, "domain_id": domain_id}

        headers = {'X-Auth-Token': self.auth_token}
        project_details = self._make_request(url, headers, params=filter_params)

        if filter_params:
            if len(project_details["projects"]) > 1:
                self.logger.error("Non-unique project credentials for filter_params: %s", filter_params)
                raise RuntimeError("Non-unique project credentials")
            project = project_details["projects"][0]
        else:
            project = project_details["project"]

        return project, project.get("id"), project.get("name")
