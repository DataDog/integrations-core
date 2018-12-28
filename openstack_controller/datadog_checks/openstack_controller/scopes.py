# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import requests
import simplejson as json

from six.moves.urllib.parse import urljoin

from .exceptions import (IncompleteIdentity, MissingNovaEndpoint, MissingNeutronEndpoint, KeystoneUnreachable)
from .settings import DEFAULT_KEYSTONE_API_VERSION


UNSCOPED_AUTH = 'unscoped'


class Authenticator(object):
    def __init__(self):
        pass

    @classmethod
    def from_config(cls, logger, keystone_endpoint, user, ssl_verify=False, proxies=None,
                    timeout=DEFAULT_KEYSTONE_API_VERSION):
        # Make Token authentication with explicit unscoped authorization
        identity = cls._get_user_identity(user)
        post_auth_token_resp = cls._post_auth_token(logger, keystone_endpoint, identity, ssl_verify=ssl_verify,
                                                    proxies=proxies, timeout=timeout, scope=UNSCOPED_AUTH)
        auth_token = post_auth_token_resp.headers.get('X-Subject-Token')
        # List all projects using retrieved auth token
        headers = {'X-Auth-Token': auth_token}
        projects = cls._get_auth_projects(logger, keystone_endpoint, headers=headers, ssl_verify=ssl_verify,
                                          proxies=proxies, timeout=timeout)

        # For each project, we create an OpenStackProject object that we add to the `project_scopes` dict
        # project_scopes = {}
        for project in projects:
            identity = {"methods": ['token'], "token": {"id": auth_token}}
            scope = {'project': {'id': project.get('id')}}
            # Make Token authentication with project id scoped authorization
            token_resp = cls._post_auth_token(logger, keystone_endpoint, identity, ssl_verify=ssl_verify,
                                              proxies=proxies, timeout=timeout, scope=scope)

            # Retrieved token, nova and neutron endpoints
            project_auth_token = token_resp.headers.get('X-Subject-Token')
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
                return Credential(auth_token, project_auth_scope, project_auth_token, nova_endpoint, neutron_endpoint)

        return None

    @staticmethod
    def _post_auth_token(logger, keystone_endpoint, identity, ssl_verify=False, proxies=None,
                         timeout=DEFAULT_KEYSTONE_API_VERSION, scope=UNSCOPED_AUTH):
        auth_url = urljoin(keystone_endpoint, "{}/auth/tokens".format(timeout))
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
                           timeout=DEFAULT_KEYSTONE_API_VERSION):
        auth_url = ""
        try:
            auth_url = urljoin(keystone_endpoint, "{}/auth/projects".format(timeout))
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
    def __init__(self, auth_token, auth_scope, project_auth_token, nova_endpoint, neutron_endpoint):
        self.auth_token = auth_token
        self.project_auth_token = project_auth_token
        self.name = auth_scope.get("project", {}).get("name")
        self.domain_id = auth_scope.get("project", {}).get("domain", {}).get("id")
        self.tenant_id = auth_scope.get("project", {}).get("id")
        self.nova_endpoint = nova_endpoint
        self.neutron_endpoint = neutron_endpoint
