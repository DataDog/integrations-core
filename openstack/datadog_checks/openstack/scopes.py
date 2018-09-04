# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import requests
import simplejson as json
from urlparse import urljoin

from datadog_checks.config import is_affirmative

from .exceptions import (IncompleteConfig, IncompleteAuthScope, IncompleteIdentity,
                         MissingNovaEndpoint, KeystoneUnreachable)
from .catalog import ServiceCatalog
from .settings import (UNSCOPED_AUTH, DEFAULT_API_REQUEST_TIMEOUT, DEFAULT_KEYSTONE_API_VERSION,
                       DEFAULT_NOVA_API_VERSION, FALLBACK_NOVA_API_VERSION)


class OpenStackScope(object):
    def __init__(self, auth_token):
        self.auth_token = auth_token

    @classmethod
    def _request_auth_token(cls, auth_scope, identity, keystone_server_url, ssl_verify, proxy=None):
        if not auth_scope:
            auth_scope = UNSCOPED_AUTH

        payload = {'auth': {'identity': identity, 'scope': auth_scope}}
        auth_url = urljoin(keystone_server_url, "{0}/auth/tokens".format(DEFAULT_KEYSTONE_API_VERSION))
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
                user and user.get('name') and user.get('password') and user.get("domain")
                and user.get("domain").get("id")
        ):
            raise IncompleteIdentity()

        identity = {"methods": ['password'], "password": {"user": user}}
        return identity

    @classmethod
    def _get_auth_scope(cls, instance_config):
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
    def _get_auth_response_from_config(cls, init_config, instance_config, proxy_config=None):
        keystone_server_url = init_config.get("keystone_server_url")
        if not keystone_server_url:
            raise IncompleteConfig()

        ssl_verify = is_affirmative(init_config.get("ssl_verify", False))

        auth_scope = cls._get_auth_scope(instance_config)
        identity = cls._get_user_identity(instance_config)

        exception_msg = None
        auth_resp = None
        try:
            auth_resp = cls._request_auth_token(auth_scope, identity, keystone_server_url, ssl_verify, proxy_config)
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            exception_msg = "Failed keystone auth with user:{user} domain:{domain} scope:{scope} @{url}".format(
                user=identity['password']['user']['name'],
                domain=identity['password']['user']['domain']['id'],
                scope=auth_scope,
                url=keystone_server_url,
            )

        if exception_msg:
            try:
                # TODO: instead of relying on a failure we should make the decision before on what param to set.
                # This will prevent a lot of failed call to be made!
                identity['password']['user']['domain']['name'] = identity['password']['user']['domain'].pop('id')

                if auth_scope:
                    if 'domain' in auth_scope['project']:
                        auth_scope['project']['domain']['name'] = auth_scope['project']['domain'].pop('id')
                    else:
                        auth_scope['project']['name'] = auth_scope['project'].pop('id')
                auth_resp = cls._request_auth_token(auth_scope, identity, keystone_server_url, ssl_verify, proxy_config)
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
        """
        Creates a OpenStackUnscoped instance

        Request authentication token from Keystone then select all projects from Keystone.
        We don't submit the authentication scope retrieved during authentication when listing all project.
        Then we loop over all projects and make call the Keystone to get project authentication tokens
        and services endpoints, from there we create a list of OpenStackProjectScope objects

        :param init_config:
        :param instance_config:
        :param proxy_config:
        :return:
        """
        keystone_server_url = init_config.get("keystone_server_url")
        if not keystone_server_url:
            raise IncompleteConfig()

        ssl_verify = is_affirmative(init_config.get("ssl_verify", True))
        nova_api_version = init_config.get("nova_api_version", DEFAULT_NOVA_API_VERSION)

        _, auth_token, _ = cls._get_auth_response_from_config(init_config, instance_config, proxy_config)

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

            try:
                service_catalog = ServiceCatalog.from_auth_response(token_resp.json(), nova_api_version)
            except MissingNovaEndpoint:
                # TODO: instead of relying on a failure we should make the decision before on what param to set.
                # This will prevent a lot of failed call to be made!
                service_catalog = ServiceCatalog.from_auth_response(token_resp.json(), FALLBACK_NOVA_API_VERSION)

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
    def _get_token_for_project(cls, auth_token, project, keystone_server_url, ssl_verify, proxy=None):
        identity = {"methods": ['token'], "token": {"id": auth_token}}
        scope = {'project': {'id': project['id']}}
        payload = {'auth': {'identity': identity, 'scope': scope}}
        headers = {'Content-Type': 'application/json'}
        auth_url = urljoin(keystone_server_url, "{0}/auth/tokens".format(DEFAULT_KEYSTONE_API_VERSION))

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
        auth_url = urljoin(keystone_server_url, "{0}/auth/projects".format(DEFAULT_KEYSTONE_API_VERSION))
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
        """

        :param init_config:
        :param instance_config:
        :param proxy_config:
        :return:
        """
        keystone_server_url = init_config.get("keystone_server_url")
        if not keystone_server_url:
            raise IncompleteConfig()

        nova_api_version = init_config.get("nova_api_version", DEFAULT_NOVA_API_VERSION)

        auth_scope, auth_token, auth_resp = cls._get_auth_response_from_config(
            init_config, instance_config, proxy_config
        )

        try:
            service_catalog = ServiceCatalog.from_auth_response(auth_resp.json(), nova_api_version)
        except MissingNovaEndpoint:
            # TODO: instead of relying on a failure we should make the decision before on what param to set.
            # This will prevent a lot of failed call to be made!
            service_catalog = ServiceCatalog.from_auth_response(auth_resp.json(), FALLBACK_NOVA_API_VERSION)

        # (NOTE): aaditya
        # In some cases, the nova url is returned without the tenant id suffixed
        # e.g. http://172.0.0.1:8774 rather than http://172.0.0.1:8774/<tenant_id>
        # It is still unclear when this happens, but for now the user can configure
        # `append_tenant_id` to manually add this suffix for downstream requests

        # TODO: Greg
        # This could be done automatically without requiring the user to enable `append_tenant_id`
        if is_affirmative(instance_config.get("append_tenant_id", False)):
            t_id = auth_scope["project"].get("id")

            assert (
                t_id and t_id not in service_catalog.nova_endpoint
            ), """Incorrect use of append_tenant_id, please inspect the service catalog response of your Identity server.
                   You may need to disable this flag if your Nova service url contains the tenant_id already"""

            service_catalog.nova_endpoint = urljoin(service_catalog.nova_endpoint, t_id)

        return cls(auth_token, auth_scope, service_catalog)
