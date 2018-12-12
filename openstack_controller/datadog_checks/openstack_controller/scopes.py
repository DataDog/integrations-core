# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.config import is_affirmative
from .exceptions import (IncompleteConfig, IncompleteIdentity, MissingNovaEndpoint,
                         MissingNeutronEndpoint)
from .api import KeystoneApi


class ScopeFetcher(object):
    def __init__(self):
        pass

    @classmethod
    def from_config(cls, logger, init_config, instance_config, proxy_config=None):
        keystone_server_url = init_config.get("keystone_server_url")
        if not keystone_server_url:
            raise IncompleteConfig()

        ssl_verify = is_affirmative(init_config.get("ssl_verify", True))
        # Make Token authentication with explicit unscoped authorization
        auth_token = cls._get_auth_response_from_config(logger, init_config, instance_config, proxy_config=proxy_config)
        keystone_api = KeystoneApi(logger, ssl_verify, proxy_config, keystone_server_url, auth_token)

        # List all projects using retrieved auth token
        projects = keystone_api.get_auth_projects()

        # For each project, we create an OpenStackProject object that we add to the `project_scopes` dict
        project_scopes = {}
        for project in projects:
            identity = {"methods": ['token'], "token": {"id": auth_token}}
            scope = {'project': {'id': project.get('id')}}
            # Make Token authentication with project id scoped authorization
            token_resp = keystone_api.post_auth_token(identity, scope=scope)

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

            project_scope = Project(project_auth_token, project_auth_scope, nova_endpoint, neutron_endpoint)
            project_name = project.get('name')
            project_id = project.get('id')
            if project_name is None or project_id is None:
                break
            project_key = (project_name, project_id)
            project_scopes[project_key] = project_scope

        return Scope(auth_token, project_scopes)

    @classmethod
    def _get_auth_response_from_config(cls, logger, init_config, instance_config, proxy_config=None):
        keystone_server_url = init_config.get("keystone_server_url")
        if not keystone_server_url:
            raise IncompleteConfig()
        ssl_verify = is_affirmative(init_config.get("ssl_verify", False))

        identity = cls._get_user_identity(instance_config)
        keystone_api = KeystoneApi(logger, ssl_verify, proxy_config, keystone_server_url, None)
        resp = keystone_api.post_auth_token(identity)
        return resp.headers.get('X-Subject-Token')

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


class Scope(object):
    def __init__(self, auth_token, project_scopes):
        self.auth_token = auth_token
        self.project_scopes = project_scopes


class Project:
    """
    Container class for a single project's authorization scope
    Embeds the auth token to be included with API requests, and refreshes
    the token on expiry
    """

    def __init__(self, auth_token, auth_scope, nova_endpoint, neutron_endpoint):
        self.auth_token = auth_token
        # Store some identifiers for this project
        self.name = auth_scope.get("project", {}).get("name")
        self.domain_id = auth_scope.get("project", {}).get("domain", {}).get("id")
        self.tenant_id = auth_scope.get("project", {}).get("id")
        self.nova_endpoint = nova_endpoint
        self.neutron_endpoint = neutron_endpoint
