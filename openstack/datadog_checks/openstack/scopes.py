# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from urlparse import urljoin
import requests
import simplejson as json

from datadog_checks.config import is_affirmative

from .settings import DEFAULT_API_REQUEST_TIMEOUT, DEFAULT_KEYSTONE_API_VERSION
from .exceptions import (IncompleteConfig, IncompleteIdentity, MissingNovaEndpoint,
                         MissingNeutronEndpoint, KeystoneUnreachable)


UNSCOPED_AUTH = 'unscoped'
V21_NOVA_API_VERSION = 'v2.1'
DEFAULT_NOVA_API_VERSION = V21_NOVA_API_VERSION


class OpenStackScope(object):
    def __init__(self, auth_token, project_scope_map):
        self.auth_token = auth_token
        self.project_scope_map = project_scope_map

    @classmethod
    def _request_auth_token(cls, identity, keystone_server_url, ssl_verify, proxy=None):
        payload = {'auth': {'identity': identity, 'scope': UNSCOPED_AUTH}}
        auth_url = urljoin(keystone_server_url, "{}/auth/tokens".format(DEFAULT_KEYSTONE_API_VERSION))
        headers = {'Content-Type': 'application/json'}

        resp = requests.post(
            auth_url,
            headers=headers,
            data=json.dumps(payload),
            verify=ssl_verify,
            timeout=DEFAULT_API_REQUEST_TIMEOUT,
            proxies=proxy,
        )
        resp.raise_for_status()

        return resp

    @classmethod
    def _get_user_identity(cls, instance_config):
        """
        Parse user identity out of init_config

        To guarantee a uniquely identifiable user, expects
        {"user": {"name": "my_username", "password": "my_password",
                  "domain": {"id": "my_domain_id"}
                  }
        }
        """
        user = instance_config.get('user')

        if not (
            user and user.get('name') and user.get('password') and user.get("domain") and user.get("domain").get("id")
        ):
            raise IncompleteIdentity()

        identity = {"methods": ['password'], "password": {"user": user}}
        return identity

    @classmethod
    def _get_auth_response_from_config(cls, init_config, instance_config, proxy_config=None):
        keystone_server_url = init_config.get("keystone_server_url")
        if not keystone_server_url:
            raise IncompleteConfig()

        ssl_verify = is_affirmative(init_config.get("ssl_verify", False))
        identity = cls._get_user_identity(instance_config)

        exception_msg = None
        try:
            auth_resp = cls._request_auth_token(identity, keystone_server_url, ssl_verify, proxy_config)
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            exception_msg = "Failed keystone auth with user:{user} domain:{domain} scope:{scope} @{url}".format(
                user=identity['password']['user']['name'],
                domain=identity['password']['user']['domain']['id'],
                scope=UNSCOPED_AUTH,
                url=keystone_server_url,
            )
        if exception_msg:
            try:
                identity['password']['user']['domain']['name'] = identity['password']['user']['domain'].pop('id')
                auth_resp = cls._request_auth_token(identity, keystone_server_url, ssl_verify, proxy_config)
            except (
                requests.exceptions.HTTPError,
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
            ) as e:
                exception_msg = "{msg} and also failed keystone auth with \
                identity:{user} domain:{domain} scope:{scope} @{url}: {ex}".format(
                    msg=exception_msg,
                    user=identity['password']['user']['name'],
                    domain=identity['password']['user']['domain']['name'],
                    scope=UNSCOPED_AUTH,
                    url=keystone_server_url,
                    ex=e,
                )
                raise KeystoneUnreachable(exception_msg)
        return auth_resp.headers.get('X-Subject-Token'), auth_resp

    @classmethod
    def _get_neutron_endpoint(cls, json_resp):
        """
        Parse the service catalog returned by the Identity API for an endpoint matching the Neutron service
        Sends a CRITICAL service check when none are found registered in the Catalog
        """
        catalog = json_resp.get('token', {}).get('catalog', [])
        match = 'neutron'

        neutron_endpoint = None
        for entry in catalog:
            if entry['name'] == match or 'Networking' in entry['name']:
                valid_endpoints = {}
                for ep in entry['endpoints']:
                    interface = ep.get('interface', '')
                    if interface in ['public', 'internal']:
                        valid_endpoints[interface] = ep['url']

                if valid_endpoints:
                    # Favor public endpoints over internal
                    neutron_endpoint = valid_endpoints.get("public", valid_endpoints.get("internal"))
                    break
        else:
            raise MissingNeutronEndpoint()

        return neutron_endpoint

    @classmethod
    def _get_nova_endpoint(cls, json_resp, nova_api_version=None):
        """
        Parse the service catalog returned by the Identity API for an endpoint matching
        the Nova service with the requested version
        Sends a CRITICAL service check when no viable candidates are found in the Catalog
        """
        nova_version = nova_api_version or DEFAULT_NOVA_API_VERSION
        catalog = json_resp.get('token', {}).get('catalog', [])

        nova_match = 'novav21' if nova_version == V21_NOVA_API_VERSION else 'nova'

        for entry in catalog:
            if entry['name'] == nova_match or 'Compute' in entry['name']:
                # Collect any endpoints on the public or internal interface
                valid_endpoints = {}
                for ep in entry['endpoints']:
                    interface = ep.get('interface', '')
                    if interface in ['public', 'internal']:
                        valid_endpoints[interface] = ep['url']

                if valid_endpoints:
                    # Favor public endpoints over internal
                    nova_endpoint = valid_endpoints.get("public", valid_endpoints.get("internal"))
                    return nova_endpoint
        else:
            raise MissingNovaEndpoint()

    @classmethod
    def from_config(cls, init_config, instance_config, proxy_config=None):
        keystone_server_url = init_config.get("keystone_server_url")
        if not keystone_server_url:
            raise IncompleteConfig()

        ssl_verify = is_affirmative(init_config.get("ssl_verify", True))
        nova_api_version = init_config.get("nova_api_version", DEFAULT_NOVA_API_VERSION)
        auth_token, _ = cls._get_auth_response_from_config(init_config, instance_config, proxy_config)

        try:
            project_resp = cls._request_project_list(auth_token, keystone_server_url, ssl_verify, proxy_config)
            projects = project_resp.json().get('projects')
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            exception_msg = "unable to retrieve project list from keystone auth with identity: @{url}: {ex}".format(
                url=keystone_server_url, ex=e
            )
            raise KeystoneUnreachable(exception_msg)
        project_scope_map = {}
        for project in projects:
            try:
                project_key = project['name'], project['id']
                token_resp = cls._get_token_for_project(
                    auth_token, project, keystone_server_url, ssl_verify, proxy_config
                )
                project_auth_token = token_resp.headers.get('X-Subject-Token')
            except (
                requests.exceptions.HTTPError,
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
            ) as e:
                exception_msg = "unable to retrieve project from keystone auth with identity: @{url}: {ex}".format(
                    url=keystone_server_url, ex=e
                )
                raise KeystoneUnreachable(exception_msg)

            nova_endpoint = cls._get_nova_endpoint(token_resp.json(), nova_api_version)
            neutron_endpoint = cls._get_neutron_endpoint(token_resp.json()),
            project_auth_scope = {
                'project': {
                    'name': project['name'],
                    'id': project['id'],
                    'domain': {} if project['domain_id'] is None else {'id': project['domain_id']},
                }
            }
            project_scope = OpenStackProject(project_auth_token, project_auth_scope, nova_endpoint, neutron_endpoint)
            project_scope_map[project_key] = project_scope
        return cls(auth_token, project_scope_map)

    @classmethod
    def _get_token_for_project(cls, auth_token, project, keystone_server_url, ssl_verify, proxy=None):
        identity = {"methods": ['token'], "token": {"id": auth_token}}
        scope = {'project': {'id': project['id']}}
        payload = {'auth': {'identity': identity, 'scope': scope}}
        headers = {'Content-Type': 'application/json'}
        auth_url = urljoin(keystone_server_url, "{}/auth/tokens".format(DEFAULT_KEYSTONE_API_VERSION))

        resp = requests.post(
            auth_url,
            headers=headers,
            data=json.dumps(payload),
            verify=ssl_verify,
            timeout=DEFAULT_API_REQUEST_TIMEOUT,
            proxies=proxy,
        )
        resp.raise_for_status()

        return resp

    @classmethod
    def _request_project_list(cls, auth_token, keystone_server_url, ssl_verify, proxy=None):
        auth_url = urljoin(keystone_server_url, "{}/auth/projects".format(DEFAULT_KEYSTONE_API_VERSION))
        headers = {'X-Auth-Token': auth_token}

        resp = requests.get(
            auth_url, headers=headers, verify=ssl_verify, timeout=DEFAULT_API_REQUEST_TIMEOUT, proxies=proxy
        )
        resp.raise_for_status()

        return resp


class OpenStackProject:
    """
    Container class for a single project's authorization scope
    Embeds the auth token to be included with API requests, and refreshes
    the token on expiry
    """

    def __init__(self, auth_token, auth_scope, nova_endpoint, neutron_endpoint):
        self.auth_token = auth_token
        # Store some identifiers for this project
        self.project_name = auth_scope["project"].get("name")
        self.domain_id = auth_scope["project"].get("domain", {}).get("id")
        self.tenant_id = auth_scope["project"].get("id")
        self.nova_endpoint = nova_endpoint
        self.neutron_endpoint = neutron_endpoint
