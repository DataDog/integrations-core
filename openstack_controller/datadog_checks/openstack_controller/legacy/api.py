# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy
from os import environ

import requests
from openstack import connection
from six import PY3
from six.moves.urllib.parse import urljoin

from .exceptions import (
    AuthenticationNeeded,
    IncompleteIdentity,
    InstancePowerOffFailure,
    KeystoneUnreachable,
    MissingNeutronEndpoint,
    MissingNovaEndpoint,
    RetryLimitExceeded,
)
from .settings import (
    DEFAULT_KEYSTONE_API_VERSION,
    DEFAULT_MAX_RETRY,
    DEFAULT_NEUTRON_API_VERSION,
    DEFAULT_PAGINATED_LIMIT,
)

UNSCOPED_AUTH = 'unscoped'


class ApiFactory(object):
    @staticmethod
    def create(logger, instance_config, requests_wrapper):
        paginated_limit = instance_config.get('paginated_limit', DEFAULT_PAGINATED_LIMIT)
        user = instance_config.get("user")
        openstack_config_file_path = instance_config.get("openstack_config_file_path")
        openstack_cloud_name = instance_config.get("openstack_cloud_name")

        # If an OpenStack configuration is specified, an OpenstackSDKApi is created, and the authentication
        # is made directly from the OpenStack configuration file
        if openstack_cloud_name is None:
            keystone_server_url = instance_config.get("keystone_server_url")
            api = SimpleApi(logger, keystone_server_url, requests_wrapper, limit=paginated_limit)
            api.connect(user)
        else:
            api = OpenstackSDKApi(logger)
            api.connect(openstack_config_file_path, openstack_cloud_name)

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

    def get_os_hypervisor_uptime(self, hypervisor):
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


class OpenstackSDKApi(AbstractApi):
    def __init__(self, logger):
        super(OpenstackSDKApi, self).__init__(logger)

        self.connection = None
        self.services = {}
        self.endpoints = {}
        self.projects = None

    def connect(self, openstack_sdk_config_file_path, openstack_sdk_cloud_name):
        if openstack_sdk_config_file_path is not None:
            # Set the environment variable to the path of the config file for openstacksdk to find it
            environ["OS_CLIENT_CONFIG_FILE"] = openstack_sdk_config_file_path
        self.connection = connection.Connection(cloud=openstack_sdk_cloud_name)
        # Raise error if the connection failed
        self.connection.authorize()

    def _check_authentication(self):
        if self.connection is None:
            raise AuthenticationNeeded()

    def _get_service(self, service_name):
        self._check_authentication()

        if service_name not in self.services:
            self.services[service_name] = self.connection.get_service(service_name)
        return self.services[service_name]

    def _get_endpoint(self, service_name):
        self._check_authentication()

        if service_name not in self.endpoints:
            try:
                service_filter = {u'service_id': self._get_service(service_name)[u'id']}
                endpoints_list = self.connection.search_endpoints(filters=service_filter)

                if not endpoints_list:
                    return None

                self.endpoints[service_name] = None
                # Get the public or the internal endpoint
                for endpoint in endpoints_list:
                    if endpoint[u'interface'] == u'public':
                        self.endpoints[service_name] = endpoint
                        return self.endpoints[service_name]
                    elif endpoint[u'interface'] == u'internal':
                        self.endpoints[service_name] = endpoint
            except Exception as e:
                self.logger.debug("Error contacting openstack endpoint with openstacksdk: %s", e)

        return self.endpoints[service_name]

    def get_keystone_endpoint(self):
        keystone_endpoint = self._get_endpoint(u'keystone')

        if keystone_endpoint is None:
            raise KeystoneUnreachable()
        return keystone_endpoint[u'links'][u'self']

    def get_nova_endpoint(self):
        nova_endpoint = self._get_endpoint(u'nova')

        if nova_endpoint is None:
            raise MissingNovaEndpoint()
        return nova_endpoint[u'links'][u'self']

    def get_neutron_endpoint(self):
        neutron_endpoint = self._get_endpoint(u'neutron')

        if neutron_endpoint is None:
            raise MissingNeutronEndpoint()
        return neutron_endpoint[u'links'][u'self']

    def get_projects(self):
        self._check_authentication()

        if self.projects is None:
            self.projects = self.connection.search_projects()

        return self.projects

    def get_project_limits(self, project_id):
        self._check_authentication()

        # Raise exception if the project is not found
        project_limits_raw = self.connection.get_compute_limits(project_id)
        project_limits = project_limits_raw["properties"]

        # Used to convert the project_limits_raw key name
        key_name_conversion = {
            "max_personality": "maxPersonality",
            "max_personality_size": "maxPersonalitySize",
            "max_server_groups": "maxServerGroups",
            "max_server_group_members": "maxServerGroupMembers",
            "max_server_meta": "maxServerMeta",
            "max_total_cores": "maxTotalCores",
            "max_total_keypairs": "maxTotalKeypairs",
            "max_total_instances": "maxTotalInstances",
            "max_total_ram_size": "maxTotalRAMSize",
            "total_cores_used": "totalCoresUsed",
            "total_instances_used": "totalInstancesUsed",
            "total_ram_used": "totalRAMUsed",
            "total_server_groups_used": "totalServerGroupsUsed",
        }

        for raw_value, value in key_name_conversion.items():
            project_limits[value] = project_limits_raw[raw_value]

        try:
            network_quotas = self.connection.get_network_quotas(project_id, details=True)
        except Exception:
            self.logger.exception('There was a problem getting network quotas')
        else:
            project_limits['totalFloatingIpsUsed'] = network_quotas['floatingip']['used']
            project_limits['maxTotalFloatingIps'] = network_quotas['floatingip']['limit']

        return project_limits

    def get_os_hypervisors_detail(self):
        self._check_authentication()

        return self.connection.list_hypervisors()

    def get_os_hypervisor_uptime(self, hypervisor):
        if PY3:
            if hypervisor.uptime is None:
                self._check_authentication()
                self.connection.compute.get_hypervisor_uptime(hypervisor)
            return hypervisor.uptime
        else:
            # Hypervisor uptime is not available in openstacksdk 0.24.0.
            self.logger.warning("Hypervisor uptime is not available with this version of openstacksdk")
            raise NotImplementedError()

    def get_os_aggregates(self):
        # Each aggregate is missing the 'uuid' attribute compared to what is returned by SimpleApi
        self._check_authentication()

        return self.connection.list_aggregates()

    def get_flavors_detail(self, query_params):
        self._check_authentication()

        return self.connection.search_flavors(filters=query_params)

    def get_networks(self):
        self._check_authentication()

        return self.connection.list_networks()

    def get_servers_detail(self, query_params):
        # Each server is missing some attributes compared to what is returned by SimpleApi.
        # They are all unused for the moment.
        # SimpleApi:
        # https://developer.openstack.org/api-ref/compute/?expanded=list-flavors-with-details-detail,list-servers-detailed-detail#list-servers-detailed
        # OpenstackSDKApi:
        # https://docs.openstack.org/openstacksdk/latest/user/connection.html#openstack.connection.Connection

        self._check_authentication()

        return self.connection.list_servers(detailed=True, all_projects=True, filters=query_params)

    def get_server_diagnostics(self, server_id):
        # With microversion 2.48 the format of server diagnostics changed
        # https://docs.openstack.org/api-ref/compute/?expanded=show-server-diagnostics-detail
        # With SimpleApi this method returns either the new or the old format depending on the hypervisor.
        # Because openstacksdk only supports the new format, this method either returns the new format with new
        # hypervisor, or an empty payload with older hypervisor.
        self._check_authentication()

        return self.connection.compute.get_server_diagnostics(server_id)


class SimpleApi(AbstractApi):
    def __init__(self, logger, keystone_endpoint, requests_wrapper, limit=DEFAULT_PAGINATED_LIMIT):
        super(SimpleApi, self).__init__(logger)
        self.http = requests_wrapper
        self.keystone_endpoint = keystone_endpoint
        self.timeout = self.http.options['timeout'][0]
        self.paginated_limit = limit
        self.nova_endpoint = None
        self.neutron_endpoint = None
        self.auth_token = None

    def connect(self, user):
        credentials = Authenticator.from_config(self.logger, self.keystone_endpoint, user, self.http)
        self.logger.debug("Nova Url: %s", credentials.nova_endpoint)
        self.nova_endpoint = credentials.nova_endpoint
        self.logger.debug("Neutron Url: %s", credentials.neutron_endpoint)
        self.neutron_endpoint = credentials.neutron_endpoint
        self.auth_token = credentials.auth_token
        self.http.options['headers']['X-Auth-Token'] = credentials.auth_token

    def _make_request(self, url, params=None):
        """
        Generic request handler for OpenStack API requests
        Raises specialized Exceptions for commonly encountered error codes
        """
        self.logger.debug("Request URL, Headers and Params: %s, %s, %s", url, self.http.options['headers'], params)

        try:
            resp = self.http.get(url, params=params)
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
        except Exception:
            self.logger.exception("Unexpected error contacting openstack endpoint %s", url)
            raise
        jresp = resp.json()
        self.logger.debug("url: %s || response: %s", url, jresp)

        return jresp

    def get_keystone_endpoint(self):
        self._make_request(self.keystone_endpoint)

    def get_nova_endpoint(self):
        self._make_request(self.nova_endpoint)

    def get_neutron_endpoint(self):
        self._make_request(self.neutron_endpoint)

    def get_os_hypervisor_uptime(self, hypervisor):
        hyp_id = hypervisor['id']
        url = '{}/os-hypervisors/{}/uptime'.format(self.nova_endpoint, hyp_id)
        resp = self._make_request(url)
        return resp.get('hypervisor', {}).get('uptime')

    def get_os_aggregates(self):
        url = '{}/os-aggregates'.format(self.nova_endpoint)
        aggregate_list = self._make_request(url)
        return aggregate_list.get('aggregates', [])

    def get_os_hypervisors_detail(self):
        url = '{}/os-hypervisors/detail'.format(self.nova_endpoint)
        hypervisors = self._make_request(url)
        return hypervisors.get('hypervisors', [])

    def get_servers_detail(self, query_params):
        url = '{}/servers/detail'.format(self.nova_endpoint)
        return self._get_paginated_list(url, 'servers', query_params)

    def get_server_diagnostics(self, server_id):
        url = '{}/servers/{}/diagnostics'.format(self.nova_endpoint, server_id)
        return self._make_request(url)

    def get_project_limits(self, tenant_id):
        url = '{}/limits'.format(self.nova_endpoint)
        server_stats = self._make_request(url, params={"tenant_id": tenant_id})
        limits = server_stats.get('limits', {}).get('absolute', {})

        try:
            url = '{}/{}/quotas/{}/details'.format(self.neutron_endpoint, DEFAULT_NEUTRON_API_VERSION, tenant_id)
            network_quotas = self._make_request(url)
        except Exception:
            self.logger.exception('There was a problem getting network quotas')
        else:
            limits['totalFloatingIpsUsed'] = network_quotas['quota']['floatingip']['used']
            limits['maxTotalFloatingIps'] = network_quotas['quota']['floatingip']['limit']

        return limits

    def get_flavors_detail(self, query_params):
        url = '{}/flavors/detail'.format(self.nova_endpoint)
        if query_params is None:
            query_params = {}
        query_params["is_public"] = "none"
        return self._get_paginated_list(url, 'flavors', query_params)

    def _get_paginated_list(self, url, obj, query_params):
        result = []
        query_params = query_params or {}
        query_params['limit'] = self.paginated_limit
        while True:
            retry = 0
            while retry < DEFAULT_MAX_RETRY:
                try:
                    resp = self._make_request(url, params=query_params)
                    break
                except requests.exceptions.HTTPError as e:
                    # Only catch HTTPErrors to enable the retry mechanism.
                    # Other exceptions raised by _make_request (e.g. AuthenticationNeeded) should be caught downstream
                    self.logger.debug(
                        "Error making paginated request to %s, lowering limit from %s to %s: %s",
                        url,
                        query_params['limit'],
                        query_params['limit'] // 2,
                        e,
                    )
                    query_params['limit'] //= 2
                    retry += 1
            else:
                raise RetryLimitExceeded("Reached retry limit while making request to {}".format(url))

            objects = resp.get(obj, [])
            result.extend(objects)
            # If there is no link to the next object, it means we're done.
            # For servers, see https://developer.openstack.org/api-ref/compute/?expanded=list-servers-detailed-detail
            if resp.get("{}_links".format(obj)) is None:
                break

            query_params['marker'] = objects[-1]['id']

        return result

    def get_networks(self):
        url = '{}/{}/networks'.format(self.neutron_endpoint, DEFAULT_NEUTRON_API_VERSION)

        try:
            networks = self._make_request(url)
            return networks.get('networks')
        except Exception as e:
            self.logger.warning('Unable to get the list of all network ids: %s', e)
            raise e

    def get_projects(self):
        """
        Returns all projects in the domain
        """
        url = urljoin(self.keystone_endpoint, "{}/{}".format(DEFAULT_KEYSTONE_API_VERSION, "projects"))
        try:
            r = self._make_request(url)
            return r.get('projects', [])

        except Exception as e:
            self.logger.warning('Unable to get projects: %s', e)
            raise e


class Authenticator(object):
    def __init__(self):
        pass

    @classmethod
    def from_config(cls, logger, keystone_endpoint, user, requests_wrapper):
        # Make Token authentication with explicit unscoped authorization
        identity = cls._get_user_identity(user)
        post_auth_token_resp = cls._post_auth_token(
            logger, keystone_endpoint, identity, requests_wrapper, scope=UNSCOPED_AUTH
        )
        keystone_auth_token = post_auth_token_resp.headers.get('X-Subject-Token')
        # List all projects using retrieved auth token
        requests_wrapper.options['headers']['X-Auth-Token'] = keystone_auth_token
        projects = cls._get_auth_projects(logger, keystone_endpoint, requests_wrapper)

        # For each project, we create an OpenStackProject object that we add to the `project_scopes` dict
        credential_auth_token = None
        credential_project_auth_scope = None
        credential_nova_endpoint = None
        credential_neutron_endpoint = None
        found_admin_credential = False
        for project in projects:
            identity = {"methods": ['token'], "token": {"id": keystone_auth_token}}
            scope = {'project': {'id': project.get('id')}}
            # Make Token authentication with project id scoped authorization
            token_resp = cls._post_auth_token(logger, keystone_endpoint, identity, requests_wrapper, scope=scope)

            # Retrieved token, nova and neutron endpoints
            auth_token = token_resp.headers.get('X-Subject-Token')
            nova_endpoint = cls._get_nova_endpoint(token_resp.json())
            neutron_endpoint = cls._get_neutron_endpoint(token_resp.json())
            roles = cls._get_roles(token_resp.json())
            has_admin_auth = "admin" in roles

            project_auth_scope = {
                'project': {
                    'name': project.get('name'),
                    'id': project.get('id'),
                    'domain': {} if project.get('domain_id') is None else {'id': project.get('domain_id')},
                }
            }

            project_name = project.get('name')
            project_id = project.get('id')

            if not found_admin_credential and project_name is not None and project_id is not None:
                found_admin_credential = has_admin_auth

                credential_auth_token = auth_token
                credential_project_auth_scope = project_auth_scope
                credential_nova_endpoint = nova_endpoint
                credential_neutron_endpoint = neutron_endpoint

        if (
            credential_auth_token
            and credential_project_auth_scope
            and credential_nova_endpoint
            and credential_neutron_endpoint
        ):
            return Credential(
                credential_auth_token,
                credential_project_auth_scope,
                credential_nova_endpoint,
                credential_neutron_endpoint,
            )

        return None

    @staticmethod
    def _post_auth_token(logger, keystone_endpoint, identity, requests_wrapper, scope=UNSCOPED_AUTH):
        auth_url = urljoin(keystone_endpoint, "{}/auth/tokens".format(DEFAULT_KEYSTONE_API_VERSION))
        try:
            payload = {'auth': {'identity': identity, 'scope': scope}}
            resp = requests_wrapper.post(auth_url, json=payload)
            resp.raise_for_status()
            logger.debug("url: %s || response: %s", auth_url, resp.json())
            return resp

        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            safe_identity = copy.deepcopy(identity)
            safe_identity['password']['user']['password'] = '********'
            msg = "Failed Keystone auth with identity:{identity} scope:{scope} @{url}".format(
                identity=safe_identity, scope=scope, url=auth_url
            )
            logger.debug(msg)
            raise KeystoneUnreachable(msg)

    @staticmethod
    def _get_auth_projects(logger, keystone_endpoint, requests_wrapper):
        auth_url = ""
        try:
            auth_url = urljoin(keystone_endpoint, "{}/auth/projects".format(DEFAULT_KEYSTONE_API_VERSION))
            resp = requests_wrapper.get(auth_url)
            resp.raise_for_status()
            jresp = resp.json()
            logger.debug("url: %s || response: %s", auth_url, jresp)
            projects = jresp.get('projects')
            return projects
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            msg = "unable to retrieve project list from Keystone auth with identity: @{url}: {ex}".format(
                url=auth_url, ex=e
            )
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
        if not (
            user and user.get('name') and user.get('password') and user.get("domain") and user.get("domain").get("id")
        ):
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

    @classmethod
    def _get_roles(cls, json_resp):
        """
        Collec the role names returned by the Identity API
        """
        roles_json = json_resp.get('token', {}).get('roles', [])
        role_names = [role.get('name') for role in roles_json]
        return role_names

    @staticmethod
    def _get_valid_endpoint(resp, name, entry_type):
        """
        Parse the service catalog returned by the Identity API for an endpoint matching
        the Nova service with the requested version
        Sends a CRITICAL service check when no viable candidates are found in the Catalog
        """
        catalog = resp.get('token', {}).get('catalog', [])
        for entry in catalog:
            if (
                entry.get('name')
                and entry.get('type')
                and entry.get('name') == name
                and entry.get('type') == entry_type
            ):
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
