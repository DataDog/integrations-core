# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from urlparse import urljoin
import requests
import simplejson as json

from datadog_checks.config import is_affirmative

from .settings import DEFAULT_API_REQUEST_TIMEOUT, DEFAULT_KEYSTONE_API_VERSION
from .exceptions import (IncompleteConfig, IncompleteAuthScope,
                         IncompleteIdentity, MissingNovaEndpoint, MissingNeutronEndpoint, KeystoneUnreachable)


UNSCOPED_AUTH = 'unscoped'
V21_NOVA_API_VERSION = 'v2.1'
DEFAULT_NOVA_API_VERSION = V21_NOVA_API_VERSION
FALLBACK_NOVA_API_VERSION = 'v2'


class KeystoneCatalog(object):
    """
    A registry of services, scoped to the project, returned by the identity server
    Contains parsers for retrieving service endpoints from the server auth response
    """

    def __init__(self, nova_endpoint, neutron_endpoint):
        self.nova_endpoint = nova_endpoint
        self.neutron_endpoint = neutron_endpoint

    @classmethod
    def from_auth_response(cls, json_response, nova_api_version, keystone_server_url=None, auth_token=None, proxy=None):
        try:
            return cls(
                nova_endpoint=cls.get_nova_endpoint(json_response, nova_api_version),
                neutron_endpoint=cls.get_neutron_endpoint(json_response),
            )
        except (MissingNeutronEndpoint, MissingNovaEndpoint) as e:
            if keystone_server_url and auth_token:
                return cls.from_unscoped_token(keystone_server_url, auth_token, nova_api_version, proxy)
            else:
                raise e

    @classmethod
    def from_unscoped_token(cls, keystone_server_url, auth_token, nova_api_version, ssl_verify=True, proxy=None):
        catalog_url = urljoin(keystone_server_url, "{}/auth/catalog".format(DEFAULT_KEYSTONE_API_VERSION))
        headers = {'X-Auth-Token': auth_token}

        resp = requests.get(
            catalog_url, headers=headers, verify=ssl_verify, timeout=DEFAULT_API_REQUEST_TIMEOUT, proxies=proxy
        )
        resp.raise_for_status()
        json_resp = resp.json()
        json_resp = {'token': json_resp}

        return cls(
            nova_endpoint=cls.get_nova_endpoint(json_resp, nova_api_version),
            neutron_endpoint=cls.get_neutron_endpoint(json_resp),
        )

    @classmethod
    def get_neutron_endpoint(cls, json_resp):
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
    def get_nova_endpoint(cls, json_resp, nova_api_version=None):
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


class OpenStackScope(object):
    def __init__(self, auth_token):
        self.auth_token = auth_token

    @classmethod
    def request_auth_token(cls, auth_scope, identity, keystone_server_url, ssl_verify, proxy=None):
        if not auth_scope:
            auth_scope = UNSCOPED_AUTH

        payload = {'auth': {'identity': identity, 'scope': auth_scope}}
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
    def get_user_identity(cls, instance_config):
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
    def get_auth_scope(cls, instance_config):
        """
        Parse authorization scope out of init_config

        To guarantee a uniquely identifiable scope, expects either:
        {'project': {'name': 'my_project', 'domain': {'id': 'my_domain_id'}}}
        OR
        {'project': {'id': 'my_project_id'}}
        """
        auth_scope = instance_config.get('auth_scope')
        if not auth_scope:
            return None

        if not auth_scope.get('project'):
            raise IncompleteAuthScope()

        if auth_scope['project'].get('name'):
            # We need to add a domain scope to avoid name clashes. Search for one. If not raise IncompleteAuthScope
            if not auth_scope['project'].get('domain', {}).get('id'):
                raise IncompleteAuthScope()
        else:
            # Assume a unique project id has been given
            if not auth_scope['project'].get('id'):
                raise IncompleteAuthScope()

        return auth_scope

    @classmethod
    def get_auth_response_from_config(cls, init_config, instance_config, proxy_config=None):
        keystone_server_url = init_config.get("keystone_server_url")
        if not keystone_server_url:
            raise IncompleteConfig()

        ssl_verify = is_affirmative(init_config.get("ssl_verify", False))

        auth_scope = cls.get_auth_scope(instance_config)
        identity = cls.get_user_identity(instance_config)

        exception_msg = None
        try:
            auth_resp = cls.request_auth_token(auth_scope, identity, keystone_server_url, ssl_verify, proxy_config)
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            exception_msg = "Failed keystone auth with user:{user} domain:{domain} scope:{scope} @{url}".format(
                user=identity['password']['user']['name'],
                domain=identity['password']['user']['domain']['id'],
                scope=auth_scope,
                url=keystone_server_url,
            )

        if exception_msg:
            try:
                identity['password']['user']['domain']['name'] = identity['password']['user']['domain'].pop('id')

                if auth_scope:
                    if 'domain' in auth_scope['project']:
                        auth_scope['project']['domain']['name'] = auth_scope['project']['domain'].pop('id')
                    else:
                        auth_scope['project']['name'] = auth_scope['project'].pop('id')
                auth_resp = cls.request_auth_token(auth_scope, identity, keystone_server_url, ssl_verify, proxy_config)
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
                    scope=auth_scope,
                    url=keystone_server_url,
                    ex=e,
                )
                raise KeystoneUnreachable(exception_msg)

        return auth_scope, auth_resp.headers.get('X-Subject-Token'), auth_resp


class OpenStackUnscoped(OpenStackScope):
    def __init__(self, auth_token, project_scope_map):
        super(OpenStackUnscoped, self).__init__(auth_token)
        self.project_scope_map = project_scope_map

    @classmethod
    def from_config(cls, init_config, instance_config, proxy_config=None):
        keystone_server_url = init_config.get("keystone_server_url")
        if not keystone_server_url:
            raise IncompleteConfig()

        ssl_verify = is_affirmative(init_config.get("ssl_verify", True))
        nova_api_version = init_config.get("nova_api_version", DEFAULT_NOVA_API_VERSION)

        _, auth_token, _ = cls.get_auth_response_from_config(init_config, instance_config, proxy_config)

        try:
            project_resp = cls.request_project_list(auth_token, keystone_server_url, ssl_verify, proxy_config)
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
                token_resp = cls.get_token_for_project(
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

            try:
                service_catalog = KeystoneCatalog.from_auth_response(token_resp.json(), nova_api_version)
            except MissingNovaEndpoint:
                service_catalog = KeystoneCatalog.from_auth_response(token_resp.json(), FALLBACK_NOVA_API_VERSION)

            project_auth_scope = {
                'project': {
                    'name': project['name'],
                    'id': project['id'],
                    'domain': {} if project['domain_id'] is None else {'id': project['domain_id']},
                }
            }
            project_scope = OpenStackProjectScope(project_auth_token, project_auth_scope, service_catalog)
            project_scope_map[project_key] = project_scope

        return cls(auth_token, project_scope_map)

    @classmethod
    def get_token_for_project(cls, auth_token, project, keystone_server_url, ssl_verify, proxy=None):
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
    def request_project_list(cls, auth_token, keystone_server_url, ssl_verify, proxy=None):
        auth_url = urljoin(keystone_server_url, "{}/auth/projects".format(DEFAULT_KEYSTONE_API_VERSION))
        headers = {'X-Auth-Token': auth_token}

        resp = requests.get(
            auth_url, headers=headers, verify=ssl_verify, timeout=DEFAULT_API_REQUEST_TIMEOUT, proxies=proxy
        )
        resp.raise_for_status()

        return resp


class OpenStackProjectScope(OpenStackScope):
    """
    Container class for a single project's authorization scope
    Embeds the auth token to be included with API requests, and refreshes
    the token on expiry
    """

    def __init__(self, auth_token, auth_scope, service_catalog):
        super(OpenStackProjectScope, self).__init__(auth_token)

        # Store some identifiers for this project
        self.project_name = auth_scope["project"].get("name")
        self.domain_id = auth_scope["project"].get("domain", {}).get("id")
        self.tenant_id = auth_scope["project"].get("id")
        self.service_catalog = service_catalog

    @classmethod
    def from_config(cls, init_config, instance_config, proxy_config=None):
        keystone_server_url = init_config.get("keystone_server_url")
        if not keystone_server_url:
            raise IncompleteConfig()

        nova_api_version = init_config.get("nova_api_version", DEFAULT_NOVA_API_VERSION)

        auth_scope, auth_token, auth_resp = cls.get_auth_response_from_config(
            init_config, instance_config, proxy_config
        )

        try:
            service_catalog = KeystoneCatalog.from_auth_response(auth_resp.json(), nova_api_version)
        except MissingNovaEndpoint:
            service_catalog = KeystoneCatalog.from_auth_response(auth_resp.json(), FALLBACK_NOVA_API_VERSION)

        # (NOTE): aaditya
        # In some cases, the nova url is returned without the tenant id suffixed
        # e.g. http://172.0.0.1:8774 rather than http://172.0.0.1:8774/<tenant_id>
        # It is still unclear when this happens, but for now the user can configure
        # `append_tenant_id` to manually add this suffix for downstream requests
        if is_affirmative(instance_config.get("append_tenant_id", False)):
            t_id = auth_scope["project"].get("id")

            assert (
                t_id and t_id not in service_catalog.nova_endpoint
            ), """Incorrect use of append_tenant_id, please inspect the service catalog response of your Identity server.
                   You may need to disable this flag if your Nova service url contains the tenant_id already"""

            service_catalog.nova_endpoint = urljoin(service_catalog.nova_endpoint, t_id)

        return cls(auth_token, auth_scope, service_catalog)
